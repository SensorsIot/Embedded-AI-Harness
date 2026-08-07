# Domain Pack: ESP32 Firmware

Domain-specific guidance for ESP32 projects (ESP-IDF or Arduino-ESP32). Load this
pack **only** when the project matches the detection signals below; otherwise the
platform-independent core (`../../../build/references/test-architecture.md`) is enough.

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
CI config, or an explicit statement). Five changes from 5.x are load-bearing when
specifying or reviewing a project, and all five are silent until a build fails:

| Change | Consequence |
|--------|-------------|
| **CMake minimum is 3.22** | A project carrying `cmake_minimum_required(VERSION 3.16)` from a 5.x template fails to configure. |
| **cJSON is no longer bundled** | The in-tree `json` component is gone; anything including `cJSON.h` needs `espressif/cjson` in `main/idf_component.yml`, and the first build needs network access to the component registry. |
| **mDNS is not bundled** | Resolving a `.local` name needs the `espressif/mdns` managed component. Prefer an IP literal where the dependency is not wanted. |
| **esp-mqtt is not bundled** | There is no `mqtt` component in the v6.0.2 image — `tcp_transport` and `esp_https_ota` are there, `mqtt` is not. `PRIV_REQUIRES mqtt` fails at *configure* time with "Component directory … does not contain a CMakeLists.txt file", which reads like a broken submodule rather than a missing dependency. Any project speaking MQTT needs the managed component declared before its first build. |
| **Managed components must be solved** | Adding `idf_component.yml` to an already-configured project does nothing until the build directory is removed or `reconfigure` is run — the cached CMake configure skips the solver. |

**Declare requirements only for what the code includes today.** ESP-IDF resolves
`PRIV_REQUIRES` at configure time, so a speculatively-listed component breaks the
build for functionality that does not exist yet — and the error names the
component, not the speculation, so it is read as a toolchain fault. Add each
requirement with the phase that needs it.

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
control loops) — see `../../../build/references/test-architecture.md` ("Scale the layer count to the
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

| Feature | Detection Patterns | Test-case library | Include |
|---------|-------------------|-----------|---------|
| **WiFi STA** | `WiFi.begin`, `esp_wifi_connect`, "STA mode" | `esp32/wifi-test-cases.md` | WIFI-001–005, EC-100–101, EC-110–111, EC-115 |
| **Captive Portal** | `WiFi.softAP`, "captive portal", "AP mode" | `esp32/captive-portal-test-cases.md` | AP-001–006, CP-001–006, TC-CP-100–102 |
| **MQTT** | `PubSubClient`, `esp_mqtt`, "MQTT broker" | `esp32/mqtt-test-cases.md` | MQTT-001–031, TC-MQTT-100–103 |
| **BLE** | `NimBLE`, `esp_ble`, `BLEDevice`, "BLE", "GATT" | `esp32/ble-test-cases.md` | BLE-001–032, TC-BLE-100–103 |
| **BLE NUS** | `NUS`, `6E400001`, "Nordic UART" | `esp32/ble-test-cases.md` | BLE-020–023, TC-BLE-101 |
| **OTA** | `esp_ota`, `httpUpdate`, "firmware update", "OTA" | `esp32/ota-test-cases.md` | OTA-001–013, TC-OTA-100–102 |
| **USB HID** | `tinyusb`, `tusb_`, "HID", "keyboard", "USB device" | `esp32/usb-hid-test-cases.md` | HID-001–022, TC-HID-100–103 |
| **NVS** | `Preferences`, `nvs_`, "NVS", "stored credentials" | `esp32/nvs-test-cases.md` | NVS-001–024, TC-NVS-100–103 |
| **Watchdog** | `esp_task_wdt`, `TWDT`, "watchdog" | `esp32/watchdog-test-cases.md` | WDT-001–022, TC-WDT-100–102 |
| **Logging** | `ESP_LOG`, `udp_log`, "UDP logging", "serial log" | `esp32/logging-test-cases.md` | LOG-001–026, TC-LOG-100–103 |
| **Ethernet** | `W5500`, `ETH.begin`, "dual network" | `esp32/wifi-test-cases.md` | TEST-001–005, EC-100 |

### Workflow — propose, then gate

1. Scan the FSD requirements and source code for the detection patterns above.
2. For each detected feature, read the corresponding `references/domains/esp32/*.md`.
3. **Ask about depth before asking about content.** A full match across five or six
   features is 100+ cases, and most of them assert response shape rather than
   behaviour. Offer the choice as one `AskUserQuestion`, recommending the middle:
   *curated subset* (only cases that can fail for this product, each traceable to a
   stated decision) · *full families* · *decisions-only* (no pack cases at all).
   Asking family-by-family instead produces a long interrogation whose answer is
   almost always "some of each".
4. **Then run the pack backwards, as a gap detector.** Ask what the pack flagged
   that the decisions never mention. A detected feature the user never discussed is
   either genuinely out of scope or a capability nobody thought about — and the
   second is where the pack earns its keep. A watchdog on an unattended device is
   the recurring example: nobody asks for it, and without it any hang costs a site
   visit. Present these as a separate short question, not buried in the depth one.
5. Write **only** the accepted items into the FSD, each carrying its provenance
   (below). Record the rejected ones in **§5 Risks, Assumptions & Dependencies**
   under *Explicitly out of scope*, so a later reader can see the choice was made
   rather than overlooked.
6. Bind every `{{parameter}}` the accepted items carry (next section). An unbound
   parameter is an incomplete FSD — the finalisation checklist fails on it.
7. Accepted cases become entries in the project's test plan, declared by
   `/build` with their tier, equipment and expectations; traceability is
   computed from the plan, never hand-maintained.

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

### Test-case libraries

All under `../../../build/references/domains/esp32/` — they live with the
Method skill because they are test proposals, consumed at declaration time:

**These files are a library of proposed test cases, not a specification format.**
Take the cases that apply, declare each as an entry in the project's plan file
with its tier, the equipment it needs and what it expects, and drop the rest. A
pack proposes; it never adopts — and it never introduces a second place where
tests are described.


| File | Coverage |
|------|----------|
| `wifi-test-cases.md` | WiFi STA connection, signal, DHCP, ethernet test mode |
| `captive-portal-test-cases.md` | AP mode, captive portal, provisioning, credential change |
| `mqtt-test-cases.md` | Broker connection, pub/sub, QoS, LWT, reconnect, buffering |
| `ble-test-cases.md` | BLE advertising, GATT, NUS, pairing, coexistence |
| `ota-test-cases.md` | OTA download, rollback, integrity, power loss recovery |
| `usb-hid-test-cases.md` | USB enumeration, keyboard layouts, latency, stuck key prevention |
| `nvs-test-cases.md` | Config persistence, factory reset, corruption recovery, credentials |
| `watchdog-test-cases.md` | Software/hardware WDT, memory watchdog, false trigger prevention |
| `logging-test-cases.md` | Serial logging, UDP logging, log levels, crash capture |
