---
name: setup-workbench
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
git clone https://github.com/SensorsIot/Universal-Embedded-Workbench.git
cd Universal-Embedded-Workbench/pi
sudo bash install.sh
```

`install.sh` is idempotent and does eight things: apt packages, masking the
services it manages dynamically (`hostapd`, `dnsmasq`, `mosquitto` — it starts
them itself, so leaving them enabled fights the portal), directories, the Python
modules into `/usr/local/bin/`, helper scripts, config defaults, systemd + udev
rules, then enable and start.

Verify over HTTP — never by reading files over SSH:

```bash
curl -s http://workbench.local:8080/api/info      # portal version, host info
curl -s http://workbench.local:8080/api/devices   # every slot
```

If `workbench.local` does not resolve:

```bash
sudo python3 .claude/skills/esp-idf-handling/discover-workbench.py --hosts
```

## Single-file deploy

The pattern for every module — only the destination name changes:

```bash
scp pi/portal.py pi@workbench.local:/tmp/portal.py
ssh pi@workbench.local 'sudo cp /tmp/portal.py /usr/local/bin/rfc2217-portal && sudo systemctl restart rfc2217-portal'
```

`portal.py` is the only one renamed on install (→ `rfc2217-portal`). The rest
keep their filenames: `sdr_controller.py`, `wifi_controller.py`,
`ble_controller.py`, `mqtt_controller.py`, `debug_controller.py`,
`signal_generator.py`, `si5351.py`, `gpclk.py`, `morse.py`, `bcm_gpio.py`,
`pe4302.py`, `sniffer.py`, `plain_rfc2217_server.py`, `cw_beacon.py`.

Restarting `rfc2217-portal` is required even for a module the portal imports —
Python has already loaded the old one.

Then prove it took, rather than assuming:

```bash
curl -s http://workbench.local:8080/api/info
```

**SSH is for deploying code and nothing else.** Never drive the bench over SSH:
every operation has an HTTP endpoint and `pytest/workbench_driver.py` wraps them
all. Reaching for SSH to *do* something means the API is missing a capability —
add the endpoint instead. This is a project rule, not a preference; see
[`docs/Harness/AI-Workflow.md`](../../../docs/Harness/AI-Workflow.md#deploying-a-change-to-the-bench).

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
pytest pytest/ --wt-url http://workbench.local:8080            # no DUT needed
pytest pytest/ --wt-url http://workbench.local:8080 --run-dut  # full
pytest pytest/host/                                            # no hardware at all
```

If the change altered externally observable behaviour, it belongs in the FSD; if
it changed how the bench is built or deployed, it belongs in the Harness. See
[`docs/Harness/AI-Workflow.md`](../../../docs/Harness/AI-Workflow.md).
