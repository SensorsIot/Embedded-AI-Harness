# v1.0.0 — first official release

The Harness is an AI closed-loop programming method plus the testbench that
gives it hands and eyes: a Raspberry Pi that holds ESP32 boards and turns
every physical act — flash, reset, debug, join a network, listen on 433 MHz —
into an HTTP call.

This is the first tagged version. It is cut now because the bench finally
answers the one question a test rig has to answer honestly: **when a test is
not green, is that the product, the setup, or the instrument?**

## What is in it

**The method.** Five phases with gates that are derived, never declared —
Definition, Harness, Commissioning, Build, Shipment — carried by skills that
an AI agent invokes by name. Requirements carry verification contracts, so a
requirement and its proof are written together; a requirement whose stimulus
cannot be stated is not finished. Gate checks run in a fresh checker that
never saw the conversation that did the work.

**The testbench.** One JSON API on `:8080`, every response carrying `ok`:
slots with stable identity by USB port, serial over RFC2217, flash three ways,
OpenOCD and GDB per slot, a WiFi test AP with station events, BLE, an MQTT
broker, HTTP relay, GPIO, SDR and signal generation, firmware hosting, live
test progress and blocking operator prompts.

**Its own test partner.** `test-firmware/` is an ESP32 image the bench builds, versions
and flashes itself — captive-portal provisioning, an HTTP server, UDP logging
to whichever bench handed out its DHCP lease. Attached to this release as
`test-partner-esp32c3.tar.gz` and `test-partner-esp32s3.tar.gz`, each with the
`flash_args` that names the authoritative offsets.

## Why it is trustworthy now

Several defects found this cycle shared one shape: **the bench reported a
failure of its own instrument as an observation about the world.** Each is
fixed, and each left a test behind.

- A scan that could not run — busy radio, or one still settling into AP mode —
  returned `{"ok": true, "networks": []}`. A test read that as a shielded room
  and skipped itself, on a bench with eleven access points in range. Three of
  the four scan tests were satisfied by an empty list, so the capability could
  have been dead with the suite still green.
- Every ESP32 with built-in JTAG enumerates as `303a:1001`. OpenOCD, told
  nothing else, opened whichever one libusb offered first — so a detection
  asked for one slot reported another slot's chip, and could seize a board a
  live session was already driving. Slots are now selected by USB port path.
- Only one debug session could exist anywhere on the bench. This was believed
  to be a hardware consequence of the shared VID:PID and was written into a
  skill as one. It was an OpenOCD TCL port left at its default for every
  session. Two boards now debug at once.
- `serial.rfc2217.PortManager` is not thread-safe, and the read-only fan-out
  had given it two threads. Writes were silently swallowed whenever the device
  spoke at the same moment.
- A write reported `written: 8` about a socket that closed before the bytes
  reached the device.
- **The bench AP reached `AP-ENABLED` and radiated nothing.** hostapd
  installed a beacon the driver accepted — the SSID is legible in the beacon
  hexdump — while a station 20 cm away heard seven neighbouring APs and not
  one frame from this one. Nothing reported an error anywhere: `iw` said
  `type AP` on the right channel, `ap_status` said active, and the only
  symptom reached anyone as the partner's own `NO_AP_FOUND`, which accuses
  the partner. Every test needing a station on the bench AP had been failing on
  this.

  The cause was wpa_supplicant holding the radio. The installer disabled its
  units and NetworkManager restarted it over D-Bus within seconds, because
  it is NM's WiFi backend, so the portal lost that race on every AP start.
  The installer now marks the interface unmanaged, which leaves NM no reason
  to want a supplicant for it.
- **A serial read returned the oldest lines, not the newest.** `lines=N`
  took the first N entries of a 1000-line ring, so any slot up for more than
  a few minutes answered with ancient history whose newest timestamp aged
  steadily — indistinguishable from a recorder that had died. It survived
  because a buffer shorter than `N` is returned whole, and the read straight
  after a flash is exactly that.
- **A dead flash client wedged a slot until someone noticed.** RFC2217 is
  single-client, and an `esptool` killed mid-flash left the connection in
  `CLOSE-WAIT` — the proxy alive, `running: true`, every later client
  refused. The bench reset skipped it *because the proxy was alive*.
- **The partner's logger starved the core it logged from.** Anything logged
  below the log hook came back through it, queued another line and woke the
  task that had just logged — so the task never blocked, IDLE never ran and
  the watchdog fired. An unresponsive board is indistinguishable from an
  unreachable one, and the HTTP relay tests timed out against a board that
  was associated and had an address. The same function also passed one
  `va_list` to two consumers, which is undefined behaviour.

**The partner can now answer.** `FR-030` says a byte written to a slot reaches the
device, and the bench owned nothing that would say anything back — so the test
borrowed a project's M-Bus simulator and went red when that project reflashed
the board. The test partner now carries a line-oriented console on its USB serial
port: `ping` answers `OK pong`, `scan` reports what the partner's own radio can
hear, `info` names the image actually running, and `wifi <ssid> <pass>`
provisions it without needing a radio at all. That last one matters more than
it looks: credentials used to arrive only through the partner's captive portal, so
a board whose AP was not on the air had no way in and no way to tell *the AP is
broken* from *the AP is fine and nobody can hear it*.

**The suite no longer depends on any project's firmware.** Tests used to
assert on a specific project's board — that project's SSID, its M-Bus
simulator answering `status` with `OK` — so a testbench test went red when
that project shipped, which is the dependency backwards. Twelve of them were
hidden behind a `--run-wifi-dut` flag rather than fixed. They now provision
the bench's own test partner, and the flag is gone: a fixture that can tell *absent*
from *broken* beats an opt-out that cannot.

**And it no longer depends on anyone's house network.** Five tests read an
SSID, a passphrase or a URL out of the environment and skipped without them,
so on a fresh bench the station path and the relay's station leg — a good
part of what this bench is for — went unproven, and the skip looked like
absent hardware rather than absent configuration. The tempting fix is the
one that cannot work: aim them at something on the house LAN and the bench's
`eth0` carries the request, so the radio link under test does nothing and
the test passes on the strength of the failure it exists to catch.

They now aim at the test partner. The bench has one radio and so cannot be the access
point its own station tests join, but the partner already in the bench can be:
`testap` puts it on the air as a WPA2 AP of a known name, which makes the
right-passphrase and wrong-passphrase paths answerable, and `192.168.4.0/24`
is somewhere `eth0` has no route to. The whole suite now runs on a bench
nobody has configured.

## Known limits, stated rather than skipped

- **SDR tests need a dongle**; two cases skip without one.
- **One writing serial client per board.** Any number may read the fan-out.
- **No authentication on the API.** Keep the bench on a network you trust.
- **The MCP surface has not caught up** with serial write, bench reset, or the
  slot access manager; those are HTTP and skills only.

## Upgrading

There is nothing to upgrade from — this is the first tag. Install per the
README; `pi/install.sh` puts the portal, the proxy and the udev rules in
place.
