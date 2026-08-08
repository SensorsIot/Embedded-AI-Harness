# v1.0.0 — first official release

The Harness is an AI closed-loop programming method plus the workbench that
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

**The workbench.** One JSON API on `:8080`, every response carrying `ok`:
slots with stable identity by USB port, serial over RFC2217, flash three ways,
OpenOCD and GDB per slot, a WiFi test AP with station events, BLE, an MQTT
broker, HTTP relay, GPIO, SDR and signal generation, firmware hosting, live
test progress and blocking operator prompts.

**Its own DUT.** `test-firmware/` is an ESP32 image the bench builds, versions
and flashes itself — captive-portal provisioning, an HTTP server, UDP logging
to whichever bench handed out its DHCP lease. Attached to this release as
`bench-dut-esp32c3.tar.gz` and `bench-dut-esp32s3.tar.gz`, each with the
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

**The suite no longer depends on any project's firmware.** Tests used to
assert on a specific project's board — an `awning-net` SSID, an M-Bus
simulator answering `status` with `OK` — so a workbench test went red when
that project shipped, which is the dependency backwards. Twelve of them were
hidden behind a `--run-wifi-dut` flag rather than fixed. They now provision
the bench's own DUT, and the flag is gone: a fixture that can tell *absent*
from *broken* beats an opt-out that cannot.

## Known limits, stated rather than skipped

- **The bench cannot prove a byte reached a device without a responder**, and
  it owns none. `FR-030`'s arrival test declares its responder through
  `WT_ECHO_SLOT`/`WT_ECHO_CMD`/`WT_ECHO_REPLY` and records an unmet
  precondition otherwise. A loopback slot, or an on-demand ROM download-mode
  SYNC, would close it for good.
- **SDR tests need a dongle**; two cases skip without one.
- **One writing serial client per board.** Any number may read the fan-out.
- **No authentication on the API.** Keep the bench on a network you trust.
- **The MCP surface has not caught up** with serial write, bench reset, or the
  slot access manager; those are HTTP and skills only.

## Upgrading

There is nothing to upgrade from — this is the first tag. Install per the
README; `pi/install.sh` puts the portal, the proxy and the udev rules in
place.
