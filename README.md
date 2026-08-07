# The Harness — AI Closed-Loop Programming for Embedded Systems

[![host tests](https://img.shields.io/github/actions/workflow/status/SensorsIot/Embedded-AI-Harness/ci.yml?branch=main&label=host%20tests)](https://github.com/SensorsIot/Embedded-AI-Harness/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-c51a4a)
![ESP32](https://img.shields.io/badge/ESP32-supported-green)
![MCP](https://img.shields.io/badge/MCP-70%20tools-8a63d2)

*Spec to silicon, hands off.*

A horse is strong, fast, and willing — and useless for heavy loads until you
harness it. The harness is not a part of the horse and not a part of the cart:
it is the coupling that turns raw strength into pulled weight.

An AI is the same. It can write firmware all day — but it can't flash a board,
can't see it boot, can't know whether its fix actually worked on real
hardware. Unharnessed, it generates code and hopes. This repository is the
harness: strap the AI in, and it pulls — writes the code, compiles it, flashes
it onto a real ESP32, tests it against real WiFi, MQTT, BLE and RF, reads the
failures, corrects itself, and goes again — until the tests run clean.

## 🔄 AI Closed-Loop Programming

Today's AI coding is **open-loop**: prompt → code → hope. No feedback, so
errors accumulate uncorrected — which is exactly why people don't trust
AI-written firmware. **AI Closed-Loop Programming (AICLP)** closes the loop
with reality:

```
            FSD  ──────  the setpoint: what "done" means
             │
             ▼
   ┌──── code → build → flash ────┐        forward path
   │                              ▼
   │                        real hardware
   │                              │
   └── correct ◄── tests ◄────────┘        feedback path

        the loop exits when the error signal is zero: tests green
```

Every embedded engineer knows this diagram — it's a control loop. The spec
(FSD) is the setpoint, the firmware on the chip is the plant, the tests are
the sensor, failing tests are the error signal, and the AI is the controller
that corrects until the error reaches zero.

**True TDD, enabled by AI.** For twenty-five years, developers drove and tests
advised — written after the code, skipped under deadline, tuned until they
passed. Here the tests drive for the first time: derived from the spec, run on
real silicon, and the only way the AI gets to stop.

## 🗺️ The Journey — from idea to shipped product

| Phase | You do | You get | Gate |
|-------|--------|---------|------|
| **0 · Definition** — `/define` | Describe the product; answer an interview, one question at a time | An FSD where every requirement already says how it will be proven | Load defined |
| **1 · Harness** — `/harness` | One command; answer the two questions only you can | The project strapped in: docs, test plan, firmware hooks, CI, runner | AI harnessed |
| **2 · Commissioning** — `/commission` | Plug the board into a slot, wire any peers | Your board and peers proven working here — a failing test now means the code | Testbench trusted |
| **3 · Build** — `/build` | Start sessions; approve the occasional spec question | Requirements turning green, one by one, on real hardware | Ready for shipment |
| **⚑ Shipment** — `git tag` | Push the version tag — the one act that stays human | A release built in a pinned container and verified on the testbench: the journey runs once more on the exact bytes users download | Shipped |

Each phase ends at a **gate**, derived from project state and never declared —
nobody types "phase complete". A gate is not a marker you pass: if anything it
requires is unmet, the work loops back to the step that owns it and the whole
check runs again. And after shipment the same journey repeats in
miniature for every new feature: describe it in a sentence, the loop refuses
to code anything no requirement covers, the spec absorbs the delta, and the
phases collapse to minutes. **No code without a clause** is what keeps the
spec true for the product's whole life.

## 🧰 What the Harness consists of

- **The method** — four Claude Code skills, one per phase: `/define` (the
  FSD: atomic, falsifiable requirements, each with its verification
  contract), `/harness` (one-time setup), `/commission` and `/build` (the
  loop's driver: test design, the plan, audit, what's next).
- **The workbench** — a Raspberry Pi test instrument that gives the AI hands
  and eyes on real hardware. Described below.
- **The dev skills** — ESP-IDF and PlatformIO lifecycles, logging, WiFi,
  BLE, MQTT, debugging, RF, CI — the loop's individual muscles.

## ✅ Prerequisites — what the loop needs

| You need | For | Where |
|---|---|---|
| A **Raspberry Pi workbench** (Pi 3/4/5, or Zero 2 W + USB hub + Ethernet adapter) with an ESP32 board in a slot | The loop's hands and eyes — flash, reset, observe on real hardware | Build it: [Quick Start](#-quick-start--building-the-bench) below |
| A **GitHub account**, `git` + `gh` authenticated | CI builds, releases, and the release-verify runner | [github.com](https://github.com) |
| **Claude Code** with this repo's skills | The AI that pulls; the skills are the method | `npm i -g @anthropic-ai/claude-code`, then copy `.claude/skills/` from this repo into your project |
| **Same LAN** | Your dev machine or devcontainer must reach the bench | `curl http://workbench.local:8080/api/devices` answers |
| For your project: **ESP-IDF or PlatformIO** toolchain | The forward path — the `esp-idf-handling` / `esp-pio-handling` skills set this up | Handled during Phase 1 |

Nothing else. The FSD, tests, firmware, CI and documentation are what the loop
*produces*, not what you bring.

## 🔌 The Workbench — the loop's hands and eyes

Working on an ESP32 normally means being physically attached to it — and an
AI can't hold a USB cable. The workbench puts the boards on a Raspberry Pi
and turns everything into HTTP:

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

- **Plug in a board → it's ready.** Auto-detected in seconds and mapped to a
  fixed port by which USB connector it's in — same connector, same port,
  always. That's **slot-based identity**: a slot is a physical hole in the
  hub, so scripts and `platformio.ini` never go stale when boards swap or the
  kernel renames `/dev/ttyACM0`.
- **Serial over the network** at `rfc2217://workbench.local:4001` — esptool,
  PlatformIO, ESP-IDF and anything on pyserial speak it natively.
- **Flash three ways** — over the network, locally on the Pi, or over the air.
- **Debugging out of the box** — OpenOCD starts itself for USB-JTAG chips;
  GDB connects to port 3333.
- **The Pi is the test equipment.** Its WiFi becomes the access point your
  board joins, its Bluetooth scans and connects, optional SDR and Si5351
  hardware receive and transmit on 433 MHz, and boards log to it over UDP
  when USB is busy.
- **It presses the buttons.** GPIO wired to reset and boot forces download
  mode and rescues boot-looping boards with nobody in the room.
- **Claude drives all of it** through 70 MCP tools or the bundled skills.

Honest limits: **one serial client per board at a time** (that's RFC2217, not
a choice), the SDR is **one dongle, one user**, and the API has **no
authentication** — keep the bench on a network you trust.

## 🚀 Quick Start — building the bench

You need a Raspberry Pi with onboard WiFi and Bluetooth running Raspberry Pi
OS Lite (64-bit). A Pi Zero 2 W also needs a USB hub and a USB Ethernet
adapter, since wlan0 is reserved for testing; a Pi 3/4/5 has both built in.
An RTL-SDR dongle, an Si5351 + PE4302, and jumper wires to the board's
EN/BOOT pins are all optional.

```bash
git clone https://github.com/SensorsIot/Embedded-AI-Harness.git
cd Embedded-AI-Harness/pi
sudo bash install.sh
```

That installs every dependency (pyserial, hostapd, dnsmasq, bleak, esptool,
OpenOCD, rtl-sdr/rtl_433, mosquitto), sets up the udev hotplug rules, and
starts the portal as a systemd service. Plug in a board and check:

```bash
curl http://workbench.local:8080/api/devices | jq
```

Slots are auto-detected — no config file needed. Create
`/etc/rfc2217/workbench.json` only to rename slots, pin ports, declare GPIO
pins, or register an ESP-Prog probe; `sudo rfc2217-learn-slots` prints one
for you.

> **On a Pi Zero 2 W, do the memory hardening first.** With 512 MB the board
> OOM-crashes under load, and hard crashes corrupt the SD card. See
> [User Manual §2.2](docs/Harness-User-Manual.md#22-first-boot--system-hardening).

## 🔧 Usage

**Watch a board boot** — no client library, just HTTP:

```bash
curl -X POST http://workbench.local:8080/api/serial/reset \
  -H 'Content-Type: application/json' -d '{"slot":"SLOT1"}'
```

**Point your existing tools at it.** PlatformIO needs one line
(`upload_port = rfc2217://workbench.local:4001`); esptool takes the same URL,
and the binaries stay on your machine:

```bash
esptool --port rfc2217://workbench.local:4001 --chip esp32c3 \
  write-flash 0x10000 firmware.bin
```

**Write a test that uses the whole bench** — reset the board, give it a
network to join, wait for it to appear, then talk to it:

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

An MCP server exposes the whole API as **70 tools**, so Claude Desktop or
Claude Code can operate the bench conversationally — "flash this to slot 1
and tell me why it's crashing". Pure Python standard library, so there's
nothing to `pip install`. For Claude Desktop, drag
[`mcp/embedded-ai-harness-workbench.mcpb`](mcp/embedded-ai-harness-workbench.mcpb)
onto **Settings → Extensions** and enter your workbench URL.

The AICLP skills (`/define`, `/harness`, `/commission`, `/build`) and the
instrument skills all live under `.claude/skills/`. Setup for both:
[User Manual §15](docs/Harness-User-Manual.md#15-driving-the-bench-from-claude).

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
[User Manual §17](docs/Harness-User-Manual.md#17-troubleshooting).

## 📡 Under the Hood

Serial travels over **[RFC2217](https://www.rfc-editor.org/rfc/rfc2217)**, a
Telnet extension that carries serial line control — baud rate, DTR, RTS —
over TCP. That's why it needs no kernel modules and passes through firewalls,
and why esptool and pyserial speak it natively.

Hotplug is event-driven, not polled: a **udev** rule fires on USB add/remove
and POSTs to the portal, which starts or stops that slot's proxy. Station
events on the test AP arrive the same way, via **dnsmasq** DHCP lease
callbacks. Boards with native USB-Serial/JTAG need care — Linux asserts DTR
and RTS the moment the port opens, dropping the chip into download mode
mid-boot — so the portal delays opening and drives the reset sequence itself.

Everything is one JSON HTTP API on `:8080`; every response carries `"ok"`.

```bash
curl -X POST .../api/wifi/ap_start -d '{"ssid":"TestAP","password":"secret"}'
curl -X POST .../api/gpio/set      -d '{"pin":18,"value":0}'
curl -X POST .../api/sdr/capture   -d '{"freq_hz":433920000,"duration_s":10}'
```

## 📚 Documentation

The plane map is [`docs/00-Overview.md`](docs/00-Overview.md) — three
documents, one per question, and everything is in one of them:

| Question | Document | Read it for |
|----------|----------|-------------|
| **What must be true?** | **[Functional Specification](docs/Harness-FSD.md)** | AICLP, the journey, and what the bench does clause by clause. [Appendix D](docs/Harness-FSD.md#appendix-d-http-api--mcp-reference) is the complete HTTP API and MCP tool reference. |
| **How is it built?** | **[Method](docs/Method/00-Overview.md)** | The build contract for contributors and AI agents — [workflow](docs/Method/AI-Workflow.md), [architecture](docs/Method/project/architecture.md), conventions, testing standard. |
| **How do I run it?** | **[User Manual](docs/Harness-User-Manual.md)** | Building the Pi, wiring, and driving every service — install, serial, flashing, debug, WiFi, RF, test automation, troubleshooting. |

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
