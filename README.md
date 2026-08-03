# Universal Embedded Workbench

**Plug in any ESP32. Serial and debug are ready instantly. No configuration needed.**

A Raspberry Pi that turns into a complete remote test instrument for ESP32 devices. Plug boards into its USB hub and control everything -- serial, debug, WiFi, BLE, GPIO, SDR, signal generation, firmware updates -- over the network through a single HTTP API (or the MCP server).

Zero-config by design: on boot the portal walks the Pi's USB hub topology and pre-creates one slot per usable hub port (`SLOT1`, `SLOT2`, ...), each mapped to a physical USB connector. Plug in a device and it automatically maps to the correct slot by USB path, gets a serial port, chip identification, and OpenOCD for GDB debugging. Dual-USB boards (ESP32-S3 with sub-hub) are handled transparently -- both interfaces map to the same slot.

---

## Documentation

The project has exactly two documents:

| Document | Read it for |
|----------|-------------|
| **[User Manual](docs/Embedded-Workbench-User-Manual.md)** | How to build the Pi, wire it, and drive every service — installation, serial, flashing, debug, WiFi, RF, test automation, troubleshooting. |
| **[Functional Specification](docs/Embedded-Workbench-FSD.md)** | What the bench does, clause by clause. **[Appendix D](docs/Embedded-Workbench-FSD.md#appendix-d-http-api--mcp-reference)** is the complete HTTP API and MCP tool reference. |

---

## Features

- **Remote serial (RFC2217)** — every USB slot as a network serial port; works with esptool, PlatformIO, ESP-IDF, any pyserial tool.
- **Remote GDB / JTAG debug** — OpenOCD auto-starts per chip (C3/C6/H2/S3 USB-JTAG, dual-USB, ESP-Prog).
- **Flashing** — over USB (RFC2217, or **local-Pi esptool** for CP2102/CH340/CH9102 bridge boards) and **over-the-air** (`POST /api/ota`, espota relayed to deployed on-LAN boards).
- **SDR receiver (RTL-SDR + rtl_433)** — decode / analyze / rtl_power captures, phased `acquire`, a live rtl_433 console, "AI Sherlock" record→reverse-engineer, an rtl_433 device database, and dongle recovery.
- **Signal generator (Si5351 / GPCLK + PE4302)** — continuous carrier, Morse/CW beacon, retune, step attenuation.
- **WiFi test instrument** — SoftAP (optionally NAT-bridged to the LAN), station mode, scan, HTTP relay, and captive-portal provisioning of WiFiManager DUTs.
- **MQTT test broker** — on-demand mosquitto so DUTs on the WiFi AP can run pub/sub integration tests without internet.
- **BLE proxy** — scan / connect / write via the Pi's Bluetooth radio.
- **GPIO control** — drive boot/reset pins to force download mode, simulate buttons.
- **UDP log receiver**, **OTA firmware repository**, and **test-progress + operator-interaction** tracking.
- **Web portal** — live dashboard of slots, WiFi, logs, and test progress.
- **pytest driver** (`WorkbenchDriver`) — all of the above from test scripts.
- **MCP interface** — the entire API as 70 MCP tools for Claude Desktop / Code; one-click `.mcpb` install, no dependencies.

---

## Install

Two independent components — install either alone.

**Pi service** (on the Raspberry Pi):

```bash
git clone https://github.com/SensorsIot/Universal-Embedded-Workbench.git
cd Universal-Embedded-Workbench/pi
sudo bash install.sh
```

The installer sets up all dependencies (pyserial, hostapd, dnsmasq, bleak, esptool, OpenOCD, rtl-sdr/rtl-433, mosquitto), copies scripts to `/usr/local/bin/`, and starts the portal as a systemd service. On a Pi Zero 2 W, apply the memory hardening in **[User Manual §2.2](docs/Embedded-Workbench-User-Manual.md#22-first-boot--system-hardening)** *first* — without it the board will OOM-crash.

**Claude Code skills** (on each dev machine that drives the bench):

```bash
git clone https://github.com/SensorsIot/Universal-Embedded-Workbench.git /tmp/uew
mkdir -p .claude/skills
cp -r /tmp/uew/.claude/skills/. .claude/skills/
rm -rf /tmp/uew
```

Full setup, including the MCP server for Claude Desktop → **[User Manual §15](docs/Embedded-Workbench-User-Manual.md#15-driving-the-bench-from-claude)**.

---

## Hardware

| Component | Purpose |
|-----------|---------|
| **Raspberry Pi** (any model) | Runs the portal. Needs onboard WiFi + Bluetooth. Auto-detects model and USB topology. |
| **USB Ethernet adapter** (Pi Zero 2 W only) | Wired LAN on eth0 (wlan0 is reserved for WiFi testing). Pi 3/4/5 have built-in Ethernet. |
| **USB hub** (Pi Zero 2 W only) | Connect multiple ESP32 boards. Pi 3/4/5 already have 4 USB ports. |
| **RTL-SDR dongle** (optional) | 433/315/868 MHz receive gateway (`rtl_433`). |
| **Si5351 + PE4302** (optional) | RF signal source + step attenuator. |
| **Jumper wires** (optional) | Pi GPIO to DUT GPIO for automated boot mode / reset control. |

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
 :4001 :4002 :4003 :4004  ← auto-assigned (4001 + slot index)
 SLOT1 SLOT2 SLOT3 SLOT4  ← one per detected hub port
```

eth0 carries all management traffic (HTTP API, RFC2217 serial). wlan0 is dedicated to WiFi testing. They never overlap. Slot counts, port assignments, and the phantom-port table are covered in **[User Manual §1](docs/Embedded-Workbench-User-Manual.md#1-what-you-need)** and **[§3](docs/Embedded-Workbench-User-Manual.md#3-network-and-ports)**.

---

## A taste of it

```bash
curl http://workbench.local:8080/api/devices | jq          # what's plugged in

curl -X POST http://workbench.local:8080/api/serial/reset \
  -H 'Content-Type: application/json' -d '{"slot":"SLOT1"}'

esptool --port rfc2217://workbench.local:4001 --chip esp32c3 \
  write-flash 0x10000 firmware.bin
```

```python
from workbench_driver import WorkbenchDriver
wt = WorkbenchDriver("http://workbench.local:8080")

wt.serial_reset("SLOT1")
wt.serial_monitor("SLOT1", pattern="WiFi connected", timeout=30)
wt.ap_start("TestAP", "password123")
station = wt.wait_for_station(timeout=30)
wt.sdr_capture(freq_hz=433_920_000, duration_s=10)
```

---

## Project structure

```
pi/
  portal.py                  Main HTTP server, proxy supervisor, all API endpoints
  wifi_controller.py         WiFi AP/STA/scan/relay backend
  ble_controller.py          BLE scan/connect/write backend (bleak)
  signal_generator.py        Unified RF source: Si5351 (I2C) + optional PE4302, GPCLK fallback
  sdr_controller.py          RTL-SDR receiver: rtl_433 decode/analyze/power/acquire, live console
  si5351.py / pe4302.py / gpclk.py / morse.py   RF driver primitives
  mqtt_controller.py         On-demand mosquitto test broker
  debug_controller.py        GDB debug manager (OpenOCD lifecycle, probe allocation)
  plain_rfc2217_server.py    RFC2217 serial proxy with DTR/RTS passthrough
  bcm_gpio.py                Shared /dev/mem GPIO primitives
  install.sh                 One-command installer
  config/                    workbench.json, signalgen.json, sdr.json, rtl_433.conf
  scripts/                   udev/dnsmasq callbacks + espota.py (used by /api/ota)
  udev/ · systemd/           Hotplug rules · service unit
pytest/
  workbench_driver.py        Python test driver (WorkbenchDriver class)
  conftest.py · workbench_test.py
mcp/
  workbench_mcp.py           MCP server (API → 70 tools, stdlib-only)
  manifest.json · *.mcpb     Claude Desktop extension (one-click install)
test-firmware/               Generic ESP-IDF firmware that exercises the whole bench
.claude/skills/              Claude Code skills for driving the workbench
docs/
  Embedded-Workbench-User-Manual.md   Build it, wire it, drive it
  Embedded-Workbench-FSD.md           Functional spec (Appendix D = API/MCP reference)
```

---

## License

MIT
