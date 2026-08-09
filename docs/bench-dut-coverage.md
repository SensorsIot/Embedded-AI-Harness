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
| 6 | TestWiFiScan | 4 | – | the Pi's radio; other APs suffice. One radio cannot beacon and survey at once, so a scan while the AP runs is refused with its reason (WT-603) and WT-602's question is unanswerable here |
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

## The S3's role and task, test by test

The bench and the DUT are a **pair**, and the pairing runs in both
directions. Half these tests put the bench on one side of a radio link and
the S3 on the other; which of the two is the access point changes per test,
and getting that backwards makes the whole table unreadable.

| Role | Who is the AP | Who initiates |
|---|---|---|
| **Station** | the bench | the S3 joins |
| **Portal host** | the S3 | the bench joins and fills in the form |
| **HTTP origin** | the bench | the bench requests, the S3 answers |
| **Console responder** | — (a wire) | the bench writes, the S3 answers |
| **Flash target** | — (a wire) | the bench writes, the S3 announces |
| **JTAG target** | — (a wire) | the bench attaches; firmware plays no part |

### Station — the bench is the AP, the S3 joins it (4)

| Test | The S3's task |
|---|---|
| `WT-300` station_connect_event | associate, so the bench's AP raises a connect event carrying its MAC |
| `WT-301` station_disconnect_event | leave (or be left), so the matching disconnect event is raised |
| `WT-302` station_in_ap_status | **hold** the association, so it is still listed when `ap_status` is polled later |
| `WT-303` ip_matches_event | accept the DHCP lease and keep that address, so the event's IP and the lease agree |

### HTTP origin — reachable on the bench's own AP network (4)

| Test | The S3's task |
|---|---|
| `WT-500` get_request | serve `GET /status` with a non-empty body on `:8080` |
| `WT-501` post_with_body | answer a POST to an unimplemented path — a 404 it *chose* proves carriage |
| `WT-502` custom_headers | answer 200 with an unexpected request header present |
| `WT-505` large_response | return a JSON body that survives the relay and still parses |

`WT-503`/`WT-504` need the opposite: an address where nothing answers. They
need no DUT at all.

### Portal host — the S3 is the AP, the bench fills in its form (1)

| Test | The S3's task |
|---|---|
| `WT-2100` provision_and_reach_lan | beacon `WB-Test-Setup`, serve the HTML form, accept `ssid`/`password` POSTed to `/connect`, store them, reboot, and join the network it was handed |

This is the one test where the bench is the *client* of the S3's HTML UI.

### Console responder — the wire, no radio involved (1)

| Test | The S3's task |
|---|---|
| `TestSerialWrite::test_write_reaches_the_device…` | receive `ping\n` on the USB serial port and answer `OK pong` |

The other four `TestSerialWrite` cases check the endpoint's refusals (bad
hex, unknown slot, neither field) and need nothing of the device.

### Flash target and announcer (6)

| Test | The S3's task |
|---|---|
| `WT-1800` flash_and_serial | accept an image at the offsets `flash_args` names, boot, and print a line the bench can match |
| `WT-1801`–`WT-1804` halt/step/memory/breakpoint | run code that can be halted, stepped and read — any firmware will do; it must merely be *running* |
| `WT-1805` flash_preserves_debug | survive a flash while a debug session is held, and come back printing |

### JTAG target — silicon, not firmware (11)

`WT-1400`–`WT-1406` and `WT-1704`/`1705`/`1707`/`1709` need a part with
built-in USB-JTAG whose TAP identifies it. **Nothing is asked of the image**
— an erased S3 passes these. They are listed because the board must be
present and must not be held by another session.

### Two boards, which one S3 cannot be (2)

`TestPerSlotDebugIsolation` needs **two** built-in-JTAG boards, ideally of
different chip types. It exists because two boards sharing VID:PID
`303a:1001` were reported as each other. One S3 can never satisfy it; the
tests skip, and that skip is honest.

**29 tests need the S3 to act.** 18 of them ask only for things the wire
and the silicon provide; 9 need the radio in one direction or the other;
2 need a second board.

## What the firmware therefore provides

| Capability | Serves | Status |
|---|---|---|
| Captive portal — hosts an AP, takes credentials, reboots into STA | rows 3, 5, 10 | built |
| HTTP server on `:8080` (`/status`, `/ota`, `/wifi-reset`) | row 5 | built |
| Heartbeat on serial, every 10 s | rows 14, 15 | built |
| **Serial console** — `ping`, `status`, `scan`, `info`, `mark`, `wifi`, `forget`, `reboot` | row 18, and provisioning without the radio | built |
| **`scan`** — the DUT's own view of the air | telling a deaf receiver from a silent AP | built |
| Built-in USB-JTAG (a property of the part, not the firmware) | rows 11, 12, 13 | inherent |
| BLE advertisement, off while the portal needs the radio | future BLE tests | built |

## What the suite actually produced

98 tests: **88 passed, 0 failed, 10 skipped**, reproduced across three
separate full runs on one ESP32-S3 and an RTL-SDR dongle.

Every skip names an absent instrument or a question this bench cannot ask.
None is a capability that quietly stopped working — which is the failure this
page exists to catch:

| Skips | Reason |
|---:|---|
| 3 | no ESP32-C3 DUT present |
| 2 | FR-037 needs two built-in-JTAG boards; this bench has one |
| 1 | the multi-slot test needs 2+ DUTs |
| 1 | no Si5351 signal generator present |
| 1 | no slot currently holds a debug session |
| 1 | `WIFI_TEST_HTTP_URL` not set |
| 1 | WT-602 needs a scan taken while our own AP beacons — see below |

**Repeatability had to be fixed before any of this meant anything.** One run
passed 74/74 and the next collapsed to 51 passes and 15 failures, on the same
bench, cables and commit. WT-1800 flashes a throwaway image over the bench DUT
to prove flashing works, and nothing put the real one back; the board sat
printing `LOOP: n` and every later test that needed it to *answer* reported
absent hardware. A defined bench (FR-036) is only half a defined starting
state. The suite now restores its own DUT at session start and after the flash
tests.

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
