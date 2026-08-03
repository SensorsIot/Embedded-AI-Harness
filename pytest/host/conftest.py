"""Host-tier fixtures: no Pi, no dongle, no DUT.

These tests import the Pi's modules directly and exercise pure logic, so they run
on a laptop in milliseconds. They take no `--wt-url` and must never touch
hardware, the network, or the filesystem — if a test here needs any of those, it
belongs in the bench tier instead.
"""
import pathlib
import sys

PI = pathlib.Path(__file__).resolve().parents[2] / "pi"
if str(PI) not in sys.path:
    sys.path.insert(0, str(PI))
