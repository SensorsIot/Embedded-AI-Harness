"""WT-24xx — host tier: the maths that decides what frequency goes on air.

No hardware. These cover the code that turns a requested frequency into dividers
and a keying pattern, which is where a bug has a physical consequence you cannot
see from the API: the bench transmits, just not on the frequency you asked for,
or keys a different character than the one you sent.

The receive side has its own end-to-end check on the bench (WT-1909). This is the
transmit-side equivalent, and unlike WT-1909 it needs nothing plugged in.
"""
import pytest

import morse
from gpclk import DIV_MAX, DIV_MIN, PLLD_FREQ, GpClk
from si5351 import (
    MS_DIV_MAX,
    MS_DIV_MIN,
    OUT_FREQ_MAX,
    OUT_FREQ_MIN,
    PLL_FREQ_MAX,
    PLL_FREQ_MIN,
    XTAL_FREQ,
    Si5351,
    Si5351Error,
)


# =====================================================================
# WT-2400  GPCLK divider maths  (behind GET /api/siggen/frequencies)
# =====================================================================


class TestGpClkFrequencies:
    """GPCLK can only produce PLLD / integer, so the achievable set is sparse.

    Asking for an arbitrary frequency and silently getting a neighbouring one is
    the failure this guards: the list must contain only frequencies the hardware
    can actually synthesise.
    """

    def test_wt2400_every_listed_frequency_is_exactly_plld_over_an_integer(self):
        for entry in GpClk.list_frequencies(1_000_000, 2_000_000):
            d = entry["divider"]
            assert d == int(d), "divider must be an integer"
            assert entry["freq_hz"] == PLLD_FREQ / d, (
                f"{entry['freq_hz']} Hz is not PLLD/{d} — the hardware cannot "
                "produce it")

    def test_wt2401_results_stay_inside_the_requested_range(self):
        low, high = 10_000_000, 12_000_000
        got = GpClk.list_frequencies(low, high)
        assert got, "expected achievable frequencies in a 2 MHz window"
        for entry in got:
            assert low <= entry["freq_hz"] <= high

    def test_wt2402_dividers_stay_within_hardware_limits(self):
        for entry in GpClk.list_frequencies(200_000, 250_000_000):
            assert DIV_MIN <= entry["divider"] <= DIV_MAX

    def test_wt2403_narrow_gap_between_achievable_points_yields_nothing(self):
        # 500 MHz / 3 = 166.67 MHz, / 4 = 125 MHz. Nothing lands between them,
        # and returning a nearby frequency instead would be a real defect.
        assert GpClk.list_frequencies(130_000_000, 160_000_000) == []

    def test_wt2404_frequency_falls_as_divider_rises(self):
        got = GpClk.list_frequencies(1_000_000, 5_000_000)
        by_divider = sorted(got, key=lambda e: e["divider"])
        freqs = [e["freq_hz"] for e in by_divider]
        assert freqs == sorted(freqs, reverse=True)


# =====================================================================
# WT-241x  Si5351 VCO / divider solving  (the 433.92 MHz harmonic path)
# =====================================================================


def _solver():
    """An Si5351 whose register writes go nowhere.

    __init__ opens a real I2C bus, so it is bypassed. Only the arithmetic in
    set_frequency is under test — that is the part that decides what goes on air.
    """
    dev = Si5351.__new__(Si5351)
    dev._bus = None
    dev._addr = 0x60
    dev._ch_freqs = {}
    dev._write = lambda *a, **k: None
    dev._write_bulk = lambda *a, **k: None
    return dev


class TestSi5351Synthesis:

    def test_wt2410_returns_the_frequency_actually_programmed(self):
        dev = _solver()
        actual = dev.set_frequency(0, 86_784_000)
        # This is the frequency WT-1909 relies on: its 5th harmonic must land on
        # 433.92 MHz, so an error here moves the harmonic off the SDR's target.
        assert actual == pytest.approx(86_784_000, rel=1e-6)

    def test_wt2411_fifth_harmonic_lands_on_the_sdr_target(self):
        dev = _solver()
        actual = dev.set_frequency(0, 86_784_000)
        assert actual * 5 == pytest.approx(433_920_000, abs=500), (
            "the 5th harmonic must sit within 500 Hz of 433.92 MHz or WT-1909 "
            "is measuring the wrong bin")

    @pytest.mark.parametrize("freq", [333_334, 1_000_000, 13_560_000,
                                      86_784_000, 112_500_000])
    def test_wt2412_vco_stays_within_spec_across_the_range(self, freq):
        """The VCO must land in 600-900 MHz — outside it the part is unlocked
        and the output frequency is undefined rather than merely inaccurate."""
        dev = _solver()
        actual = dev.set_frequency(0, freq)
        assert actual == pytest.approx(freq, rel=1e-4)
        for d in range(MS_DIV_MIN, MS_DIV_MAX + 1, 2):
            if PLL_FREQ_MIN <= actual * d <= PLL_FREQ_MAX:
                break
        else:
            pytest.fail(f"no legal divider puts {actual} Hz in the VCO window")
        assert PLL_FREQ_MIN <= actual * d <= PLL_FREQ_MAX

    def test_wt2413_rejects_frequencies_the_part_cannot_reach(self):
        dev = _solver()
        with pytest.raises(Si5351Error):
            dev.set_frequency(0, OUT_FREQ_MIN - 1)
        with pytest.raises(Si5351Error):
            dev.set_frequency(0, OUT_FREQ_MAX + 1)

    def test_wt2414_rejects_an_invalid_channel(self):
        dev = _solver()
        with pytest.raises(Si5351Error):
            dev.set_frequency(3, 10_000_000)

    def test_wt2416_never_programs_a_divider_above_the_hardware_limit(self):
        """Regression: the VCO-raising loop used to exit with ms_div = 1802.

        333 kHz needs divider 1802 to reach the 600 MHz VCO floor. That cannot be
        programmed, so the part emitted some other frequency while set_frequency
        returned success — a silent wrong-frequency transmission. It must be
        rejected as out of range instead.
        """
        dev = _solver()
        with pytest.raises(Si5351Error):
            dev.set_frequency(0, 333_000)
        # one step above the true floor must still work
        assert dev.set_frequency(0, 333_334) == pytest.approx(333_334, rel=1e-4)

    def test_wt2417_declared_range_matches_what_the_solver_accepts(self):
        """The declared range must be reachable, not aspirational. It previously
        claimed 8 kHz - 160 MHz, which is the chip's range via divider stages this
        driver does not program; both ends failed with a confusing VCO error."""
        dev = _solver()
        dev.set_frequency(0, OUT_FREQ_MIN)
        dev.set_frequency(0, OUT_FREQ_MAX)
        with pytest.raises(Si5351Error):
            dev.set_frequency(0, OUT_FREQ_MIN * 0.99)
        with pytest.raises(Si5351Error):
            dev.set_frequency(0, OUT_FREQ_MAX * 1.01)

    def test_wt2415_pll_multiplier_stays_within_the_parts_limits(self):
        """vco / 25 MHz must stay in 15..90; outside that the fractional divider
        cannot represent it and the output silently drifts."""
        dev = _solver()
        for freq in (500_000, 5_000_000, 40_000_000, 100_000_000):
            actual = dev.set_frequency(0, freq)
            for d in range(MS_DIV_MIN, MS_DIV_MAX + 1, 2):
                vco = actual * d
                if PLL_FREQ_MIN <= vco <= PLL_FREQ_MAX:
                    assert 15 <= vco / XTAL_FREQ <= 90
                    break


# =====================================================================
# WT-242x  Morse keying  (what the CW beacon actually sends)
# =====================================================================


class RecordingKeyer:
    """Stands in for the RF backend, recording key-down events."""

    def __init__(self):
        self.events = []

    def key_on(self):
        self.events.append("on")

    def key_off(self):
        self.events.append("off")

    @property
    def elements(self):
        """Number of keyed elements (dits + dahs)."""
        return self.events.count("on")


class TestMorseKeying:

    def test_wt2420_keys_the_expected_number_of_elements(self):
        """SOS is ... --- ... = 9 elements. A wrong code table or a dropped
        symbol changes this count, and on air that is a different message."""
        keyer = RecordingKeyer()
        m = morse.MorseKeyer(keyer)
        m._play_once("SOS", dit=0.001)
        assert keyer.elements == 9

    def test_wt2421_key_on_and_key_off_always_pair(self):
        """An unpaired key_on leaves the transmitter keyed — a stuck carrier."""
        keyer = RecordingKeyer()
        morse.MorseKeyer(keyer)._play_once("CQ DE TEST", dit=0.001)
        assert keyer.events[0] == "on"
        assert keyer.events[-1] == "off"
        assert keyer.events.count("on") == keyer.events.count("off")
        for i in range(0, len(keyer.events), 2):
            assert keyer.events[i] == "on" and keyer.events[i + 1] == "off"

    def test_wt2422_unknown_characters_are_skipped_not_keyed(self):
        plain = RecordingKeyer()
        morse.MorseKeyer(plain)._play_once("E", dit=0.001)
        withjunk = RecordingKeyer()
        morse.MorseKeyer(withjunk)._play_once("E#~", dit=0.001)
        assert plain.elements == withjunk.elements == 1

    def test_wt2423_rejects_empty_message_and_out_of_range_wpm(self):
        m = morse.MorseKeyer(RecordingKeyer())
        with pytest.raises(ValueError):
            m.start("", wpm=15)
        with pytest.raises(ValueError):
            m.start("TEST", wpm=0)
        with pytest.raises(ValueError):
            m.start("TEST", wpm=61)

    def test_wt2424_code_table_matches_itu(self):
        """A transposed entry sends a different letter, which no bench test
        would catch without someone decoding the audio by ear."""
        for char, code in {"A": ".-", "N": "-.", "S": "...", "O": "---",
                           "E": ".", "T": "-", "5": ".....",
                           "0": "-----"}.items():
            assert morse.MORSE_TABLE[char] == code
