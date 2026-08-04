---
name: esp-idf-handling
description: >
  Complete ESP-IDF lifecycle: project setup, build, flash, monitor, and OTA.
  Automatically detects whether a workbench is available or the device is
  connected locally via USB. Covers sdkconfig, partition tables, esptool,
  RFC2217 remote flashing, GPIO download mode, OTA updates, crash recovery,
  and flapping. Triggers on "flash", "build", "upload", "idf.py", "monitor",
  "serial console", "slot", "workbench", "esptool", "OTA", "erase",
  "download mode", "crash loop", "flapping", "bricked", "menuconfig",
  "set-target", "sdkconfig", "partition".
---

# ESP-IDF Handling

Complete lifecycle for ESP-IDF projects — from project creation to flashing
and monitoring. Automatically adapts to local USB or remote workbench.

## Step 1: Detect Environment

Determine whether a workbench is available or the device is local.

```bash
curl -s $WORKBENCH_URL/api/info
```

- **Response received** → workbench is available, use remote flashing (RFC2217/OTA)
- **Connection refused / timeout** → try the discovery script:
  ```bash
  sudo python3 .claude/skills/esp-idf-handling/discover-workbench.py --hosts
  ```
- **Still no response** → no workbench, use local USB flashing

## Step 2: Project Setup

```bash
source /opt/esp-idf/export.sh
idf.py create-project <name>           # Create new project
idf.py set-target esp32s3              # Set target chip (esp32, esp32s3, esp32c3, etc.)
idf.py menuconfig                      # Interactive configuration (writes sdkconfig)
```

### sdkconfig.defaults

Put persistent config in `sdkconfig.defaults` (not `sdkconfig` which is generated):

```
CONFIG_ESPTOOLPY_FLASHSIZE_4MB=y
CONFIG_PARTITION_TABLE_CUSTOM=y
CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions-4mb.csv"
```

## Step 3: Build

```bash
source /opt/esp-idf/export.sh
idf.py build                           # Build
idf.py fullclean                       # Clean build directory
```

### Step 3b: When there is no local toolchain

`export.sh` missing is not a broken setup — a project set up by the
[`setup-action`](../setup-action/SKILL.md) skill builds on GitHub deliberately,
and some machines never install ESP-IDF at all. Check before assuming:

```bash
ls /opt/esp-idf/export.sh ~/esp/esp-idf/export.sh 2>/dev/null || echo "build in CI"
```

Then the binaries have to come back before Step 4 can run:

```bash
# `gh` needs a token, and a tool call is a NON-interactive shell, where
# ~/.bashrc returns before it sources the secrets. Without this line gh says
# "not logged into any GitHub hosts" even though the terminal works fine.
# Never `gh auth login` — see the `github` skill.
. /run/secrets/env 2>/dev/null

gh run download -R <owner>/<repo> -D /tmp/fw            # latest successful run
gh run download -R <owner>/<repo> <run-id> -D /tmp/fw   # one specific run
gh release download v1.2.0 -R <owner>/<repo> -D /tmp/fw # a published release
```

Without a token, download the artefact zip from the run page in a browser and
unpack it — the flash steps below only care that the files exist.

`setup-action`'s template publishes exactly what the two flash paths need:

| Artefact | Feeds |
|---|---|
| `coldflash/` — `flash_args` plus every image it names | Step 4a/4b — a first flash over USB |
| `firmware_v<version>.bin` | Step 4c — the OTA image |
| `sdkconfig.generated` | the effective config, since `sdkconfig` is not committed |

**Use the `flash_args` form in Step 4b when the artefact carries one**, and the
explicit-offset form only when it does not. Offsets are not constant: enabling
OTA moves the app from `0x10000` to `0x20000` and adds `ota_data_initial.bin` at
`0xf000`. A remembered offset writes into the wrong partition and boots the
previous firmware, which looks exactly like a flash that worked.

Confirm what you are about to flash rather than trusting the filename — the
version is compiled into the image:

```bash
strings /tmp/fw/coldflash/firmware.bin | grep -m1 '^[0-9]\+\.[0-9]\+\.[0-9]\+'
```

## Flash Size and Partition Tables

**Measure the flash; never assume it.** There is no universal default — ESP-IDF
picks one per target, and it is often smaller than expected (an ESP32-C3 build
with nothing set comes out at 2 MB). Whatever it picks is written into the image
header, and the bootloader then *prints that value back at you*, so a boot log
saying `SPI Flash Size : 2MB` is only repeating the config. It is not evidence
about the chip, and reading it as such is an easy way to design a partition
layout around a number nobody checked.

Getting it wrong is not loud. Configure more than the part has and the partition
table extends past the end of flash: the build succeeds, the flash succeeds, and
the failure arrives later as corruption at whatever offset first exceeds the
physical device — usually OTA or NVS, rarely the app.

Ask the bench — it reads the chip directly
([FSD §6.7.3](../../../docs/Embedded-Workbench-FSD.md#673-chip-identity-via-post-apichipinfo)):

```bash
curl -X POST $WORKBENCH_URL/api/chip/info \\
  -H 'Content-Type: application/json' -d '{"slot": "SLOT3"}'
# -> "flash_size": "4MB", plus chip, revision, MAC and USB mode
```

It runs `esptool flash_id` on the Pi with the proxy stopped, so **it reboots the
DUT** — a deliberate call, not something to poll. Stop any debug session first
or it returns `409`.

Off the bench, the same thing over a local port:

```bash
esptool --port /dev/ttyACM0 flash_id     # "Detected flash size: ..."
```

```c
/* Or from the firmware, the only way that survives a board swap */
uint32_t size = 0;
esp_flash_get_physical_size(NULL, &size);
ESP_LOGI(TAG, "flash %lu MB", (unsigned long)(size / (1024 * 1024)));
```

Then set `CONFIG_ESPTOOLPY_FLASHSIZE_<n>MB=y` in `sdkconfig.defaults` to the
measured value and size the partition table to fit it. Setting
`CONFIG_ESPTOOLPY_HEADER_FLASHSIZE_UPDATE=y` additionally lets esptool correct
the header from the detected size at flash time — useful when one image serves
boards that differ, but it does not resize the partition table, so it is a
safety net rather than a substitute for measuring.

**Check OTA fits before writing OTA code.** Two app partitions plus NVS, PHY
and the bootloader is the constraint that decides whether an OTA design is
possible at all, and it is cheapest to discover before the firmware exists.
`test-firmware/` carries a worked pair — `partitions-4mb.csv` (1216K app) and
`partitions.csv` for 8MB+ (1536K app).

## Step 4a: Flash — Local USB

When the device is connected directly via USB (no workbench).

```bash
source /opt/esp-idf/export.sh
idf.py -p /dev/ttyUSB0 flash           # Flash to specific port
idf.py -p /dev/ttyUSB0 monitor         # Open serial monitor
idf.py -p /dev/ttyUSB0 flash monitor   # Flash and monitor
```

### esptool flags by device type

| Device | `--before` | `--after` |
|--------|-----------|----------|
| ESP32 (local USB, ttyUSB) | `default-reset` | `hard-reset` |
| ESP32-C3/S3 (local USB, ttyACM) | `default-reset` | `no-reset` |
| Any chip via `/api/flash` | fixed by the portal | fixed by the portal |

**A DTR/RTS reset can take a native-USB board off the bus.** `POST
/api/serial/reset` on a C3/S3 re-enumerates USB, and the device normally comes
back within a second or two. When it does not, the slot goes `absent` and stays
there — seen once immediately after a reset, with `USB remove` in the activity
log and nothing on `lsusb` afterwards. Prefer `/api/serial/monitor` for reading a
running device, and keep resets for when you actually need a reboot.

**`/api/flash` takes no reset flags.** The portal hardcodes
`--before default_reset --after hard_reset`, so the device reboots into the new
firmware on its own — do **not** follow it with `POST /api/serial/reset`. The
`--after no-reset` advice applies only to driving esptool yourself over RFC2217,
where the reset has to be a separate call.

Stop debug before flashing native USB chips (serial + JTAG share USB).

### Boot mode (manual)

1. Hold **BOOT** button
2. Press **RESET** button
3. Release **RESET**, then **BOOT**

## Step 4b: Flash — Workbench (RFC2217)

When a workbench is available. Use serial flashing when:
- Device has **no firmware** (blank/bricked/first flash)
- Firmware **lacks OTA support**
- You need to **erase NVS** or flash a **bootloader/partition table**
- Device has **no WiFi connectivity**

### Discover devices and slot

Slots are mapped to physical USB hub ports via prefix matching. The portal auto-detects the slot count from the Pi's USB topology at startup (typically 3–4); `workbench.json` is optional and only needed for custom labels/ports. Slot labels are `SLOT1`, `SLOT2`, ..., `SLOTn`; TCP ports are `4000 + slot_index` (e.g. SLOT1 = :4001). Always read slot info from `/api/devices` to learn the actual layout and verify the device is present.

```bash
curl -s $WORKBENCH_URL/api/devices | jq .
```

Response fields per slot: `label`, `state`, `url` (RFC2217, auto-assigned port), `present`, `running`, `detected_chip`, `debugging`.

**A debug session on *any* slot can block this one.** Native-USB parts share the
VID:PID `303a:1001` and OpenOCD claims the interface by it, so a session on a
different board fails this slot with `A serial exception error occurred: Write
timeout` while it reads `idle` and `debugging: false`. Stop every session, not
just this slot's — see `workbench-debug`.

**`state: "idle"` is not enough — check `debugging` too.** A slot with a live
OpenOCD session reads `idle` while still holding the port, and `/api/flash` is
refused. On native-USB parts serial and JTAG share the one interface, so this is
the normal state of a board you have been debugging:

```bash
curl -X POST $WORKBENCH_URL/api/debug/stop \
  -H 'Content-Type: application/json' -d '{"slot": "SLOT3"}'
```

### Flash via RFC2217

**Bootloader offsets:** Classic ESP32 → `0x1000`, all newer chips (C3/S3/C6/H2) → `0x0000`.

#### Preferred: `POST /api/flash` (Pi-side esptool)

The portal stops the proxy, runs esptool directly on the Pi against the
local devnode, then restarts the proxy. Use this whenever your client is
not on the same LAN as the workbench — RFC2217's SET_CONTROL roundtrip is
too slow to keep the auto-reset window open from a high-latency path.

**Multipart with ESP-IDF `flash_args`** (recommended — uses what the build
already produces):

```bash
cd build
curl -s -X POST $WORKBENCH_URL/api/flash \
  -F slot=SLOT1 -F chip=esp32 -F baud=921600 \
  -F flash_args=@flash_args \
  -F bootloader.bin=@bootloader/bootloader.bin \
  -F partition-table.bin=@partition_table/partition-table.bin \
  -F ota_data_initial.bin=@ota_data_initial.bin \
  -F firmware.bin=@firmware.bin \
  | jq .
```

Each .bin file's multipart **part name must equal its basename** as
referenced by `flash_args` (e.g. `bootloader.bin`).

**Multipart with explicit offsets** — the form to use whenever there is no build
tree to take `flash_args` from: a CI artefact (Step 3b), a released binary, or a
one-off single-binary flash. The part name is `bin@<offset>`; a part named just
`<offset>` is stored as a plain file and never flashed, so the request fails with
`no binaries to flash`:

```bash
curl -s -X POST $WORKBENCH_URL/api/flash \
  -F slot=SLOT1 -F chip=esp32c3 \
  -F 'bin@0x0000=@bootloader.bin' \
  -F 'bin@0x8000=@partition-table.bin' \
  -F 'bin@0x10000=@firmware.bin'
```

Every field, its default, and the response shape: [FSD §6.7.1](../../../docs/Embedded-Workbench-FSD.md#671-local-flashing-via-post-apiflash).

#### Reading flash back: `POST /api/flash/read`

The counterpart to `/api/flash`. Pull a region of flash off the device without
dropping to OpenOCD — a coredump partition, an NVS blob, the live partition
table. JSON body, no upload; same proxy lifecycle as a flash (it stops the
proxy and does a reset, so it disturbs the running firmware just like a flash).

```bash
curl -s -X POST $WORKBENCH_URL/api/flash/read \
  -H 'Content-Type: application/json' \
  -d '{"slot":"SLOT3","offset":"0x3F0000","length":"0x10000","chip":"esp32c3"}'
# -> {"ok":true,"offset":4128768,"length":65536,"sha256":"...","data_b64":"..."}
```

`offset`/`length` accept an int or a `0x…` string. The bytes come back
base64-encoded in `data_b64` with a `sha256` to verify. Stop any debug session
first (`/api/debug/stop`) — a live OpenOCD holds the port and esptool cannot
open it. For a coredump, decode the bytes then
`esp-coredump --chip <c> info_corefile --core <file> --core-format raw <elf>`.

#### Fallback: direct esptool over RFC2217

Only viable when your client is on the same LAN as the workbench
(sub-millisecond RTT). Slow paths break the auto-reset timing window
because each pyserial `SET_CONTROL` is a network roundtrip.

```bash
SLOT_URL=$(curl -s $WORKBENCH_URL/api/devices | jq -r '.slots[0].url')
esptool --port "$SLOT_URL" --chip esp32c3 \
  --before default-reset --after no-reset \
  write-flash --flash-mode dio --flash-size 4MB \
  0x0000 bootloader.bin 0x8000 partition-table.bin 0x10000 firmware.bin
curl -X POST $WORKBENCH_URL/api/serial/reset \
  -H "Content-Type: application/json" -d '{"slot":"SLOT1"}'
```

### Workbench API endpoints

The full endpoint reference is [FSD Appendix D](../../../docs/Embedded-Workbench-FSD.md#appendix-d-http-api--mcp-reference)
— D.1 discovery, D.2 serial, D.8 firmware repository, D.9 flashing. Read it there
rather than from memory: this skill states *which* call to reach for and what
breaks, not the request shapes.

### Serial reset

`POST /api/serial/reset` ([D.2](../../../docs/Embedded-Workbench-FSD.md#d2-serial-management)) pulses DTR/RTS and
returns the boot output. Needed after driving esptool yourself over RFC2217 —
**not** after `/api/flash`, which resets the device itself.

### Slot states

Defined with their transitions in the [FSD](../../../docs/Embedded-Workbench-FSD.md#16-state-model). Only two accept a
flash: **`idle`** (via `/api/flash` or RFC2217) and **`download_mode`** (direct
serial on the Pi). Anything else means wait or recover first — see
Flapping & Automatic Recovery below.

## Step 4c: Flash — Workbench OTA

Use OTA when the device already runs firmware with an OTA HTTP endpoint and
is on the WiFi network. Faster than serial and doesn't block the serial port.

```bash
# 1. Upload firmware to workbench
curl -X POST $WORKBENCH_URL/api/firmware/upload \
  -F "project=my-project" \
  -F "file=@build/firmware.bin"

# 2. Verify upload
curl -s $WORKBENCH_URL/api/firmware/list | jq .

# 3. Trigger OTA on the ESP32 via HTTP relay
OTA_BODY=$(echo -n '{"url":"$WORKBENCH_URL/firmware/my-project/firmware.bin"}' | base64)
curl -X POST $WORKBENCH_URL/api/wifi/http \
  -H 'Content-Type: application/json' \
  -d "{\"method\": \"POST\", \"url\": \"http://192.168.4.2/ota\", \"headers\": {\"Content-Type\": \"application/json\"}, \"body\": \"$OTA_BODY\", \"timeout\": 30}"

# 4. Monitor OTA progress via UDP logs
curl "$WORKBENCH_URL/api/udplog?limit=50"
```

### Firmware repository management

Upload, list and delete are [FSD Appendix D.8](../../../docs/Embedded-Workbench-FSD.md#d8-firmware-repository). The
one detail this flow depends on: an uploaded image is served to the device at
`$WORKBENCH_URL/firmware/<project>/<filename>`, and that URL is
what step 3 above hands to the ESP32.

## Step 5: Monitor

```bash
# Local
idf.py -p /dev/ttyUSB0 monitor

# Workbench — via serial monitor API (see workbench-logging skill)
# or via UDP logs
curl "$WORKBENCH_URL/api/udplog?limit=50"
```

### Monitor shortcuts

- `Ctrl+]` — Exit monitor
- `Ctrl+T` `Ctrl+H` — Show help
- `Ctrl+T` `Ctrl+R` — Reset target

## GPIO Download Mode (Workbench)

When DTR/RTS reset doesn't work (no auto-download circuit), use GPIO.

### Pin mapping

| Pi GPIO | ESP32 Pin | Function |
|---------|-----------|----------|
| GPIO17 | EN | **RST** — pull LOW to reset |
| GPIO18 | GPIO0 | **BOOT** — hold LOW during reset to enter download mode |

Allowed BCM pins: `5, 6, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27`

### Enter download mode

```bash
# 1. Hold BOOT LOW
curl -X POST $WORKBENCH_URL/api/gpio/set \
  -H 'Content-Type: application/json' -d '{"pin": 18, "value": 0}'
sleep 1
# 2. Pull EN LOW (reset)
curl -X POST $WORKBENCH_URL/api/gpio/set \
  -H 'Content-Type: application/json' -d '{"pin": 17, "value": 0}'
sleep 0.2
# 3. Release EN HIGH (ESP32 exits reset, samples BOOT=LOW → download mode)
curl -X POST $WORKBENCH_URL/api/gpio/set \
  -H 'Content-Type: application/json' -d '{"pin": 17, "value": 1}'
sleep 0.5
# 4. Release BOOT HIGH
curl -X POST $WORKBENCH_URL/api/gpio/set \
  -H 'Content-Type: application/json' -d '{"pin": 18, "value": 1}'
```

### Flash after GPIO download mode

```bash
sleep 5  # Wait for USB re-enumeration
esptool.py --port "rfc2217://<bench>:<PORT>?ign_set_control" \
  --chip esp32s3 --before=no_reset write_flash @flash_args
```

### GPIO probe — auto-detect board capabilities

Not all boards have EN/BOOT wired to Pi GPIOs. Run once per board:

| GPIO probe output | USB reset output | Board type |
|-------------------|-----------------|------------|
| `boot:0x23` (DOWNLOAD) | — | **GPIO-controlled** — Pi GPIOs wired to EN/BOOT |
| No output / normal boot | `rst:0x15` | **USB-controlled** — use DTR/RTS |
| No output | No output | No control — check wiring or wrong slot |

**Dual-USB hub boards** have onboard auto-download circuit — GPIO wiring not needed.

## Crash-Loop Recovery (Workbench)

When firmware crashes on boot (repeated `rst:0xc (RTC_SW_CPU_RST)` with backtraces),
use the `/api/flash` endpoint to reflash working firmware. The portal handles proxy
lifecycle safely. If the device is completely unresponsive, use GPIO download mode
(if available) or reflash directly on the Pi with the portal stopped.

## Flapping & Automatic Recovery (Workbench)

Empty or corrupt flash can cause USB connection cycling (`flapping` state).
The portal actively recovers by unbinding USB and re-entering download mode.

### With GPIO

```
State flow: flapping → recovering → download_mode → (flash firmware) → idle
```

After portal reaches `download_mode`, upload and flash on the Pi:

```bash
scp build/bootloader/bootloader.bin build/partition_table/partition-table.bin \
    build/ota_data_initial.bin build/*.bin pi@<bench-hostname>:/tmp/
ssh pi@<bench-hostname> "python3 -m esptool --chip esp32s3 --port /dev/ttyACM1 \
  write_flash --flash_mode dio --flash_size 4MB \
  0x0 /tmp/bootloader.bin 0x8000 /tmp/partition-table.bin \
  0xf000 /tmp/ota_data_initial.bin 0x20000 /tmp/firmware.bin"
```

Then release GPIO:

```bash
curl -X POST $WORKBENCH_URL/api/serial/release \
  -H 'Content-Type: application/json' -d '{"slot": "SLOT1"}'
```

### Without GPIO

```
State flow: flapping → recovering → idle (if stable) or flapping (retry, up to 2x)
```

After 2 failed attempts, flash directly on the Pi with `esptool --before=usb_reset`.

### Manual recovery trigger

```bash
curl -X POST $WORKBENCH_URL/api/serial/recover \
  -H 'Content-Type: application/json' -d '{"slot": "SLOT1"}'
```

## Power-cycling a DUT (don't automate it with uhubctl)

A test that needs a **true power cycle** — a `POWERON` reset reason, or clearing
the ESP32's RTC SRAM to exercise a cold-boot guard — is tempting to automate by
cutting USB VBUS with `uhubctl`. On a typical bench Pi this backfires two ways,
both observed:

- **It can take the whole bench offline.** The Pi's *one* switchable root port
  (`uhubctl` shows `ppps` on only that port) usually feeds a **ganged** hub that
  carries the DUT slots *and the Pi's own USB-Ethernet uplink*. Cutting it drops
  the Pi's network, and the port frequently does not restore on its own — the
  bench needs a physical power-cycle to come back. Never run `uhubctl` against
  the root port that carries the Pi's uplink.
- **A brief VBUS cut may not be a real power cycle anyway.** The ESP32-C3's RTC
  domain holds its charge across a short outage, so `reset_reason` comes back
  `USB`, not `POWERON`, and RTC-SRAM guards still see stale state. Even a Pi
  power-cycle left the C3's RTC SRAM intact in one run.

If a case genuinely needs power removed from the DUT alone, use a **per-port
switchable hub** (uhubctl's supported list) powering only the DUT slots, a
smart-plug/relay on the DUT rail, or an operator replug — never the shared root
port. Treat "true power cycle" as an operator-assisted tier, not an automated
one, unless the bench has isolated DUT power.

## Troubleshooting

### Local USB

| Issue | Solution |
|-------|----------|
| Failed to connect | Enter boot mode (BOOT+RESET sequence) |
| No serial port found | Check USB cable, `ls /dev/ttyUSB*` or `ls /dev/ttyACM*` |
| Permission denied | `sudo usermod -aG dialout $USER`, re-login |

### Workbench

| Problem | Fix |
|---------|-----|
| Slot shows `absent` | Check USB cable, re-seat device |
| Slot went `absent` and stays there | Check `lsusb` on the Pi. **If no `303a:` device appears, no API call can help** — `/api/serial/recover` and GPIO download mode both drive a board that is still enumerated. A device off the bus needs hands: re-seat the cable or power-cycle the board |
| `flapping` state | Recovery should start automatically; if stuck, `POST /api/serial/recover` |
| `recovering` state | USB unbound, recovery in progress — wait for `download_mode` or `idle` |
| `download_mode` state | Flash firmware on the Pi, then `POST /api/serial/release` |
| esptool can't connect | Use `POST /api/flash` — never call esptool over RFC2217 directly |
| Device crash-looping | Reflash via `POST /api/flash` with working firmware |
| Board occupies two slots | Onboard USB hub — identify JTAG vs UART via `udevadm info` |

### OTA

| Problem | Fix |
|---------|-----|
| Upload fails | Use `-F` flags (multipart), not `-d` |
| ESP32 can't download firmware | Device must reach workbench; check WiFi |
| OTA trigger times out | Check device's OTA endpoint URL; increase timeout |
