---
name: esp-pio-handling
description: >
  PlatformIO lifecycle for ESP32 firmware: platformio.ini, environment
  selection, build, upload and serial monitor, on local USB or through the
  workbench. Covers what differs from ESP-IDF — the .pio/build layout, the
  boot_app0 image an Arduino-framework build needs, and RFC2217 upload ports.
  Triggers on "pio", "platformio", "pio run", "pio upload", "platformio.ini",
  "lib_deps", "Arduino framework".
---

# PlatformIO Handling

Build, upload and monitor a PlatformIO ESP32 project, locally or through the
workbench.

**The workbench does not care which build system produced the image.** Slot
discovery, `/api/flash`, GPIO download mode, crash-loop and flapping recovery are
the same either way and live in
[`esp-idf-handling`](../esp-idf-handling/SKILL.md). This skill covers only what
PlatformIO does differently. When something goes wrong with the *bench* rather
than the build, read that skill.

## Step 1: Detect environment

Same as [`esp-idf-handling`](../esp-idf-handling/SKILL.md): if `/api/info`
answers, use the workbench; if nothing answers, flash over local USB. The
discovery script is shared —
`.claude/skills/esp-idf-handling/discover-workbench.py --hosts`.

## Step 2: Build

```bash
pio run                    # default environment
pio run -e esp32dev        # one environment
pio run -t clean
```

With several environments in `platformio.ini`, ask which to build rather than
guessing — they often target different boards. After a build, read the size
report, and check `lib_deps` when a header is missing rather than installing
libraries globally.

## Step 3a: Upload — local USB

```bash
pio device list
pio run -t upload
pio run -e esp32dev -t upload
pio run -t upload && pio device monitor
```

## Step 3b: Upload — workbench

Prefer `POST /api/flash` over driving esptool through RFC2217, for the reasons in
[`esp-idf-handling`](../esp-idf-handling/SKILL.md). What differs here is where the
images are and which ones exist.

PlatformIO writes them to `.pio/build/<env>/`, and there is **no `flash_args`**,
so use the explicit `bin@<offset>` form:

```bash
cd .pio/build/<env>
curl -s -X POST $WORKBENCH_URL/api/flash \
  -F slot=SLOT1 -F chip=esp32 \
  -F 'bin@0x1000=@bootloader.bin' \
  -F 'bin@0x8000=@partitions.bin' \
  -F 'bin@0x10000=@firmware.bin' | jq .
```

**An Arduino-framework build also needs `boot_app0.bin` at `0xe000`.** It is not
in `.pio/build/` — it ships inside the framework package, under
`~/.platformio/packages/framework-arduinoespressif32*/tools/partitions/`. Without
it the bootloader has no OTA-selection data and boots the wrong slot after an
update. An ESP-IDF project has no equivalent, which is why this step is not
simply a pointer.

`workbench-flash.py` beside this skill collects all four and posts them:

```bash
pio run
python3 .claude/skills/esp-pio-handling/workbench-flash.py \
  --host <bench>:8080 --slot SLOT3 --chip esp32
```

Offsets: classic ESP32 → `0x1000`, C3/S3/C6/H2 → `0x0`. Fields and response:
[FSD Appendix D.9](../../../docs/Embedded-Workbench-FSD.md#d9-flashing-usb--ota).

### Fallback: RFC2217 upload (LAN clients only)

```ini
upload_port  = rfc2217://<bench>:4001
monitor_port = rfc2217://<bench>:4001
```

```bash
pio run -t upload --upload-port 'rfc2217://<bench>:4001?ign_set_control'
```

`?ign_set_control` is required: PlatformIO's esptool drives DTR/RTS, and over
RFC2217 each one is a network roundtrip.

## Step 4: Monitor

```bash
pio device monitor                                                    # local
pio device monitor --port 'rfc2217://<bench>:4001?ign_set_control'
```

For pattern matching, UDP logs, or watching a device whose USB port is occupied,
use [`workbench-logging`](../workbench-logging/SKILL.md).

## Troubleshooting

Bench-side problems — `absent`, `flapping`, `download_mode`, crash loops — are in
[`esp-idf-handling`](../esp-idf-handling/SKILL.md). PlatformIO-specific:

| Issue | Fix |
|-------|-----|
| No device found | `pio device list`; check the cable |
| Permission denied | `sudo usermod -a -G dialout $USER`, then re-login |
| Upload timeout on local USB | Enter boot mode: hold **BOOT**, press **RESET**, release **RESET** then **BOOT** |
| Port busy | Another terminal holds the same RFC2217 port |
| `Wrong boot mode detected (0x13)` | Classic ESP32 behind a USB-serial bridge (CP2102/CH340/CH9102) — its external auto-reset cannot be driven through the proxy. Flash via `POST /api/flash` (Step 3b). Native-USB C3/S3/C6/H2 strap internally and are unaffected |
| Wrong firmware runs after an OTA | `boot_app0.bin` was not flashed — see Step 3b |
