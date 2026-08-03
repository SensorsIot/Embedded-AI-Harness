# Universal Embedded Workbench

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.9+-blue)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-c51a4a)
![ESP32](https://img.shields.io/badge/ESP32-supported-green)
![MCP](https://img.shields.io/badge/MCP-70%20tools-8a63d2)

## 🎯 The Problem

Working on an ESP32 means being physically attached to it. The board has to be
plugged into the machine you're typing on, so you can't develop from a laptop in
another room, and a container or VM can't reach the board at all without
fighting USB passthrough. Testing it properly needs a second pile of hardware —
a spare WiFi network, a Bluetooth radio, a signal generator, an SDR — and a
person sitting there to press the reset button.

## 💡 The Solution

Put the boards on a Raspberry Pi instead, and reach everything over the network.
Plug an ESP32 into the Pi's USB hub and it appears instantly as a network serial
port, a GDB target, and a set of HTTP endpoints. The Pi's own radios stand in for
the missing test equipment, and its GPIO pins press the buttons for you.

```bash
curl http://workbench.local:8080/api/devices    # what's plugged in right now
```

## ✨ What It Does

- **Plug in a board → it's ready.** Auto-detected within seconds and mapped to a
  fixed port by which USB connector it's in — same connector, same port, always,
  whatever board is in it and whatever name Linux picks this time.
- **Serial over the network** at `rfc2217://workbench.local:4001`, working with
  esptool, PlatformIO, ESP-IDF, and anything else built on pyserial.
- **Debugging works out of the box.** OpenOCD starts by itself for chips with
  USB-JTAG; connect GDB to port 3333.
- **Flash three ways** — over the network, locally on the Pi (for bridge-chip
  boards whose auto-reset can't be driven remotely), or over the air.
- **The Pi is the test equipment.** Its WiFi becomes an access point your board
  joins; its Bluetooth scans and connects; an optional SDR receives 433 MHz
  traffic and an optional Si5351 transmits it.
- **It presses the buttons.** GPIO pins wired to the board's reset and boot pins
  force download mode, simulate button presses, and rescue boards stuck in a
  boot loop — automatically, without anyone in the room.
- **Logs still reach you when USB is busy.** Boards can send debug output to the
  Pi over UDP, which matters when the USB port is doing something else — running
  as a keyboard, say.
- **A dashboard** at `http://workbench.local:8080` shows every slot, the WiFi
  state, the activity log, and live test progress.
- **Claude can drive all of it** through 70 MCP tools or the bundled skills.

Honest limits: **one serial client per board at a time** (that's RFC2217, not a
choice), the SDR is **one dongle, one user** — a capture and the live console
can't run at once — and the API has **no authentication**, so keep the bench on
a network you trust.

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
in the USB hub, not a device. On boot the Pi walks its own USB topology and
creates one slot per usable port, then hands each slot a permanent TCP port.
Whatever you plug into that hole answers on that port — so your scripts, your
`platformio.ini`, and your colleagues' bookmarks never go stale, even after you
swap boards or the kernel renames `/dev/ttyACM0` to `/dev/ttyACM3`.

The two network interfaces never mix: **eth0** carries your traffic to the bench,
**wlan0** is dedicated to testing and is free to become whatever access point a
test needs.

## 📋 Prerequisites

| Component | Notes |
|-----------|-------|
| **Raspberry Pi** (any model) | Needs onboard WiFi + Bluetooth. Auto-detects model and USB topology. |
| **USB Ethernet adapter** | Pi Zero 2 W only — wlan0 is reserved for testing. Pi 3/4/5 have built-in Ethernet. |
| **USB hub** | Pi Zero 2 W only. Pi 3/4/5 already have 4 USB ports. |
| **RTL-SDR dongle** | Optional — 433/315/868 MHz receive via `rtl_433`. |
| **Si5351 + PE4302** | Optional — RF signal source + step attenuator. |
| **Jumper wires** | Optional — Pi GPIO to the board's EN and BOOT pins. |

Raspberry Pi OS Lite (64-bit), Python 3.9+. On the client side: `pyserial`, plus
`esptool` if you want to flash.

## 🚀 Quick Start

```bash
git clone https://github.com/SensorsIot/Universal-Embedded-Workbench.git
cd Universal-Embedded-Workbench/pi
sudo bash install.sh
```

That installs every dependency (pyserial, hostapd, dnsmasq, bleak, esptool,
OpenOCD, rtl-sdr/rtl_433, mosquitto), sets up the udev hotplug rules, and starts
the portal as a systemd service. Then plug in a board and check:

```bash
curl http://workbench.local:8080/api/devices | jq
```

> **On a Pi Zero 2 W, do the memory hardening first.** With 512 MB the board
> OOM-crashes under load, and hard crashes corrupt the SD card. See
> [User Manual §2.2](docs/Embedded-Workbench-User-Manual.md#22-first-boot--system-hardening).

## ⚙️ Configuration

None required — slots are auto-detected. Create `/etc/rfc2217/workbench.json`
only to rename slots, pin specific TCP/GDB ports, declare the GPIO pins you wired,
or register an ESP-Prog probe. Print a ready-to-paste config from whatever is
currently plugged in:

```bash
sudo rfc2217-learn-slots
```

Details, plus the separate `signalgen.json` and `sdr.json`, are in
[User Manual §2.5](docs/Embedded-Workbench-User-Manual.md#25-optional-pin-usb-slots).

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

**Attach a debugger.** OpenOCD is already running:

```bash
riscv32-esp-elf-gdb build/project.elf \
  -ex "target extended-remote workbench.local:3333"
```

**Write a test that uses the whole bench** — reset the board, give it a WiFi
network to join, wait for it to appear, then talk to it:

```python
from workbench_driver import WorkbenchDriver
wt = WorkbenchDriver("http://workbench.local:8080")

wt.serial_reset("SLOT1")
wt.serial_monitor("SLOT1", pattern="WiFi connected", timeout=30)

wt.ap_start("TestAP", "password123")
station = wt.wait_for_station(timeout=30)
wt.http_get(f"http://{station['ip']}/status")

wt.sdr_capture(freq_hz=433_920_000, duration_s=10)
```

## 🤖 Driving It From Claude

The bench ships an MCP server that exposes the whole API as **70 tools**, so
Claude Desktop or Claude Code can operate it conversationally — "flash this to
slot 1 and tell me why it's crashing". It's pure Python standard library, so
there's nothing to `pip install`.

For Claude Desktop, drag
[`mcp/universal-embedded-workbench.mcpb`](mcp/universal-embedded-workbench.mcpb)
onto **Settings → Extensions** and enter your workbench URL.

The repo also carries Claude Code skills under `.claude/skills/` covering the
build/flash lifecycle, logging, WiFi, BLE, MQTT, debug, RF, and test workflows.
Setup for both:
[User Manual §15](docs/Embedded-Workbench-User-Manual.md#15-driving-the-bench-from-claude).

## 🩺 Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Device not detected | Charge-only USB cable | Use a data cable; check `lsusb` on the Pi |
| Connection refused on port 5000 | Wrong port | The portal is on **8080** |
| `Wrong boot mode (0x13)` when flashing | Bridge-chip board — RFC2217 can't drive its auto-reset | Flash with `POST /api/flash` instead |
| Rapid connect/disconnect | Erased or corrupt flash, boot loop | Auto-recovers via GPIO; force with `POST /api/serial/recover` |
| ESP32-C3 stuck in download mode | DTR asserted when the port opened | `POST /api/serial/reset` |
| GDB won't connect | Classic ESP32 has no USB-JTAG | Wire an ESP-Prog and declare it in `workbench.json` |
| SDR decodes noise or all zeros | Transmitter too close, AGC overloading | Add distance, set a fixed `gain` |
| Pi reboots at random | Out of memory (Pi Zero 2 W) | Apply the §2.2 hardening; check `free -h` |

The full table, with the diagnostics to run on the Pi, is in
[User Manual §17](docs/Embedded-Workbench-User-Manual.md#17-troubleshooting).

## 📡 Under the Hood

Serial travels over **[RFC2217](https://www.rfc-editor.org/rfc/rfc2217)**, a
Telnet extension that carries serial line control — baud rate, DTR, RTS — over
TCP. That's why it needs no kernel modules and passes through firewalls, and why
`esptool` and `pyserial` speak it natively.

Hotplug is event-driven, not polled: a **udev** rule fires on USB add/remove and
POSTs to the portal, which starts or stops that slot's proxy. Station events on
the test AP arrive the same way, via **dnsmasq** DHCP lease callbacks.

Boards with native USB-Serial/JTAG (ESP32-C3/S3) need care — Linux asserts DTR
and RTS the moment the port is opened, which drops the chip into download mode
mid-boot. The portal delays opening and drives the reset sequence itself.

Everything is one JSON HTTP API on `:8080`; every response carries `"ok"`.

```bash
curl http://workbench.local:8080/api/devices              # discovery
curl -X POST .../api/wifi/ap_start -d '{"ssid":"TestAP","password":"secret"}'
curl -X POST .../api/gpio/set      -d '{"pin":18,"value":0}'
curl -X POST .../api/sdr/capture   -d '{"freq_hz":433920000,"duration_s":10}'
```

**Full endpoint reference →
[FSD Appendix D](docs/Embedded-Workbench-FSD.md#appendix-d-http-api--mcp-reference)**

## 🌐 Network & Ports

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| 8080 | TCP/HTTP | Clients → Pi | Web portal, REST API, firmware downloads |
| 4001+ | TCP/RFC2217 | Clients → Pi | Serial (`4000 + slot index`) |
| 3333+ | TCP/GDB | Clients → Pi | GDB (`3332 + slot index`) |
| 4444+ | TCP/telnet | Clients → Pi | OpenOCD telnet (`4443 + slot index`) |
| 5555 | UDP | Boards → Pi | Debug log receiver |
| 1883 | TCP/MQTT | Boards → Pi | Test broker (when started) |

## 📁 Files

```
pi/
  portal.py                  HTTP server, proxy supervisor, all API endpoints
  plain_rfc2217_server.py    RFC2217 proxy with DTR/RTS passthrough
  *_controller.py            wifi · ble · mqtt · sdr · debug backends
  signal_generator.py        RF source: Si5351 + PE4302, GPCLK fallback
  install.sh                 One-command installer
  config/ · udev/ · systemd/ Defaults · hotplug rules · service unit
pytest/                      WorkbenchDriver + the test suite
mcp/                         MCP server and Claude Desktop extension
test-firmware/               ESP-IDF firmware that exercises the whole bench
.claude/skills/              Claude Code skills for driving the workbench
docs/                        User Manual + Functional Specification
```

## 📚 Documentation

Two documents, and everything is in one of them:

| Document | Read it for |
|----------|-------------|
| **[User Manual](docs/Embedded-Workbench-User-Manual.md)** | Building the Pi, wiring, and driving every service — install, serial, flashing, debug, WiFi, RF, test automation, troubleshooting. |
| **[Functional Specification](docs/Embedded-Workbench-FSD.md)** | What the bench does, clause by clause. Appendix D is the complete HTTP API and MCP tool reference. |

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
