# v1.0.1 — the rescue that had never run

One fix, and everything it turned out to be sitting on top of.

`v1.0.0` shipped with a known limit: `/api/serial/recover` set a slot to
`download_mode` without asking the device whether it had got there. Fixing
that uncovered why nobody had noticed — **on a default installation, flap
recovery had never run at all.**

## The bug under the bug

The USB device to unbind was parsed out of `slot_key`. That key is a udev
`ID_PATH` only for slots pinned in a config file; on an auto-detected bench —
which the manual calls the normal case, *"slots are auto-detected, no config
file needed"* — it is a synthetic `_fixed_SLOT2` with no USB path in it. The
parse returned `None`, recovery aborted at its first guard with *"cannot
determine USB device from slot_key"*, and the endpoint answered `ok: true`.

So one of the headline capabilities — *it presses the buttons, and rescues a
boot-looping board with nobody in the room* — was inoperative on the
configuration the README recommends, and said nothing.

Five changes, each found because the previous one exposed it:

- the USB device is resolved **from the slot's devnode** when `slot_key`
  cannot name it, and the endpoint refuses up front when neither can, rather
  than reporting a start it never performed
- the GPIO path **probes with esptool** (`--before no-reset`, so the check
  cannot create the condition it is meant to observe) instead of declaring
  `download_mode`
- the devnode is **re-resolved from sysfs** before probing. A rebind
  re-enumerates and the kernel hands out a different number — SLOT2 left as
  `ttyACM2` and came back as `ttyACM0` — so the first version of the check
  reported *"no devnode after rebind"* for a device that was present and well
- a failed attempt **releases BOOT**. Holding it low only helps a caller
  about to flash, and there is no such caller when download mode was never
  reached; leaving it asserted stops the board booting at all
- `/api/serial/release` is **no longer gated on state**. It is cleanup, and
  the gate refused exactly the board a failed recovery had just stranded —
  which turned up within a minute of making recovery honest

`/api/serial/recover` now says what it is: it reports the *attempt*, and
names where the outcome appears (`/api/devices`, as `download_mode` or
`flapping` with `last_error`).

## Configured pins are not connected pins

`gpio_boot=18` and `gpio_en=17` are defaults the portal fills in. No software
can see a wire, and on most benches those pins go nowhere — so `has_gpio` was
a statement about configuration that recovery had been reading as a statement
about hardware.

The obvious fix is a checkbox: let the operator confirm the wiring. That
replaces the bench's assumption with the operator's recollection of what they
soldered, which is an observation by eye — and this project's own rule is
that the operator's hands are for physical acts while **observations belong
to instruments**.

So `POST /api/serial/gpio-test` measures it, in about fifteen seconds:

- **EN** — pulse it, and listen for the ROM boot banner the recorder is
  already capturing. A wired board resets; an unwired one does not
- **BOOT** — only meaningful once EN answers: hold BOOT low across a reset
  and probe with esptool. A wired BOOT reaches download mode

The verdict is a fact with a timestamp, stored in
`/var/lib/rfc2217/gpio-wiring.json` and reloaded at startup — a measurement
that does not survive a restart is an assumption again by morning. The API
keeps the two apart: `has_gpio` means pins are configured, `gpio_wired` means
a measurement found them connected. **Recovery takes the GPIO path only where
the wiring has been measured**, and logs why when it falls back to the
wire-free unbind/rebind cycle. There is a per-slot button in the portal UI,
and the board is handed back running whatever the answer.

Measured on the reference bench: both slots `en_wired=false,
boot_wired=false` — correct, nothing is soldered to those pins there.

## The portal names the bench

The page fetched the hostname, printed it in the info line, and guarded the
heading with `if (hostName)` — then assigned a constant. Every bench called
itself the same thing, and two identical browser tabs is precisely the
situation in which somebody flashes the wrong board. The name is now
substituted server-side, so the tab title is right before any JavaScript runs
and stays right on a bench whose `/api/devices` is wedged. `hostname` also
refreshes alongside `host_ip`, which was already refreshed for this reason.

## Verification

`102 passed, 0 failed, 1 skipped` on hardware — the skip is a Si5351 that is
not plugged in. The recovery cycle was exercised end to end on the bench:
the endpoint accepts, the slot moves `recovering` → `flapping`, `last_error`
names both possible causes, and the board boots on its own afterwards.

## Upgrading from v1.0.0

`sudo bash pi/install.sh --update`, then measure each slot once:

```bash
curl -s -X POST http://$BENCH:8080/api/serial/gpio-test \
     -H 'Content-Type: application/json' -d '{"slot":"SLOT1"}'
```

Until a slot is measured, `gpio_wired` is `null` and recovery uses the
wire-free path — which is the safe default, and the one that was silently in
force anyway.
