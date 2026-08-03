# Domain Pack: ESP32 Firmware

Domain-specific guidance for ESP32 projects (ESP-IDF or Arduino-ESP32). Load this
pack **only** when the project matches the detection signals below; otherwise the
platform-independent core (`references/test-architecture.md`) is enough.

## Detection signals

Treat the project as ESP32 firmware if any of these are present:

- Files: `sdkconfig`, `sdkconfig.defaults`, `platformio.ini`, `partitions*.csv`,
  `idf_component.yml`, `CMakeLists.txt` with `idf_component_register`.
- Code/symbols: `esp_`, `ESP_LOG`, `nvs_`, `esp_wifi`, `esp_mqtt`, `esp_ota`,
  `NimBLE`/`esp_ble`, `tinyusb`/`tusb_`, `app_main`, FreeRTOS tasks.
- Description mentions: ESP32 / ESP32-C3/S3/etc., ESP-IDF, Arduino-ESP32, a named
  dev board, or the chip's peripherals.

## ESP-IDF 6.x

Assume **ESP-IDF 6.x** unless the project pins otherwise (`idf_component.yml`,
CI config, or an explicit statement). Four changes from 5.x are load-bearing when
specifying or reviewing a project, and all four are silent until a build fails:

| Change | Consequence |
|--------|-------------|
| **CMake minimum is 3.22** | A project carrying `cmake_minimum_required(VERSION 3.16)` from a 5.x template fails to configure. |
| **cJSON is no longer bundled** | The in-tree `json` component is gone; anything including `cJSON.h` needs `espressif/cjson` in `main/idf_component.yml`, and the first build needs network access to the component registry. |
| **mDNS is not bundled** | Resolving a `.local` name needs the `espressif/mdns` managed component. Prefer an IP literal where the dependency is not wanted. |
| **Managed components must be solved** | Adding `idf_component.yml` to an already-configured project does nothing until the build directory is removed or `reconfigure` is run — the cached CMake configure skips the solver. |

State the IDF major version in the FSD's dependencies, and commit
`dependencies.lock` (not `managed_components/`) so builds are reproducible.

## Layer profile (for FSD §2.4)

Embedded layer contents — apply the core ownership rule (library/managed client to
an external service = foundation; hand-written decoder/driver/handler = interface):

- **L0 — Foundation / transport**: WiFi, VPN (e.g. WireGuard), the MQTT *client*,
  NVS/flash, the RTOS (boot + scheduling), `esp_http_client`/server stacks. Tested
  transitively.
- **L1 — Interfaces**: hand-written protocol decoders (DLMS/OBIS, custom UART
  framing), bus drivers (Modbus, I²C/SPI device drivers), device HTTP handlers
  (captive portal, status portal, OTA receiver), provisioning client. Pure
  converter/policy core on the host tier; wire/flow on target/bench.
- **L2 — Application logic**: control loops, state machines, scheduling/decision
  logic. Pure functions on the host tier.

These three are the common default. A project may **add layers** if it genuinely
has more one-way-dependent tiers (e.g. a device-orchestration layer above several
control loops) — see `../test-architecture.md` ("Scale the layer count to the
system"). Each layer becomes its own body Part, and the source layout mirrors it
(one module per component; see "Source layout mirrors the layers").

## Test tiers (for the §x.0 Test Architecture, in the V&V chapter)

| Tier | Runs on | Speed | Catches |
|---|---|---|---|
| **host** | Dev machine, plain `gcc`/host build | ms, every commit | Pure logic: parsing, encoding, math, lookups, bounds. No ESP-IDF, no hardware. |
| **target** | The ESP32, real ESP-IDF | seconds, pre-merge | UART/I²C/SPI timing, NVS, the HTTP server, flash writes, RTOS behaviour. |
| **bench** | Device + real peers (sensors, broker, server) | minutes, pre-release | End-to-end; recovery, reconnection, timing. |
| **other** | — | — | Non-firmware (server/CI/silicon) or review-only. |

Extract each interface's pure core as a free function (e.g. a size/range
predicate separate from its HTTP/flash handler) so it is host-testable.

## Standard test libraries

A domain pack **proposes**. It never adopts. Everything below is a library of
things that *often* matter for ESP32 firmware — not a statement about this
product. Detecting `esp_mqtt` in the source proves the project speaks MQTT; it
does not prove the product owes anyone offline buffering, ordered replay, command
acknowledgement, or a configuration button.

Silent adoption is how a 12-requirement device acquires 60 requirements nobody
asked for, each of which then demands tests, implementation, and maintenance.

| Feature | Detection Patterns | Test Spec | Include |
|---------|-------------------|-----------|---------|
| **WiFi STA** | `WiFi.begin`, `esp_wifi_connect`, "STA mode" | `esp32/wifi-test-spec.md` | WIFI-001–005, EC-100–101, EC-110–111, EC-115 |
| **Captive Portal** | `WiFi.softAP`, "captive portal", "AP mode" | `esp32/captive-portal-test-spec.md` | AP-001–006, CP-001–006, TC-CP-100–102 |
| **MQTT** | `PubSubClient`, `esp_mqtt`, "MQTT broker" | `esp32/mqtt-test-spec.md` | MQTT-001–031, TC-MQTT-100–103 |
| **BLE** | `NimBLE`, `esp_ble`, `BLEDevice`, "BLE", "GATT" | `esp32/ble-test-spec.md` | BLE-001–032, TC-BLE-100–103 |
| **BLE NUS** | `NUS`, `6E400001`, "Nordic UART" | `esp32/ble-test-spec.md` | BLE-020–023, TC-BLE-101 |
| **OTA** | `esp_ota`, `httpUpdate`, "firmware update", "OTA" | `esp32/ota-test-spec.md` | OTA-001–013, TC-OTA-100–102 |
| **USB HID** | `tinyusb`, `tusb_`, "HID", "keyboard", "USB device" | `esp32/usb-hid-test-spec.md` | HID-001–022, TC-HID-100–103 |
| **NVS** | `Preferences`, `nvs_`, "NVS", "stored credentials" | `esp32/nvs-test-spec.md` | NVS-001–024, TC-NVS-100–103 |
| **Watchdog** | `esp_task_wdt`, `TWDT`, "watchdog" | `esp32/watchdog-test-spec.md` | WDT-001–022, TC-WDT-100–102 |
| **Logging** | `ESP_LOG`, `udp_log`, "UDP logging", "serial log" | `esp32/logging-test-spec.md` | LOG-001–026, TC-LOG-100–103 |
| **Ethernet** | `W5500`, `ETH.begin`, "dual network" | `esp32/wifi-test-spec.md` | TEST-001–005, EC-100 |

### Workflow — propose, then gate

1. Scan the FSD requirements and source code for the detection patterns above.
2. For each detected feature, read the corresponding `references/domains/esp32/*.md`.
3. **Present the candidates to the user as a proposal, not as content.** Group them
   by feature and ask which to adopt. Use `AskUserQuestion` with a recommendation,
   the way §4.2 requires; for a long list, present the table and ask for exclusions.
4. Write **only** the accepted items into the FSD, each carrying its provenance
   (below). Record the rejected ones in **§5 Risks, Assumptions & Dependencies**
   under *Explicitly out of scope*, so a later reader can see the choice was made
   rather than overlooked.
5. Bind every `{{parameter}}` the accepted items carry (next section). An unbound
   parameter is an incomplete FSD — the §13 quality checklist fails on it.
6. Place accepted tests in the spec files mirroring their chapters; the generated
   traceability matrix picks them up (never hand-edit the matrix).

### Provenance — every requirement says where it came from

Tag each requirement in the FSD so its authority is visible:

| Tag | Meaning | Can it be dropped? |
|-----|---------|--------------------|
| `[user]` | Stated by the user, directly | Only by the user |
| `[derived]` | A logical consequence of a `[user]` requirement | Only if its parent changes |
| `[code]` | Observed in the existing implementation | Yes — but flag it, since dropping means removing working behaviour |
| `[pack:esp32]` | Proposed by this domain pack and **accepted** by the user | Yes, freely |

Anything a pack proposed and the user did not accept never enters the document.

### Parameter binding

Spec files in this pack use `{{parameter}}` for values that are genuinely
project-specific. They are deliberately unbound — a reusable library cannot know
your deadlines. Bind each one when the tests are adopted:

| Parameter | Meaning | Typical |
|-----------|---------|---------|
| `{{reconnect_deadline_s}}` | Max seconds from peer returning to service resuming | 30 |
| `{{offline_buffer_depth}}` | Messages retained while disconnected, before the oldest is dropped | 50 |
| `{{boot_deadline_s}}` | Max seconds from reset to the device reaching its first steady state | 10 |
| `{{ble_idle_timeout_s}}` | Idle GATT seconds before the device drops the link | 60 |
| `{{ota_max_stall_ms}}` | Worst-case added application latency during an OTA download | 100 |

The "typical" column is a starting point for the conversation, **not** a default to
apply silently — the same rule as the requirements themselves.

### Spec files

All under `references/domains/esp32/`:

| File | Coverage |
|------|----------|
| `wifi-test-spec.md` | WiFi STA connection, signal, DHCP, ethernet test mode |
| `captive-portal-test-spec.md` | AP mode, captive portal, provisioning, credential change |
| `mqtt-test-spec.md` | Broker connection, pub/sub, QoS, LWT, reconnect, buffering |
| `ble-test-spec.md` | BLE advertising, GATT, NUS, pairing, coexistence |
| `ota-test-spec.md` | OTA download, rollback, integrity, power loss recovery |
| `usb-hid-test-spec.md` | USB enumeration, keyboard layouts, latency, stuck key prevention |
| `nvs-test-spec.md` | Config persistence, factory reset, corruption recovery, credentials |
| `watchdog-test-spec.md` | Software/hardware WDT, memory watchdog, false trigger prevention |
| `logging-test-spec.md` | Serial logging, UDP logging, log levels, crash capture |
