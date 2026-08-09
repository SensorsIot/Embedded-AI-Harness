# The bench DUT: what it is for, test by test

The bench owns one ESP32 of its own — `test-firmware/`, built by CI, flashed
by the bench, currently the ESP32-S3 in SLOT4. This page says what each of
the 98 bench tests needs from it, so its firmware is driven by the suite's
demands rather than by whatever seemed useful at the time.

**Why it exists at all.** A workbench test that asserts on a *project's*
firmware goes red when that project ships. It happened twice: the captive
portal test drove an `awning-net` board that later left the bench, and the
serial-write test asserted that an M-Bus simulator answered `status` with
`OK` until the gplug project reflashed it. The bench must be able to answer
its own questions.

## Coverage

`✓` needs the DUT · `–` bench-only, no DUT involved · `SDR` needs a dongle

| # | Class | Tests | DUT? | What the DUT must do |
|---|---|---:|:---:|---|
| 1 | TestBasicProtocol | 2 | – | portal answers, `ok` present |
| 2 | TestSoftAPManagement | 9 | – | the Pi's own AP lifecycle |
| 3 | **TestStationEvents** | 4 | ✓ | **join the bench AP** and hold the association so connect/disconnect/IP events are real |
| 4 | TestSTAMode | 5 | – | the **Pi** joins an external network; no DUT |
| 5 | **TestHTTPRelay** | 7 | ✓ (5 of 7) | **serve HTTP** on a known port and path so the relay has something to reach |
| 6 | TestWiFiScan | 4 | – | the Pi's radio; other APs suffice |
| 7 | TestSiggen | 5 | – | Si5351 + PE4302 |
| 8 | TestRfLoopback | 1 | SDR | bench transmitter → bench receiver |
| 9 | TestMqttBroker | 3 | – | mosquitto on the Pi |
| 10 | **TestCaptivePortal** | 1 | ✓ | **host a provisioning portal**, accept credentials, join what it was given |
| 11 | TestUSBJTAGDebug | 7 | ✓ | be a **native-USB part with built-in JTAG** — nothing is asked of the firmware |
| 12 | TestAutoDebug | 4 | ✓ | same; chip identity detectable over JTAG |
| 13 | **TestPerSlotDebugIsolation** | 2 | ✓✓ | **two** built-in-JTAG boards, of different chip types |
| 14 | TestEndToEnd | 6 | ✓ | accept a flash and **print a known marker** afterwards |
| 15 | TestSerialArchitecture | 8 | ✓ | emit output continuously so buffer, fan-out and monitor have traffic |
| 16 | TestSlotAccessManager | 9 | ✓ | exist in a slot; mode arbitration is bench-side |
| 17 | TestBenchReset | 4 | ✓ | exist in a slot |
| 18 | **TestSerialWrite** | 5 | ✓ | **answer a written command** — FR-030's only real proof |
| 19 | TestApiSurface | 8 | ✓ (most) | be flashable and readable |
| 20 | TestFlashEndpoint | 4 | ✓ | accept a flash at declared offsets |

**Totals:** 98 tests. Roughly 60 need a DUT present; **17 need it to *do*
something** (rows 3, 5, 10, 13, 14, 18).

## What the firmware therefore provides

| Capability | Serves | Status |
|---|---|---|
| Captive portal — hosts an AP, takes credentials, reboots into STA | rows 3, 5, 10 | built |
| HTTP server on `:8080` (`/status`, `/ota`, `/wifi-reset`) | row 5 | built |
| Heartbeat on serial, every 10 s | rows 14, 15 | built |
| **Serial console** — `ping`→`OK pong`, `status`, `wifi`, `forget`, `reboot` | row 18, and provisioning without the radio | built, first CI build green pending |
| Built-in USB-JTAG (a property of the part, not the firmware) | rows 11, 12, 13 | inherent |
| BLE advertisement, off while the portal needs the radio | future BLE tests | built |

## Two gaps this list makes visible

**Row 13 needs a second board.** Per-slot debug isolation cannot be tested
with one JTAG part, and it exists precisely because two boards sharing
VID:PID `303a:1001` were being confused for each other. One S3 leaves it
untestable. A second native-USB part — any of C3/S3/C6/H2, ideally a
different type — is the cheapest coverage on this page.

**BLE has no tests.** The firmware advertises and the bench can scan, but no
test asserts on it. That is a gap in the suite, not in the DUT.

## Why serial console before anything else

Everything above depends on provisioning, and provisioning depended on the
radio: credentials arrived only through the DUT's own captive portal. When
an S3 stopped transmitting there was no way in at all — and, worse, no way
to tell *the AP is broken* from *the AP is fine and the Pi cannot hear it*.
The console is a wire. It answers that question directly and it provisions
without a beacon.
