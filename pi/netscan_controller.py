"""
Netscan Controller — TCP connect check of one host on the bench AP network
(FR-039).

Verifies a DUT's claim that it exposes no listening service. The target rules
are enforced in `validate_target` before any connection is made: a single IPv4
address inside the AP subnet, never the Pi itself. The caller (the portal, as
composition root) supplies the subnet and the Pi's AP address, so this module
does not depend on the WiFi controller.
"""

import concurrent.futures
import ipaddress
import logging
import socket
import time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_IN_FLIGHT = 128
CONNECT_TIMEOUT_S = 1.0
DEFAULT_PORTS = "1-65535"
DEFAULT_TIMEOUT_S = 120.0
MIN_TIMEOUT_S = 1.0
MAX_TIMEOUT_S = 600.0

# ---------------------------------------------------------------------------
# Pure core
# ---------------------------------------------------------------------------


def validate_target(host, subnet: str, self_ip: str) -> str:
    """Return the normalised address, or raise ValueError naming the reason."""
    if not isinstance(host, str) or "/" in host:
        raise ValueError("host must be a single IPv4 address")
    try:
        addr = ipaddress.IPv4Address(host.strip())
    except ipaddress.AddressValueError:
        raise ValueError("host must be a single IPv4 address") from None
    net = ipaddress.IPv4Network(subnet, strict=True)
    if addr not in net:
        raise ValueError(f"host {addr} is outside the AP subnet {net}")
    if addr in (net.network_address, net.broadcast_address):
        raise ValueError(f"host {addr} is the network or broadcast address")
    if addr == ipaddress.IPv4Address(self_ip):
        raise ValueError(f"host {addr} is the testbench itself")
    return str(addr)


def parse_ports(spec) -> list:
    """Parse "22,80,1000-2000" into a sorted, de-duplicated list of ports."""
    if not isinstance(spec, str) or not spec.strip():
        raise ValueError("ports must be a non-empty string")
    ports = set()
    for item in spec.split(","):
        item = item.strip()
        lo_s, sep, hi_s = item.partition("-")
        if not lo_s.isdigit() or (sep and not hi_s.isdigit()):
            raise ValueError(f"bad port item {item!r}")
        lo = int(lo_s)
        hi = int(hi_s) if sep else lo
        if not (1 <= lo <= hi <= 65535):
            raise ValueError(f"port item {item!r} is outside 1-65535 or reversed")
        ports.update(range(lo, hi + 1))
    return sorted(ports)


def clamp_timeout(value) -> float:
    """The total budget in seconds, within MIN_TIMEOUT_S..MAX_TIMEOUT_S."""
    if value is None:
        return DEFAULT_TIMEOUT_S
    try:
        t = float(value)
    except (TypeError, ValueError):
        raise ValueError("timeout_s must be a number") from None
    if not (MIN_TIMEOUT_S <= t <= MAX_TIMEOUT_S):
        raise ValueError(f"timeout_s must be {MIN_TIMEOUT_S:g}-{MAX_TIMEOUT_S:g}")
    return t

# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------


def _accepts(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(CONNECT_TIMEOUT_S)
        return s.connect_ex((host, port)) == 0


def scan(host: str, ports: list, timeout_s: float) -> dict:
    """Connect-check `ports` on an already validated `host` within timeout_s."""
    start = time.monotonic()
    deadline = start + timeout_s
    open_ports = []
    scanned = 0
    pending = iter(ports)
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_IN_FLIGHT) as pool:
        in_flight = {}
        while True:
            # Keep the pool full until the budget would be overrun.
            while (len(in_flight) < MAX_IN_FLIGHT
                   and time.monotonic() + CONNECT_TIMEOUT_S <= deadline):
                port = next(pending, None)
                if port is None:
                    break
                in_flight[pool.submit(_accepts, host, port)] = port
            if not in_flight:
                break
            done, _ = concurrent.futures.wait(
                in_flight, timeout=max(0.0, deadline - time.monotonic()) + CONNECT_TIMEOUT_S,
                return_when=concurrent.futures.FIRST_COMPLETED)
            if not done:
                break
            for fut in done:
                port = in_flight.pop(fut)
                scanned += 1
                if fut.result():
                    open_ports.append(port)
    complete = scanned == len(ports)
    elapsed = round(time.monotonic() - start, 1)
    logger.info("portscan %s: %d/%d ports, open=%s, complete=%s",
                host, scanned, len(ports), sorted(open_ports), complete)
    return {"host": host, "open": sorted(open_ports), "scanned": scanned,
            "complete": complete, "elapsed_s": elapsed}
