#!/usr/bin/env python3
"""Discover ESP32 Testbench instances on the network.

Sends UDP DISCOVER probes to every host on the gateway subnet and collects
responses from any testbench portal running a beacon responder (port 5888).

Works from inside Docker containers where broadcast/multicast cannot cross
the Docker bridge — uses a fast unicast sweep of the /24 subnet instead.

Usage:
    python3 discover-testbench.py              # print JSON result
    python3 discover-testbench.py --hosts      # also write /etc/hosts entry
    python3 discover-testbench.py --timeout 2  # custom timeout
"""

import argparse
import json
import socket
import sys

BEACON_PORT = 5888
DEFAULT_TIMEOUT = 2


def _get_subnet_ips():
    """Derive the gateway /24 subnet from resolv.conf nameserver."""
    ips = []
    try:
        with open("/etc/resolv.conf") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[0] == "nameserver":
                    octets = parts[1].split(".")
                    if len(octets) == 4:
                        prefix = ".".join(octets[:3])
                        ips.extend(f"{prefix}.{i}" for i in range(1, 255))
                        break  # use first nameserver only
    except OSError:
        pass
    return ips


def discover(timeout=DEFAULT_TIMEOUT):
    """Send DISCOVER probes to every IP on the subnet, collect responses."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    # Fire off probes to all 254 IPs — UDP sends are non-blocking
    for ip in _get_subnet_ips():
        try:
            sock.sendto(b"DISCOVER", (ip, BEACON_PORT))
        except OSError:
            pass

    # Collect responses until timeout
    results = []
    seen = set()
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            source_ip = addr[0]
            if source_ip in seen:
                continue
            seen.add(source_ip)
            try:
                info = json.loads(data.decode())
                info["source_ip"] = source_ip
                results.append(info)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        except socket.timeout:
            break
    sock.close()
    return results


def write_hosts_entry(hostname, ip):
    """Add or update an /etc/hosts entry for the testbench."""
    hosts_path = "/etc/hosts"
    marker = "# testbench-discovery"
    new_line = f"{ip}\t{hostname}\t{marker}\n"

    try:
        with open(hosts_path) as f:
            lines = f.readlines()
    except OSError:
        lines = []

    # Remove old discovery entries
    lines = [line for line in lines if marker not in line]
    lines.append(new_line)

    try:
        with open(hosts_path, "w") as f:
            f.writelines(lines)
        return True
    except PermissionError:
        print(f"Permission denied writing {hosts_path} — run with sudo",
              file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Discover ESP32 Testbench")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help=f"Seconds to wait for responses (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--hosts", action="store_true",
                        help="Write discovered testbench to /etc/hosts")
    parser.add_argument("--quiet", action="store_true",
                        help="Only output on success")
    parser.add_argument("--url", action="store_true",
                        help="Print only the base URL, for: export TESTBENCH_URL=$(... --url)")
    parser.add_argument("--name",
                        help="Only the bench with this hostname (case-insensitive). "
                             "Needed once more than one bench answers.")
    args = parser.parse_args()

    results = discover(timeout=args.timeout)

    if args.name:
        wanted = args.name.lower().removesuffix(".local")
        results = [w for w in results
                   if w.get("hostname", "").lower() == wanted]

    if not results:
        if not args.quiet:
            which = f" named {args.name}" if args.name else ""
            print(f"No ESP32 Testbench{which} found", file=sys.stderr)
        return 1

    # --url must name exactly one bench, or the caller would export the wrong
    # address. Two benches answer here, so silence is not an option.
    if args.url:
        if len(results) > 1:
            names = ", ".join(sorted(w.get("hostname", "?") for w in results))
            print(f"{len(results)} benches answered ({names}) — pass --name to choose",
                  file=sys.stderr)
            return 2
        print(f"http://{results[0]['source_ip']}:{results[0]['port']}")
        return 0

    for wb in results:
        hostname = wb.get("hostname", "testbench")
        # The address the reply actually came from, not the one the payload
        # claims. The portal caches its own IP and refreshes it periodically,
        # so after the bench changes address the beacon advertises the old one
        # until that refresh runs — and the whole point of the beacon is to say
        # where to connect. A source address cannot be stale.
        ip = wb["source_ip"]
        fqdn = f"{hostname}.local"

        if not args.quiet:
            print(json.dumps(wb, indent=2))

        if args.hosts:
            if write_hosts_entry(fqdn, ip):
                if not args.quiet:
                    print(f"Wrote {ip}\t{fqdn} to /etc/hosts")

    return 0


if __name__ == "__main__":
    sys.exit(main())
