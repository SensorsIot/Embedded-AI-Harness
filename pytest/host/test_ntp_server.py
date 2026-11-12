"""Host tier for the NTP server (FR-040). Pure logic only — no sockets."""
import struct

import ntp_controller as ntp


def _request(version=4, mode=3, length=48, tx=b"\x11" * 8):
    pkt = bytes([(version << 3) | mode]) + b"\0" * 39 + tx
    return pkt[:length] if length <= 48 else pkt + b"\0" * (length - 48)


def test_fr040_answers_a_client_request():
    tx = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    r = ntp.build_reply(_request(version=4, tx=tx), 1762960000.25, 1762960000.5, True)
    assert len(r) == 48
    assert r[0] & 0x7 == 4, "mode 4 (server)"
    assert (r[0] >> 3) & 0x7 == 4, "the request's version"
    assert r[24:32] == tx, "originate = the client's transmit timestamp"
    secs, frac = struct.unpack("!II", r[40:48])
    assert secs - ntp.NTP_EPOCH_OFFSET == 1762960000 and abs(frac / 2**32 - 0.5) < 1e-6
    secs, _ = struct.unpack("!II", r[32:40])
    assert secs - ntp.NTP_EPOCH_OFFSET == 1762960000, "receive timestamp"


def test_fr040_copies_version_3():
    r = ntp.build_reply(_request(version=3), 0.0, 0.0, True)
    assert (r[0] >> 3) & 0x7 == 3


def test_fr040_drops_a_short_packet():
    assert ntp.build_reply(_request(length=47), 0.0, 0.0, True) is None


def test_fr040_drops_a_non_client_packet():
    assert ntp.build_reply(_request(mode=4), 0.0, 0.0, True) is None


def test_fr040_synced_clock_is_stratum_2_leap_0():
    r = ntp.build_reply(_request(), 0.0, 0.0, True)
    assert r[0] >> 6 == 0 and r[1] == 2


def test_fr040_unsynced_clock_is_never_served_as_good():
    r = ntp.build_reply(_request(), 0.0, 0.0, False)
    assert r[0] >> 6 == 3 and r[1] == 16
