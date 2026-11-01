"""Host tier for FR-040: the identity probe runs once per board, not per wake."""
import pytest

import debug_controller as dc

MAC = "48:27:E2:EA:48:3C"


@pytest.mark.parametrize("probed,serial,chip,want", [
    (None, MAC, None, True),         # first sight of a board
    (MAC, MAC, "esp32s3", False),    # the same board back from deep sleep
    ("AA:BB", MAC, "esp32s3", True),  # another board in the socket
    (MAC, MAC, None, True),          # identified, but the chip is unknown
    (None, None, None, True),        # no serial number: cannot be recognised
    (None, None, "esp32", True),     # still none on a later add
])
def test_fr040_probe_needed(probed, serial, chip, want):
    assert dc.probe_needed(probed, serial, chip) is want
