# Waveshare USB-TO-LoRa DTU — Notes & Reference

Working notes for the **Waveshare USB-TO-LoRa** sticks (SX1262, LF/433 model),
as characterised on the Universal Embedded Workbench. Written for a multi-station
(4+) addressed network. Product wiki: `waveshare.com/wiki/USB-TO-LoRa-xF`.

> Everything here is **verified on hardware** unless marked ⚠️. It corrects an
> earlier version of this doc that pre-dated cracking the AT interface.

---

## 0. TL;DR / hard-won rules

- **NEVER press the button.** On these sticks the button is **firmware-update
  mode**, not config. Pressing it wedges the stick in the bootloader (goes silent
  / answers `?>`). Recover with a clean power-cycle (see §2).
- **AT config needs `+++\r\n` with DTR & RTS asserted (=True).** The workbench
  RFC2217 proxy opens ports with DTR=RTS=**False**, which is why `+++` never
  works through it. Configure via the **raw devnode** (DTR=RTS=True) — see §4.
- **All config commands end in `\r\n`.** Frequency: **channel = MHz − 410**
  (ch 23 = 433 MHz default, ch 24 = 434 MHz).
- **Addressing = packet mode** (`AT+MODE=2`): prefix each message with
  `[dest_hi][dest_lo][channel]`. `FF FF` = broadcast. See §6.

## 1. What these are

- Waveshare **USB-TO-LoRa** stick: SX1262 LoRa radio behind a **WCH CH343**
  USB-serial bridge (`1a86:55d3`, enumerates as `/dev/ttyACM*`). Firmware Ver 1.2.
- Default personality is a **transparent data pipe** at 115200 8N1. Configured
  over an AT command set (§5). Three working modes: **stream** (default),
  **packet** (addressed), **relay** (§6).
- Factory defaults: `MODE=1` (stream), `ADDR=0`, `NETID=0`, `TXCH=RXCH=23`
  (433 MHz), `SF=7`, `BW=0` (125 kHz), `CR=1` (4/5), `PWR=22`, `115200 8N1`.

## 2. The button = firmware update — and recovery

From the manual: *"Press and hold the button for 2 seconds to enter firmware
update mode… release when TXD and RXD lights are on simultaneously."* So the
button is **only** for reflashing firmware. If pressed:

- The stick leaves normal mode → the bootloader answers `?>` to anything, then
  can go fully silent. It stops relaying LoRa and won't accept AT.
- **Recover:** unplug completely, wait ~10 s, **replug without touching the
  button**, wait >3 s. It boots back to normal mode. (Verified: this revived two
  wedged sticks.)
- If a genuinely clean power-cycle doesn't revive it, it needs Waveshare's
  **firmware-update tool** + the `.ws` firmware file — a USB re-enumeration alone
  won't fix it (VBUS stays up), and the bench can't force a real power-cycle on a
  bus-powered stick.

## 3. Reaching them on the workbench

Two different needs, two different setups:

| Purpose | How | DTR/RTS |
|---------|-----|---------|
| **Data** (transparent/packet traffic) | RFC2217 port (`rfc2217://<host>:400x`) is fine | False works |
| **AT config** | **raw devnode**, not the proxy | **DTR=RTS=True** required |

The proxy holds the devnode and its supervisor restarts it if killed, so before
opening the raw devnode: **`POST /api/stop {slot_key}`** (clean stop, supervisor
won't grab it back), do the AT work over SSH on the Pi, then **`POST /api/start`**
to restore. Do NOT SSH to drive DUTs in general — this is the one config case, and
only because the proxy can't assert DTR/RTS the way AT entry needs.

## 4. Entering AT mode (the method that works)

On the **raw devnode**, 115200 8N1, **DTR=True, RTS=True**:

```
(idle ≥1 s)  +++\r\n     → enters AT mode (echoes "+++")
             AT+VER\r\n  → "Ver1.2\r\nOK"
             …config…
             AT+EXIT\r\n → back to transparent/data mode
```

Reply format is `"<echoed cmd>\n\r\n+KEY=value\r\n\r\nOK\r\n"`. Notes:
- **`+++` must have `\r\n`** here, and DTR/RTS asserted. Bare `+++` or DTR/RTS
  low → it's treated as data (sent over the air) or returns `ERROR`.
- Echo is on by default; `ATE\r\n` toggles it.
- ⚠️ An AT session can go quiet after several commands or after `EXIT`+reopen —
  use **short sessions** and **re-read in a fresh session** to confirm a write.
- Settings persist to NVM (survive power-cycle).

## 5. AT command reference

Query `AT+X?`, set `AT+X=value`, all `\r\n`-terminated.

| Command | Meaning | Notes / range |
|---------|---------|---------------|
| `+++` | enter AT mode | needs `\r\n` + DTR/RTS high |
| `AT+EXIT` | leave AT → data mode | |
| `ATE` | toggle command echo | |
| `AT+VER` | firmware version | e.g. `Ver1.2` |
| `AT+HELP` | list commands | |
| `AT+MODE` | working mode | **1=stream, 2=packet, 3=relay** |
| `AT+ADDR` | node address | 0–65535; **65535 = broadcast** |
| `AT+NETID` | network id | 0–65535 |
| `AT+TXCH` / `AT+RXCH` | TX / RX channel | 0–80; **MHz = 410 + ch** (LF model) |
| `AT+SF` | spreading factor | 7–12 |
| `AT+BW` | bandwidth | 0=125 kHz, 1=250, 2=500 |
| `AT+CR` | coding rate (FEC) | 1=4/5 … 4=4/8 |
| `AT+PWR` | TX power | 10–22 dBm |
| `AT+LBT` | listen-before-talk | 0/1 |
| `AT+RSSI` | append RSSI to RX data | 0/1 |
| `AT+BAUD` | UART baud | 1200–115200 |
| `AT+COMM` | UART framing | e.g. `"8N1"` |
| `AT+AllP` | dump/set all params | read: `AT+AllP?` |
| `AT+RESTORE=1` | factory reset | |

**Frequency:** channel = MHz − 410. So **434 MHz = ch 24**, 433 = 23 (default),
etc.

## 6. Modes & addressing (the multi-station part)

- **Stream mode (`MODE=1`, default):** a broadcast *group* — devices with the
  **same ADDR + channel** hear each other; different ADDR = deaf to each other.
  `ADDR=65535` = broadcast/listen-all on the channel. No per-message targeting.
- **Packet mode (`MODE=2`) — use this for an addressed network.** Each message
  is prefixed with **3 bytes: `[dest_hi][dest_lo][channel]`**, then the payload.
  The radio routes to that address; the **receiver outputs just the payload**
  (prefix is consumed). `FF FF <ch>` = broadcast. A wrong/absent address is
  silently dropped. ✅ Verified: ADDR 1 ↔ ADDR 4 on ch 24, 6/6 both directions;
  `→ addr 9` (no such node) delivered nothing.
  - To reach **ADDR 4 on ch 24 (0x18)**: send `00 04 18` + data.
  - To reach **ADDR 1**: send `00 01 18` + data.
  - Broadcast: `FF FF 18` + data.
- **Relay mode (`MODE=3`):** a repeater node forwards between others; the relay
  node uses a different `NETID` from the endpoints. ⚠️ not tested here.

**For a 4-station addressed network:** all nodes on one channel + NETID + same
SF/BW/CR, each a unique `ADDR`, all in **packet mode**; each node prefixes the
destination address. (Our built config in §8.)

## 7. Error correction & reliability

LoRa gives integrity for free, but not delivery:
- **FEC** via coding rate (default `CR=1` = 4/5; up to 4/8 for more robustness).
- **CRC** on the LoRa payload — the SX1262 drops failed packets in hardware, so
  **corrupt bytes are never delivered** (unlike weak-CRC OOK sensors — no
  plausibility filter needed on this link).
- **No ARQ** (no ACK/retransmit): a packet lost to a failed CRC is simply gone →
  **loss, never corruption.** If delivery must be guaranteed, add app-layer
  **sequence + ACK + retransmit** (detection is already handled by the CRC).

## 8. The 4-station config we built (434 MHz)

All on **channel 24 (434 MHz)**, `SF7 / BW125 / CR4-5 / NETID0`:

| USB serial | Address | Mode |
|-----------|:---:|------|
| …514 | 1 | packet ✅ |
| …334 | 2 | stream (convert to packet) |
| …331 | 3 | stream (convert to packet) |
| …287 | 4 | packet ✅ |

(For a uniform addressed network, set …334/…331 to `MODE=2` as well.)

## 9. Performance vs packet length (SF7/BW125/CR4-5)

~50–60 ms fixed cost per packet (preamble + framing), so throughput climbs with
size; **batch into ~240-byte frames**, don't dribble:

| payload | latency | throughput |
|--------:|--------:|-----------:|
| 4 B | 61 ms | 66 B/s |
| 64 B | 162 ms | 396 B/s |
| 240 B | 445 ms | ~540 B/s |

First packet after idle can drop (warm-up) — send a keepalive/throwaway if it
matters. Numbers scale with SF/BW/CR.

---

## Appendix A — config over the raw devnode (Python, run on the Pi)

Enters AT with DTR/RTS asserted, sets address + channel, reads back. Stop the
proxy first (`POST /api/stop {slot_key}`), restart after.

```python
import serial, time, glob, re

dev = sorted(glob.glob("/dev/ttyACM*"))[0]

def sess():
    s = serial.Serial()
    s.port = dev; s.baudrate = 115200; s.timeout = 0.1
    s.dtr = True; s.rts = True          # <-- the key: control lines asserted
    s.open(); s.dtr = True; s.rts = True
    return s

def rd(s, t):
    end = time.time() + t; b = b""
    while time.time() < end:
        n = s.in_waiting
        b += s.read(n) if n else b""
        if not n: time.sleep(0.02)
    return b

def at(s, c, t=0.7):
    s.reset_input_buffer(); s.write(c); s.flush(); time.sleep(0.4); return rd(s, t)

ADDR, CH = 1, 24          # station address, channel (434 MHz)
s = sess(); time.sleep(1.0); s.reset_input_buffer()
at(s, b"+++\r\n", 1.0)
at(s, b"AT+MODE=2\r\n")                        # packet mode
at(s, ("AT+ADDR=%d\r\n" % ADDR).encode())
at(s, ("AT+TXCH=%d\r\n" % CH).encode())
at(s, ("AT+RXCH=%d\r\n" % CH).encode())
at(s, b"AT+EXIT\r\n")
s.close()
# confirm in a FRESH session (an AT session can go quiet after many commands)
s = sess(); time.sleep(1.0); s.reset_input_buffer(); at(s, b"+++\r\n", 1.0)
print("ADDR:", at(s, b"AT+ADDR?\r\n"))
print("TXCH:", at(s, b"AT+TXCH?\r\n"))
at(s, b"AT+EXIT\r\n"); s.close()
```

## Appendix B — packet-mode addressed link test

Two sticks in packet mode; sends addressed frames and checks delivery + that a
wrong address is filtered.

```python
import serial, time
def op(dev):
    s = serial.Serial(); s.port = dev; s.baudrate = 115200; s.timeout = 0.1
    s.dtr = True; s.rts = True; s.open(); s.dtr = True; s.rts = True; return s
def rd(s, t):
    end = time.time() + t; b = b""
    while time.time() < end:
        n = s.in_waiting
        b += s.read(n) if n else b""
        if not n: time.sleep(0.02)
    return b

a1 = op("/dev/ttyACM0")     # ADDR 1
a4 = op("/dev/ttyACM1")     # ADDR 4
CH = 0x18                   # channel 24
def frame(dst, data): return bytes([(dst >> 8) & 0xff, dst & 0xff, CH]) + data

# warm up (first packet after idle often drops)
a4.reset_input_buffer(); a1.write(frame(4, b"w\n")); a1.flush(); rd(a4, 1.5)
a1.reset_input_buffer(); a4.write(frame(1, b"w\n")); a4.flush(); rd(a1, 1.5)

a4.reset_input_buffer(); a1.write(frame(4, b"hi 1->4\n")); a1.flush(); time.sleep(1)
print("1->4:", rd(a4, 1.5))          # -> b'hi 1->4\n'  (payload only)
a1.reset_input_buffer(); a4.write(frame(1, b"hi 4->1\n")); a4.flush(); time.sleep(1)
print("4->1:", rd(a1, 1.5))          # -> b'hi 4->1\n'
a4.reset_input_buffer(); a1.write(frame(9, b"nobody\n")); a1.flush(); time.sleep(1)
print("1->9:", rd(a4, 1.5))          # -> b''  (wrong address, dropped)
a1.close(); a4.close()
```
