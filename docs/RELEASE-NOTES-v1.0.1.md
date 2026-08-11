# v1.0.1

Bug fixes to flap recovery and the debug lifecycle, plus a way to measure
whether a slot's BOOT/EN pins are actually wired.

## Fixed

**`POST /api/serial/recover` did nothing on an auto-detected bench.** The USB
device to unbind was parsed from `slot_key`, which is a udev `ID_PATH` only
for slots pinned in a config file; auto-detected slots carry a synthetic key
with no USB path, so every call aborted at the first guard and still returned
`ok: true`. It now resolves the device from the slot's devnode, refuses up
front when neither source can name one, and reports the *attempt* — naming
`/api/devices` as where the outcome appears.

**GPIO recovery declared `download_mode` without checking.** It now probes the
device with esptool before claiming it, re-resolving the devnode from sysfs
first because a rebind re-enumerates under a different `ttyACM` number. A
failed attempt releases BOOT instead of leaving the board unable to boot.

**`POST /api/serial/release` was gated on `download_mode`.** Releasing a pin is
cleanup; the gate refused the board a failed recovery had just left with BOOT
held.

**Stopping a debug session killed OpenOCD without resuming the target.** It now
issues `reset run` first (5 s timeout, then kills regardless), so a later test
does not inherit a halted core.

**The portal UI showed a constant instead of the bench's name.** The hostname
is substituted server-side, so the tab title is correct before any JavaScript
runs, and `hostname` now refreshes alongside `host_ip`.

**`debug-test` firmware could be read but not written to.** It had no
`sdkconfig.defaults`, so USB-Serial/JTAG was a secondary, output-only console
and host writes reached a peripheral nothing serviced. Now set per target
(`esp32c3`, `esp32c6`, `esp32h2`); the classic ESP32 has no such peripheral and
is excluded.

## Added

**`POST /api/serial/gpio-test`** — measures whether BOOT and EN are physically
wired to a slot's board, in about fifteen seconds. It pulses EN and listens for
the ROM boot banner; if EN answers, it holds BOOT low across a reset and probes
with esptool. The result is persisted to `/var/lib/rfc2217/gpio-wiring.json`,
reloaded at startup, and exposed as `gpio_wired` in `/api/devices` alongside
the existing `has_gpio` (pins *configured*). The portal UI gains a per-slot
button. The board is left running whatever the outcome.

**Recovery now takes the GPIO path only where the wiring has been measured**,
falling back to the wire-free unbind/rebind cycle otherwise, and logging why.

**`.github/workflows/debug-test-firmware.yml`** — builds `debug-test` for
`esp32`, `esp32c3`, `esp32c6` and `esp32h2`, ships `flash_args` and the `.elf`
the debug tests resolve symbols against, and fails the build if the console
setting above is lost. The binaries were previously committed prebuilt with
nothing able to reproduce them.

## Verification

`102 passed, 0 failed, 1 skipped` against the bench. The skip is `WT-1909`,
which needs a Si5351 signal generator that is not installed.

## Upgrading from v1.0.0

```bash
sudo bash pi/install.sh --update
```

Then measure each slot once, since recovery will not use pins it has not seen
work:

```bash
curl -s -X POST http://$BENCH:8080/api/serial/gpio-test \
     -H 'Content-Type: application/json' -d '{"slot":"SLOT1"}'
```

Until a slot is measured, `gpio_wired` is `null` and recovery uses the
wire-free path.
