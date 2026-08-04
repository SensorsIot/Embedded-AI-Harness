# Universal Embedded Workbench

[![host tests](https://img.shields.io/github/actions/workflow/status/SensorsIot/Universal-Embedded-Workbench/ci.yml?branch=main&label=host%20tests)](https://github.com/SensorsIot/Universal-Embedded-Workbench/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-c51a4a)
![ESP32](https://img.shields.io/badge/ESP32-supported-green)
![MCP](https://img.shields.io/badge/MCP-70%20tools-8a63d2)

## 🎯 The Problem

Working on an ESP32 means being physically attached to it. The board has to be
plugged into the machine you're typing on, so you can't develop from a laptop in
another room, and a container or VM can't reach it at all without fighting USB
passthrough. Testing it properly needs a second pile of hardware — a spare WiFi
network, a Bluetooth radio, a signal generator, an SDR — and a person sitting
there to press the reset button.

## 💡 The Solution

Put the boards on a Raspberry Pi instead, and reach everything over the network.
Plug an ESP32 into the Pi's USB hub and it appears instantly as a network serial
port, a GDB target, and a set of HTTP endpoints. The Pi's own radios stand in for
the missing test equipment, and its GPIO pins press the buttons for you.

```bash
curl http://workbench.local:8080/api/devices    # what's plugged in right now
```

## ✨ What It Does

- **Plug in a board → it's ready.** Auto-detected in seconds and mapped to a fixed
  port by which USB connector it's in — same connector, same port, always.
- **Serial over the network** at `rfc2217://workbench.local:4001`, working with
  esptool, PlatformIO, ESP-IDF, and anything else built on pyserial.
- **Debugging out of the box.** OpenOCD starts by itself for chips with USB-JTAG;
  connect GDB to port 3333.
- **Flash three ways** — over the network, locally on the Pi (for bridge-chip
  boards whose auto-reset can't be driven remotely), or over the air.
- **The Pi is the test equipment.** Its WiFi becomes an access point your board
  joins, its Bluetooth scans and connects, and optional SDR and Si5351 hardware
  receive and transmit on 433 MHz. Boards can log to it over UDP when the USB
  port is busy doing something else.
- **It presses the buttons.** GPIO wired to reset and boot forces download mode
  and rescues boards stuck in a boot loop, with nobody in the room.
- **Claude can drive all of it** through 70 MCP tools or the bundled skills.

Honest limits: **one serial client per board at a time** (that's RFC2217, not a
choice), the SDR is **one dongle, one user**, and the API has **no
authentication** — keep the bench on a network you trust.

## 🏗️ How It Works

```
 LAN (192.168.0.x)
       |
       | eth0 (wired)
       v
  Raspberry Pi ---- wlan0 (WiFi test AP: 192.168.4.x)
  workbench.local      hci0  (Bluetooth LE)
       |             UDP :5555 (log receiver)
       | USB hub (internal on Pi 3/4/5, external on Zero)
       |
  +----+----+----+----+
  |    |    |    |
 :4001 :4002 :4003 :4004  <- auto-assigned (4001 + slot index)
 SLOT1 SLOT2 SLOT3 SLOT4  <- one per detected hub port
```

The idea that makes it work is **slot-based identity**. A slot is a physical hole
in the USB hub, not a device. On boot the Pi walks its own USB topology, creates
one slot per usable port, and hands each a permanent TCP port. Whatever you plug
into that hole answers on that port — so your scripts and your `platformio.ini`
never go stale, even after you swap boards or the kernel renames `/dev/ttyACM0`
to `/dev/ttyACM3`.

The two interfaces never mix: **eth0** carries your traffic to the bench, **wlan0**
is dedicated to testing and free to become whatever network a test needs.

## 🚀 Quick Start

You need a Raspberry Pi with onboard WiFi and Bluetooth running Raspberry Pi OS
Lite (64-bit). A Pi Zero 2 W also needs a USB hub and a USB Ethernet adapter,
since wlan0 is reserved for testing; a Pi 3/4/5 has both built in. An RTL-SDR
dongle, an Si5351 + PE4302, and jumper wires to the board's EN/BOOT pins are all
optional.

```bash
git clone https://github.com/SensorsIot/Universal-Embedded-Workbench.git
cd Universal-Embedded-Workbench/pi
sudo bash install.sh
```

That installs every dependency (pyserial, hostapd, dnsmasq, bleak, esptool,
OpenOCD, rtl-sdr/rtl_433, mosquitto), sets up the udev hotplug rules, and starts
the portal as a systemd service. Plug in a board and check:

```bash
curl http://workbench.local:8080/api/devices | jq
```

Slots are auto-detected — no config file needed. Create
`/etc/rfc2217/workbench.json` only to rename slots, pin ports, declare GPIO pins,
or register an ESP-Prog probe; `sudo rfc2217-learn-slots` prints one for you.

> **On a Pi Zero 2 W, do the memory hardening first.** With 512 MB the board
> OOM-crashes under load, and hard crashes corrupt the SD card. See
> [User Manual §2.2](docs/Embedded-Workbench-User-Manual.md#22-first-boot--system-hardening).

## 🔌 Usage

**Watch a board boot** — no client library, just HTTP:

```bash
curl -X POST http://workbench.local:8080/api/serial/reset \
  -H 'Content-Type: application/json' -d '{"slot":"SLOT1"}'
```

**Point your existing tools at it.** PlatformIO needs one line
(`upload_port = rfc2217://workbench.local:4001`); esptool takes the same URL, and
the binaries stay on your machine:

```bash
esptool --port rfc2217://workbench.local:4001 --chip esp32c3 \
  write-flash 0x10000 firmware.bin
```

**Write a test that uses the whole bench** — reset the board, give it a network
to join, wait for it to appear, then talk to it:

```python
from workbench_driver import WorkbenchDriver
wt = WorkbenchDriver("http://workbench.local:8080")

wt.serial_reset("SLOT1")
wt.serial_monitor("SLOT1", pattern="WiFi connected", timeout=30)

wt.ap_start("TestAP", "password123")
station = wt.wait_for_station(timeout=30)
wt.http_get(f"http://{station['ip']}/status")
```

## 🤖 Driving It From Claude

An MCP server exposes the whole API as **70 tools**, so Claude Desktop or Claude
Code can operate the bench conversationally — "flash this to slot 1 and tell me
why it's crashing". Pure Python standard library, so there's nothing to
`pip install`. For Claude Desktop, drag
[`mcp/universal-embedded-workbench.mcpb`](mcp/universal-embedded-workbench.mcpb)
onto **Settings → Extensions** and enter your workbench URL.

The repo also carries Claude Code skills under `.claude/skills/` for the
build/flash lifecycle, logging, WiFi, BLE, MQTT, debug, RF, and test workflows.
Setup for both:
[User Manual §15](docs/Embedded-Workbench-User-Manual.md#15-driving-the-bench-from-claude).

## 🩺 Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Device not detected | Charge-only USB cable | Use a data cable; check `lsusb` on the Pi |
| `Wrong boot mode (0x13)` when flashing | Bridge-chip board — RFC2217 can't drive its auto-reset | Flash with `POST /api/flash` instead |
| Rapid connect/disconnect | Erased or corrupt flash, boot loop | Auto-recovers via GPIO; force with `POST /api/serial/recover` |
| ESP32-C3 stuck in download mode | DTR asserted when the port opened | `POST /api/serial/reset` |
| GDB won't connect | Classic ESP32 has no USB-JTAG | Wire an ESP-Prog and declare it in `workbench.json` |
| SDR decodes noise or all zeros | Transmitter too close, AGC overloading | Add distance, set a fixed `gain` |
| Pi reboots at random | Out of memory (Pi Zero 2 W) | Apply the §2.2 hardening; check `free -h` |

Full table, with the diagnostics to run on the Pi →
[User Manual §17](docs/Embedded-Workbench-User-Manual.md#17-troubleshooting).

## 📡 Under the Hood

Serial travels over **[RFC2217](https://www.rfc-editor.org/rfc/rfc2217)**, a
Telnet extension that carries serial line control — baud rate, DTR, RTS — over
TCP. That's why it needs no kernel modules and passes through firewalls, and why
esptool and pyserial speak it natively.

Hotplug is event-driven, not polled: a **udev** rule fires on USB add/remove and
POSTs to the portal, which starts or stops that slot's proxy. Station events on
the test AP arrive the same way, via **dnsmasq** DHCP lease callbacks. Boards with
native USB-Serial/JTAG need care — Linux asserts DTR and RTS the moment the port
opens, dropping the chip into download mode mid-boot — so the portal delays
opening and drives the reset sequence itself.

Everything is one JSON HTTP API on `:8080`; every response carries `"ok"`.

```bash
curl -X POST .../api/wifi/ap_start -d '{"ssid":"TestAP","password":"secret"}'
curl -X POST .../api/gpio/set      -d '{"pin":18,"value":0}'
curl -X POST .../api/sdr/capture   -d '{"freq_hz":433920000,"duration_s":10}'
```

## 📚 Documentation

Three documents, one per question, and everything is in one of them:

| Question | Document | Read it for |
|----------|----------|-------------|
| **How do I run it?** | **[User Manual](docs/Embedded-Workbench-User-Manual.md)** | Building the Pi, wiring, and driving every service — install, serial, flashing, debug, WiFi, RF, test automation, troubleshooting. |
| **What must be true?** | **[Functional Specification](docs/Embedded-Workbench-FSD.md)** | What the bench does, clause by clause. [Appendix D](docs/Embedded-Workbench-FSD.md#appendix-d-http-api--mcp-reference) is the complete HTTP API and MCP tool reference. |
| **How is it built?** | **[Harness](docs/Harness/00-Overview.md)** | The build contract for contributors and AI agents — [workflow](docs/Harness/AI-Workflow.md), [architecture](docs/Harness/project/architecture.md), conventions, testing standard. |

## 🙏 Attributions

Built on [pyserial](https://github.com/pyserial/pyserial)
([RFC2217](https://www.rfc-editor.org/rfc/rfc2217)),
[esptool](https://github.com/espressif/esptool) and
[OpenOCD](https://github.com/espressif/openocd-esp32) from Espressif,
[bleak](https://github.com/hbldh/bleak),
[rtl_433](https://github.com/merbanan/rtl_433),
[hostapd / dnsmasq](https://w1.fi/hostapd/),
[mosquitto](https://mosquitto.org/), and the
[Model Context Protocol](https://modelcontextprotocol.io).

## 📄 License

MIT — see [LICENSE](LICENSE).
