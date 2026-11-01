"""
MQTT Impair Controller — impairs one AP client's TCP traffic to the test broker
(FR-040).

Verifies a DUT's MQTT recovery under a dead link (`cut`) and under links that
stall part-way (`drop-large`, `drop-after`). Every rule lives in one
bench-owned chain, jumped to from the top of INPUT. The chain and its jump
exist only while an impairment does: the last clear or timeout removes both,
and portal start and bench reset remove any left by an earlier process.

The client address is validated by the caller (the portal, as composition
root), which owns the AP subnet rules; this module validates its own
parameters and does not depend on the WiFi controller.
"""

import logging
import subprocess
import threading
import time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CHAIN = "TB_MQTT_IMPAIR"
BROKER_PORT = 1883
MODES = ("cut", "drop-large", "drop-after")
DEFAULT_BYTES = {"drop-large": 300, "drop-after": 2000}
MIN_BYTES = 1
MAX_BYTES = 65535
MIN_DURATION_S = 1.0
MAX_DURATION_S = 3600.0

# ---------------------------------------------------------------------------
# Pure core
# ---------------------------------------------------------------------------


def validate_params(mode, nbytes, duration_s):
    """Return (mode, bytes, duration_s) with defaults applied, or raise ValueError."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {', '.join(MODES)}")
    if mode == "cut":
        if nbytes is not None:
            raise ValueError("bytes is not accepted with mode cut")
    elif nbytes is None:
        nbytes = DEFAULT_BYTES[mode]
    elif isinstance(nbytes, bool) or not isinstance(nbytes, int):
        raise ValueError("bytes must be an integer")
    elif not (MIN_BYTES <= nbytes <= MAX_BYTES):
        raise ValueError(f"bytes must be {MIN_BYTES}-{MAX_BYTES}")
    if duration_s is not None:
        try:
            duration_s = float(duration_s)
        except (TypeError, ValueError):
            raise ValueError("duration_s must be a number") from None
        if not (MIN_DURATION_S <= duration_s <= MAX_DURATION_S):
            raise ValueError(
                f"duration_s must be {MIN_DURATION_S:g}-{MAX_DURATION_S:g}")
    return mode, nbytes, duration_s


def rule_args(iface: str, client_ip: str, mode: str, nbytes) -> list:
    """The iptables rule (after the chain name) for one client's impairment."""
    args = ["-i", iface, "-s", client_ip, "-p", "tcp", "--dport", str(BROKER_PORT)]
    if mode == "drop-large":
        args += ["-m", "length", "--length", f"{nbytes}:{MAX_BYTES}"]
    elif mode == "drop-after":
        args += ["-m", "connbytes", "--connbytes", f"{nbytes}:",
                 "--connbytes-dir", "original", "--connbytes-mode", "bytes"]
    return args + ["-j", "DROP"]

# ---------------------------------------------------------------------------
# Impairment state
# ---------------------------------------------------------------------------


def _run_iptables(args: list) -> int:
    return subprocess.run(args, capture_output=True, timeout=10,
                          check=False).returncode


class Impairer:
    """One impairment per client, each with an optional self-lifting timer.

    `run` executes an iptables argv and returns its exit code; the portal uses
    the real one, host tests a fake.
    """

    def __init__(self, run=_run_iptables, iface: str = "wlan0"):
        self._run = run
        self._iface = iface
        self._lock = threading.Lock()
        self._active = {}  # client_ip -> dict(mode, bytes, rule, deadline, timer)

    def _ensure_chain(self):
        self._run(["iptables", "-N", CHAIN])  # fails harmlessly if it exists
        jump = ["-j", CHAIN]
        if self._run(["iptables", "-C", "INPUT"] + jump) != 0:
            self._run(["iptables", "-I", "INPUT", "1"] + jump)

    def _drop_chain(self):
        # Every jump goes, including duplicates left by an earlier process.
        while self._run(["iptables", "-D", "INPUT", "-j", CHAIN]) == 0:
            pass
        self._run(["iptables", "-F", CHAIN])
        self._run(["iptables", "-X", CHAIN])

    def _remove_unlocked(self, client_ip: str) -> bool:
        entry = self._active.pop(client_ip, None)
        if entry is None:
            return False
        if entry["timer"] is not None:
            entry["timer"].cancel()
        self._run(["iptables", "-D", CHAIN] + entry["rule"])
        if not self._active:
            self._drop_chain()
        return True

    def impair(self, client_ip: str, mode: str, nbytes, duration_s=None) -> None:
        """Install (or replace) the impairment of one already validated client."""
        rule = rule_args(self._iface, client_ip, mode, nbytes)
        with self._lock:
            self._remove_unlocked(client_ip)
            self._ensure_chain()
            if self._run(["iptables", "-A", CHAIN] + rule) != 0:
                raise RuntimeError(f"iptables refused the {mode} rule for {client_ip}")
            timer = deadline = None
            if duration_s is not None:
                deadline = time.monotonic() + duration_s
                timer = threading.Timer(duration_s, self._expire)
                # The timer passes itself, so a replaced one can tell it is stale.
                timer.args = (client_ip, timer)
                timer.daemon = True
            self._active[client_ip] = dict(mode=mode, bytes=nbytes, rule=rule,
                                           deadline=deadline, timer=timer)
            if timer is not None:
                timer.start()
        logger.info("mqtt impair %s: %s bytes=%s duration=%s",
                    client_ip, mode, nbytes, duration_s)

    def _expire(self, client_ip: str, timer) -> None:
        with self._lock:
            entry = self._active.get(client_ip)
            # A replaced impairment's timer may fire after its replacement.
            if entry is None or entry["timer"] is not timer:
                return
            entry["timer"] = None
            self._remove_unlocked(client_ip)
        logger.info("mqtt impair %s: duration ran out", client_ip)

    def clear(self, client_ip=None) -> list:
        """Lift one client's impairment, or every one; return those lifted."""
        with self._lock:
            targets = [client_ip] if client_ip else list(self._active)
            cleared = [ip for ip in targets if self._remove_unlocked(ip)]
        if cleared:
            logger.info("mqtt impair cleared: %s", cleared)
        return cleared

    def reset(self) -> None:
        """Remove the chain and its jump, including any left by a previous process."""
        with self._lock:
            for entry in self._active.values():
                if entry["timer"] is not None:
                    entry["timer"].cancel()
            self._active.clear()
            self._drop_chain()

    def status(self) -> list:
        now = time.monotonic()
        with self._lock:
            return [
                {"client_ip": ip, "mode": e["mode"], "bytes": e["bytes"],
                 "remaining_s": (None if e["deadline"] is None
                                 else round(max(0.0, e["deadline"] - now), 1))}
                for ip, e in sorted(self._active.items())
            ]
