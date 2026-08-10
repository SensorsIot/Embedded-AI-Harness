# The test partner: what it must do, test by test

The bench owns one ESP32 of its own — `test-firmware/`, built by CI, flashed
by the bench. Which slot holds it is not written down anywhere on purpose —
boards move, and every fixture discovers the slot by asking. This page says
what each of the bench tests needs from it, so its firmware is driven by the suite's
demands rather than by whatever seemed useful at the time.

**Why it exists at all.** A testbench test that asserts on a *project's*
firmware goes red when that project ships. It happened twice: the captive
portal test drove one project's board that later left the bench, and the
serial-write test asserted that an M-Bus simulator answered `status` with
`OK` until that project reflashed the board. The bench must be able to answer
its own questions.

## Coverage

`✓` needs the partner · `–` bench-only, no partner involved · `SDR` needs a dongle

| # | Class | Tests | Partner? | What the partner must do |
|---|---|---:|:---:|---|
| 1 | TestBasicProtocol | 2 | – | portal answers, `ok` present |
| 2 | TestSoftAPManagement | 9 | – | the Pi's own AP lifecycle |
| 3 | **TestStationEvents** | 4 | ✓ | **join the bench AP** and hold the association so connect/disconnect/IP events are real |
| 4 | **TestSTAMode** | 5 | ✓ (4 of 5) | **host a WPA2 AP of a given name** (`testap`) so the Pi has something to be a station against |
| 5 | **TestHTTPRelay** | 7 | ✓ (5 of 7) | **serve HTTP** on a known port and path so the relay has something to reach |
| 6 | TestWiFiScan | 4 | – | the Pi's radio; other APs suffice. One radio cannot beacon and survey at once, so a scan while the AP runs is refused with its reason (WT-603), and WT-602 asks the answerable form of the question instead: an SSID taken off the air is gone from the next scan |
| 7 | TestSiggen | 5 | – | Si5351 + PE4302 |
| 8 | TestRfLoopback | 1 | SDR | bench transmitter → bench receiver |
| 9 | TestMqttBroker | 5 | – | mosquitto on the Pi — started, stopped, **and asked to carry a message** |
| 10 | **TestCaptivePortal** | 4 | ✓ | **the whole provisioning journey**: raise a portal, accept SSID/password/broker through its form, reboot and join that AP, then publish to that broker |
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

**Totals:** 103 tests. Roughly 60 need the partner present; **21 need it to *do*
something** (rows 3, 4, 5, 10, 13, 14, 18).

## The S3's role and task, test by test

The bench and the partner are a **pair**, and the pairing runs in both
directions. Half these tests put the bench on one side of a radio link and
the S3 on the other; which of the two is the access point changes per test,
and getting that backwards makes the whole table unreadable.

| Role | Who is the AP | Who initiates |
|---|---|---|
| **Station** | the bench | the S3 joins |
| **AP under test** | the S3 | the bench joins, right passphrase and wrong |
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

### AP under test — the S3 is the AP, the bench is the station (4)

The mirror of the previous section, and the reason the S3 has a `testap`
command at all. The bench has **one radio**: it cannot be the access point
its own station tests join, and its provisioning portal — the other AP the
S3 can raise — is open by design, which leaves the WPA2 paths with nothing
to aim at. So the board already under test takes a second job.

`testap <ssid> <password>` stores the request and reboots the S3 into an AP
of that name, WPA2 when the passphrase is at least eight characters and
**refused outright** when it is shorter: an open AP under a name the caller
believes is protected would let a WPA2 test pass having proved nothing. The
request is cleared by the next `wifi` command, so provisioning over serial —
which every fixture already does to recover the partner — puts the board back to
being a station with no second command anyone could forget to send.

| Test | The S3's task |
|---|---|
| `WT-401` join_wpa2_network | beacon `WT-PARTNER-AP` with WPA2-PSK, accept the association, hand out a `192.168.4.x` lease |
| `WT-402` join_wrong_password | **refuse** an association offering the wrong passphrase, while still beaconing — a join that fails because nothing is on the air is WT-403 |
| `WT-404` leave_sta | hold the association long enough for the bench to leave it deliberately |
| `WT-405` softap_stops_during_sta | be there to be joined, so the bench's own AP can be observed going down as it becomes a station |

`WT-403` needs the opposite — an SSID nobody beacons — and so needs no partner.

These four read an SSID and passphrase out of the environment until August
2026 and skipped without them, which meant the station path went unproven on
any bench nobody had hand-configured. The obvious fix, pointing them at the
house network, is the one that cannot work for its neighbour `WT-506`: the
bench's `eth0` is already on that LAN, so the request never crosses the
radio.

### HTTP origin — reachable on the bench's own AP network (4)

| Test | The S3's task |
|---|---|
| `WT-500` get_request | serve `GET /status` with a non-empty body on `:8080` |
| `WT-501` post_with_body | answer a POST to an unimplemented path — a 404 it *chose* proves carriage |
| `WT-502` custom_headers | answer 200 with an unexpected request header present |
| `WT-505` large_response | return a JSON body that survives the relay and still parses |

`WT-503`/`WT-504` need the opposite: an address where nothing answers. They
need no partner at all.

### Portal host — the S3 is the AP, the bench fills in its form (4)

The provisioning journey, one gate per test. This is where the bench is the
*client* of the S3's HTML UI rather than its access point.

| Test | The S3's task |
|---|---|
| `WT-2101` raises a captive portal | beacon `WB-Test-Setup` and serve a form carrying `ssid`, `password` and `broker` |
| `WT-2102` bench fills the form | accept those three POSTed to `/connect` and store them |
| `WT-2103` reboots and joins — **success 1** | come back in station mode and join the network it was handed |
| `WT-2104` publishes — **success 2** | reach the MQTT broker it was given and publish |

It was one test asserting the partner had an address on the bench AP, which it
called "provisioned through its portal". It was not: the fixture behind it
provisions over the serial console first and falls back to the portal only
if that fails, so the portal usually never ran — a test named after a
capability, passing without exercising it.

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

**36 tests need the S3 to act.** 18 of them ask only for things the wire
and the silicon provide; 16 need the radio in one direction or the other;
2 need a second board.

## What the firmware therefore provides

| Capability | Serves | Status |
|---|---|---|
| Captive portal — hosts an AP, takes credentials, reboots into STA | rows 3, 5, 10 | built |
| HTTP server on `:8080` (`/status`, `/ota`, `/wifi-reset`) | row 5 | built |
| Heartbeat on serial, every 10 s | rows 14, 15 | built |
| **Serial console** — `ping`, `status`, `scan`, `info`, `mark`, `wifi`, `testap`, `forget`, `reboot` | row 18, and provisioning without the radio | built |
| **`scan`** — the partner's own view of the air | telling a deaf receiver from a silent AP | built |
| **`testap`** — a WPA2 AP of a given name, on request | row 4: the bench cannot be the AP its own station tests join | built |
| Built-in USB-JTAG (a property of the part, not the firmware) | rows 11, 12, 13 | inherent |
| **MQTT client** — publishes to the broker the portal was given | WT-2104 | built |
| BLE advertisement, off unless the station is actually up | future BLE tests | built |

## What the suite actually produced

103 tests: **102 passed, 0 failed, 1 skipped** in 14 minutes, on one
ESP32-S3, one ESP32-C6 and an RTL-SDR dongle — **with nothing configured**:
no environment variables, no external network, no hand-written slot labels.

| Skips | Reason |
|---:|---|
| 1 | no Si5351 signal generator present |

One skip, and it names a piece of hardware that is not plugged in. That is
the state this page exists to reach, and getting there took removing four
different kinds of false skip:

| Was skipped because | Now |
|---|---|
| `WIFI_TEST_STA_SSID` / `WIFI_TEST_HTTP_URL` unset (5 tests) | the partner hosts the network, so there is nothing to configure |
| WT-602 asked something one radio cannot answer | asks the answerable form: an SSID off the air is gone from the next scan |
| a second ESP32-C3 was assumed | the tests follow whichever part is present |
| the suite destroyed its own partner and never restored it | reflashed at session start and after the flash tests |

Two earlier skips remain latent rather than fixed: `TestPerSlotDebugIsolation`
genuinely needs two built-in-JTAG boards, and passes only while a second one
is in the bench. That skip is honest when it happens.

**Repeatability had to be fixed before any of this meant anything.** One run
passed 74/74 and the next collapsed to 51 passes and 15 failures, on the
same bench, cables and commit. WT-1800 flashes a throwaway image over the partner
to prove flashing works, and nothing put the real one back; the board sat
printing `LOOP: n` and every later test that needed it to *answer* reported
absent hardware. A defined bench (FR-036) is only half a defined starting
state. The suite now restores the partner at session start and after the flash
tests.

## Two gaps this list makes visible

**Row 13 needs a second board.** Per-slot debug isolation cannot be tested
with one JTAG part, and it exists precisely because two boards sharing
VID:PID `303a:1001` were being confused for each other. One S3 leaves it
untestable. A second native-USB part — any of C3/S3/C6/H2, ideally a
different type — is the cheapest coverage on this page.

**BLE has no tests.** The firmware advertises and the bench can scan, but no
test asserts on it. That is a gap in the suite, not in the partner.

## Why serial console before anything else

Everything above depends on provisioning, and provisioning depended on the
radio: credentials arrived only through the partner's own captive portal. When
an S3 stopped transmitting there was no way in at all — and, worse, no way
to tell *the AP is broken* from *the AP is fine and the Pi cannot hear it*.
The console is a wire. It answers that question directly and it provisions
without a beacon.
