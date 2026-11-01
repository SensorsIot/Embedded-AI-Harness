"""Host tier: opening a native-USB ESP32's port never passes through reset.

USB-Serial/JTAG holds the chip in reset while RTS=1 and DTR=0. The kernel
raises both lines on open, so the proxy must drop RTS before DTR.
"""
import pytest

serial = pytest.importorskip("serial")
import plain_rfc2217_server as srv  # noqa: E402


class LineRecorder:
    """Mimics pyserial's POSIX Serial for the control lines only."""

    def __init__(self):
        self.dsrdtr = False
        self._dtr = self._rts = True   # not yet open: lines as the setters see them
        self.is_open = False
        self.line = None                # physical (dtr, rts) once open
        self.history = []

    def _set(self, dtr, rts):
        self.line = (dtr, rts)
        self.history.append(self.line)

    @property
    def dtr(self):
        return self._dtr

    @dtr.setter
    def dtr(self, v):
        self._dtr = v
        if self.is_open:
            self._set(v, self.line[1])

    @property
    def rts(self):
        return self._rts

    @rts.setter
    def rts(self, v):
        self._rts = v
        if self.is_open:
            self._set(self.line[0], v)

    def open(self):
        # cdc-acm raises DTR and RTS together, then pyserial writes DTR
        # (unless dsrdtr) and then RTS -- serialposix.Serial.open().
        self.is_open = True
        self._set(True, True)
        if not self.dsrdtr:
            self._set(self._dtr, self.line[1])
        self._set(self.line[0], self._rts)


IN_RESET = (False, True)   # (dtr, rts)


def test_open_and_release_never_reset():
    ser = LineRecorder()
    srv.quiet_open_settings(ser)
    ser.open()
    srv.release_control_lines(ser)
    assert IN_RESET not in ser.history
    assert ser.line == (False, False)


def test_plain_pyserial_order_would_reset():
    """The regression: setting dtr/rts False before open is not enough."""
    ser = LineRecorder()
    ser.dtr = False
    ser.rts = False
    ser.open()
    assert IN_RESET in ser.history


def test_release_from_client_left_lines_high():
    ser = LineRecorder()
    ser.open()
    ser.dtr = True
    ser.rts = True
    ser.history.clear()
    srv.release_control_lines(ser)
    assert IN_RESET not in ser.history
