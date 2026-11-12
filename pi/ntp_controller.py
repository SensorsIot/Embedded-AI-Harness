"""
NTP Controller — an on-demand SNTP server on UDP 123 that logs every request
it answers (FR-040).

A test fixture: DUTs on the isolated AP get a time source, and a test can see
that a DUT asked and which address it asked. Started and stopped on demand by
the portal, like the MQTT test broker.

The reply is built by a pure function so the host tier can test it.
"""

import collections
import logging
import socket
import struct
import subprocess
import threading
import time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NTP_PORT = 123
LOG_MAX = 1000
NTP_EPOCH_OFFSET = 2208988800          # seconds from 1900-01-01 to 1970-01-01
PACKET_LEN = 48
MODE_CLIENT, MODE_SERVER = 3, 4

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_sock = None
_thread = None
_stop = threading.Event()
_requests: collections.deque = collections.deque(maxlen=LOG_MAX)

# ---------------------------------------------------------------------------
# Pure core
# ---------------------------------------------------------------------------


def to_ntp(t: float) -> bytes:
    """Unix time → 64-bit NTP timestamp."""
    secs = int(t) + NTP_EPOCH_OFFSET
    frac = int((t - int(t)) * (1 << 32)) & 0xFFFFFFFF
    return struct.pack("!II", secs & 0xFFFFFFFF, frac)


def build_reply(request: bytes, recv_time: float, tx_time: float, clock_synced: bool):
    """The server reply to one datagram, or None when it is not a client
    request (shorter than 48 bytes, or mode other than 3)."""
    if len(request) < PACKET_LEN:
        return None
    version = (request[0] >> 3) & 0x7
    if request[0] & 0x7 != MODE_CLIENT:
        return None
    leap, stratum = (0, 2) if clock_synced else (3, 16)
    head = struct.pack("!BBbb", (leap << 6) | (version << 3) | MODE_SERVER, stratum, 4, -20)
    root = struct.pack("!II", 0, 0)                 # root delay, root dispersion
    ref_id = b"LOCL"
    return (head + root + ref_id
            + to_ntp(recv_time)                     # reference timestamp
            + request[40:48]                        # originate = client's transmit
            + to_ntp(recv_time)                     # receive
            + to_ntp(tx_time))                      # transmit


def request_version(request: bytes) -> int:
    return (request[0] >> 3) & 0x7

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------


def clock_synced() -> bool:
    """True when systemd reports the Pi's clock as NTP-synchronised."""
    try:
        out = subprocess.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() == "yes"
    except Exception:
        return False


def _serve(sock, synced_flag):
    while not _stop.is_set():
        try:
            data, addr = sock.recvfrom(512)
        except socket.timeout:
            continue
        except OSError:
            break
        recv = time.time()
        reply = build_reply(data, recv, time.time(), synced_flag["synced"])
        if reply is None:
            continue
        try:
            sock.sendto(reply, addr)
        except OSError as exc:
            logger.info("ntp: reply to %s failed: %s", addr[0], exc)
            continue
        _requests.append({"ts": recv, "source": addr[0], "version": request_version(data)})


def _refresh(synced_flag):
    """Re-read the clock state every 60 s while running."""
    while not _stop.wait(60):
        synced_flag["synced"] = clock_synced()


def status() -> dict:
    with _lock:
        running = _sock is not None
    return {"running": running, "port": NTP_PORT, "clock_synced": clock_synced(),
            "requests": len(_requests)}


def requests(since: float = 0.0, source: str = "", limit: int = 200) -> list:
    out = []
    for r in list(_requests):
        if r["ts"] <= since or (source and r["source"] != source):
            continue
        out.append(r)
        if len(out) >= limit:
            break
    return out


def start() -> dict:
    """Start the server (idempotent). Raises OSError naming the port on bind failure."""
    global _sock, _thread
    with _lock:
        if _sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.bind(("0.0.0.0", NTP_PORT))
            except OSError as exc:
                sock.close()
                raise OSError(f"cannot bind UDP port {NTP_PORT}: {exc}") from exc
            sock.settimeout(1.0)
            _stop.clear()
            flag = {"synced": clock_synced()}
            _thread = threading.Thread(target=_serve, args=(sock, flag), name="ntp", daemon=True)
            _thread.start()
            threading.Thread(target=_refresh, args=(flag,), name="ntp-clock", daemon=True).start()
            _sock = sock
            logger.info("ntp: listening on UDP %d", NTP_PORT)
    return status()


def stop() -> bool:
    """Stop the server (idempotent). Returns True when it was running."""
    global _sock, _thread
    with _lock:
        sock, _sock = _sock, None
        thread, _thread = _thread, None
    if sock is None:
        return False
    _stop.set()
    if thread is not None:
        thread.join(timeout=5)
    sock.close()
    logger.info("ntp: stopped")
    return True
