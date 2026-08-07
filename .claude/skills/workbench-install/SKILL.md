---
name: workbench-install
description: Use this skill whenever the workbench Pi itself needs to be built, installed, updated, or have code deployed to it — a fresh SD card, a first `install.sh` run, pushing a changed controller module to a running bench, or diagnosing why a change had no effect. This is about the machine, not the instruments: the other workbench-* skills drive a bench that already works. Triggers on "install the workbench", "set up the Pi", "deploy", "push this to the bench", "my change didn't take effect", "rebuild the SD card", "update the portal", "install.sh", "systemctl restart rfc2217-portal".
---

# Setting up and deploying the workbench

The one fact that explains most confusion: **the service runs from
`/usr/local/bin/`, not from the git checkout.** Editing files in the repo on the
Pi — or on your laptop — changes nothing until they are copied across and the
service is restarted. Every "my fix didn't work" report traces back to this.

Full operator procedure lives in
[`docs/Embedded-Workbench-User-Manual.md`](../../../docs/Embedded-Workbench-User-Manual.md)
§2. This skill is the working procedure plus the things that only bite when you
actually do it.

## Pick the operation

| Situation | Do this |
|---|---|
| New Pi, blank SD card | **Fresh install** below |
| Bench works, want the latest code + no system changes | `sudo bash install.sh --update` |
| Changed one module, want it live now | **Single-file deploy** below |
| Changed a config default in `pi/config/` | Fresh-install path won't overwrite it — see *Config files are never overwritten* |

## Fresh install

```bash
git clone https://github.com/SensorsIot/Embedded-Development-Harness.git
cd Embedded-Development-Harness/pi
sudo bash install.sh
```

`install.sh` is idempotent and does eight things: apt packages, standing down
the services it manages dynamically (`hostapd` is masked; `dnsmasq` and
`mosquitto` are disabled — the portal starts them itself, so leaving them
enabled fights it), directories, the Python modules into `/usr/local/bin/`,
helper scripts, config defaults, systemd + udev rules, then enable and start.

It fetches `openocd-esp32` from GitHub releases and installs it as
`/usr/local/bin/openocd-esp32`, alongside — not replacing — Debian's `openocd`.

**It runs under `set -e`, and the script copy comes before systemd and udev.** So
a single missing file aborts the install after the packages are in but before the
service exists, and the output ends on a bare `cp: cannot stat` with no summary.
Read the last line rather than assuming a long successful-looking log means it
finished; `curl /api/info` is the only proof.

**A fresh install exercises code that `--update` never reaches.** An installer
bug can therefore sit undiscovered indefinitely on benches that were built before
it was introduced — a file deleted from `pi/` but still named in `install.sh`
breaks every new bench and no existing one.

Verify over HTTP — never by reading files over SSH:

```bash
curl -s $WORKBENCH_URL/api/info      # portal version, host info
curl -s $WORKBENCH_URL/api/devices   # every slot
```

If the bench has moved or you do not know its address:

```bash
sudo python3 .claude/skills/esp-idf-handling/discover-workbench.py --hosts
```

Then prove the subsystems actually loaded, because an import that fails on a
newer Python takes only its own endpoint down and leaves the portal answering:

```bash
for ep in sdr/status siggen/status mqtt/status wifi/mode debug/probes gpio/status; do
  curl -s "$WORKBENCH_URL/api/$ep"; echo
done
```

## Platform

The installer pins nothing and works across releases. Verified on:

| | Debian 12 bookworm | Debian 13 trixie |
|---|---|---|
| Python | 3.11 | 3.13 |
| esptool | 4.x | 5.x |

**Python 3.13 removed `telnetlib`, `cgi`, `imp` and `distutils`.** No portal
module uses them today; check before adding a dependency that might.

**esptool 5 renamed things and warns loudly.** `esptool.py` → `esptool`,
`flash_id` → `flash-id`, and its output fields changed (`Chip is` → `Chip type:`,
`Crystal is` → `Crystal frequency:`). The old spellings still work, so the portal
keeps using them for compatibility with older benches, and anything parsing
esptool output must accept both wordings.

## Single-file deploy

The pattern for every module — only the destination name changes:

```bash
scp pi/portal.py pi@<bench-hostname>:/tmp/portal.py
ssh pi@<bench-hostname> 'sudo cp /tmp/portal.py /usr/local/bin/rfc2217-portal && sudo systemctl restart rfc2217-portal'
```

`portal.py` is the only one renamed on install (→ `rfc2217-portal`). The rest
keep their filenames: `sdr_controller.py`, `wifi_controller.py`,
`ble_controller.py`, `mqtt_controller.py`, `debug_controller.py`,
`signal_generator.py`, `si5351.py`, `gpclk.py`, `morse.py`, `bcm_gpio.py`,
`pe4302.py`, `sniffer.py`, `plain_rfc2217_server.py`.

Restarting `rfc2217-portal` is required even for a module the portal imports —
Python has already loaded the old one.

Then prove it took, rather than assuming:

```bash
curl -s $WORKBENCH_URL/api/info
```

**SSH is for deploying code and nothing else.** Never drive the bench over SSH:
every operation has an HTTP endpoint and `pytest/workbench_driver.py` wraps them
all. Reaching for SSH to *do* something means the API is missing a capability —
add the endpoint instead. This is a project rule, not a preference; see
[`docs/Method/AI-Workflow.md`](../../../docs/Method/AI-Workflow.md#deploying-a-change-to-the-bench).

## Things that only bite in practice

**Config files are never overwritten.** `install.sh` writes
`/etc/rfc2217/signalgen.json` and `sdr.json` only when absent, so changing a
default in `pi/config/` and re-running the installer does nothing on a bench that
already has one. Copy it explicitly, or delete the file on the Pi first. The one
exception is `/etc/rtl_433/rtl_433.conf`, which is copied unconditionally — a
hand-edited flex decoder there is lost on every install.

**There is no default `workbench.json`.** Slots auto-detect from USB topology at
boot. Only create `/etc/rfc2217/workbench.json` to override labels or pins.

**Auto-detection over-reports on a Pi 3B+.** It finds five ports where only four
are wired; `0:1.4` is the phantom. Pin the real four in `workbench.json` rather
than trusting the count.

**Do not usbreset several ESP32s at once on a Pi 3B+.** Concurrent resets have
hard-hung the bench — suspected undervoltage. Reset one slot at a time.

**No overlayroot.** It was removed, so the filesystem is writable and there is no
power-loss protection. Shut down cleanly.

**openocd-esp32 is fetched from GitHub releases** for the detected architecture.
On an unsupported arch the installer warns and continues, and debug endpoints
then fail at runtime rather than at install time — check `/api/info` if debug
misbehaves on a new host.

## After a change lands

Re-run the tests against the live bench, and say what actually ran:

```bash
pytest pytest/ --wt-url $WORKBENCH_URL            # no DUT needed
pytest pytest/ --wt-url $WORKBENCH_URL --run-dut  # full
pytest pytest/host/                                            # no hardware at all
```

On a bench with nothing plugged in, expect roughly **47 passed, 42 skipped** —
that is the whole of what can be checked without a DUT, and it is the right
acceptance run for a new build. A test that fails there rather than skipping is
usually the test's own bug: one that omits a slot lets the portal auto-select the
first present device, so on an empty bench it fails with `no device found`
instead of exercising what it claims to.

If the change altered externally observable behaviour, it belongs in the FSD; if
it changed how the bench is built or deployed, it belongs in the Method. See
[`docs/Method/AI-Workflow.md`](../../../docs/Method/AI-Workflow.md).
