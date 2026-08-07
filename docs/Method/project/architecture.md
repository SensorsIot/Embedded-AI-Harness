# Project — Architecture and source layout

How the workbench code is structured. The FSD's §2.4 states the layering as
behaviour; this file states the rules the source obeys.

## Layers

Dependencies point one way only: **L0 → L1 → L2**. A lower layer never imports a
higher one.

| Layer | Contents | Modules |
|-------|----------|---------|
| **L0 — Foundation** | Hardware primitives and OS services. No knowledge of the API or of slots. | `bcm_gpio.py` (`/dev/mem` GPIO), `si5351.py`, `pe4302.py`, `gpclk.py`, `morse.py`; externally hostapd, dnsmasq, systemd, udev, OpenOCD, rtl_433 |
| **L1 — Interfaces** | One module per instrument. Owns a protocol or a device; knows nothing about HTTP. | `plain_rfc2217_server.py`, `wifi_controller.py`, `ble_controller.py`, `mqtt_controller.py`, `sdr_controller.py`, `debug_controller.py`, `signal_generator.py` |
| **L2 — Application** | Slot supervision, hotplug state, the HTTP API surface. | `portal.py` |

## Rules

- **One module per instrument.** A new instrument gets its own `*_controller.py`
  at L1. Never fold an instrument into `portal.py` because it is "only a couple of
  endpoints" — that is exactly how the monolith below grew.
- **The dependency arrow stays one-way.** When an L1 module must notify upward
  (a hotplug event, a station join), it exposes a callback the composition root
  wires up. `portal.py` is the composition root; L1 modules stay ignorant of it.
- **Controllers do not import `portal`.** If one needs something from it, the
  dependency is inverted.
- **Extract pure cores.** Parsing, framing, timing arithmetic, and decision logic
  belong in free functions with no serial, socket, or `/dev/mem` dependency, so
  they can be tested without a Pi. This is the main lever for moving tests off the
  bench tier — see [`../standards/testing.md`](../standards/testing.md).
- **Slot identity is by USB path, never by devnode.** `/dev/ttyACM0` is not
  stable across replug; the slot key derived from the USB topology is. Any new
  code that keys off a devnode is a bug.
- **Release what you claim.** GPIO pins are released to input (`"z"`) after use;
  the SDR dongle and each serial port have exactly one owner at a time.

## Known deviations

Recorded because an undocumented deviation gets copied by the next change.

- **`portal.py` is a 4700-line monolith.** It holds the HTTP server, the routing
  table, slot supervision, hotplug handling, the flap state machine, the web UI,
  and several handlers that should be L1 modules. New work should move code *out*
  of it, and must not add new instrument logic *into* it.
- **`serial_proxy.py` is dead code.** `pi/install.sh` does not install it and
  nothing references it; `plain_rfc2217_server.py` replaced it. It still ships in
  the repo.
- **`sniffer.py` is installed but unreachable.** `install.sh` copies it to
  `/usr/local/bin/`, but no endpoint, FR, or skill drives it — it has no `/api/`
  surface. Either give it one and specify it in the FSD, or drop it.

## Configuration

Runtime config lives in `/etc/rfc2217/` on the Pi, with defaults shipped in
`pi/config/`: `workbench.json` (slots, GPIO, probes), `signalgen.json`,
`sdr.json`, `rtl_433.conf`. Slots are auto-detected — config is an override, never
a prerequisite. Anything a user must edit before first run is a design failure.
