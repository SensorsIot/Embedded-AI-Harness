"""Host tier for FR-040 (MQTT broker link impairment). Pure logic and the
impairment state, driven against a fake iptables — no real firewall."""
import time

import pytest

import mqtt_impair_controller as imp

IF = "wlan0"
DUT = "192.168.4.15"
OTHER = "192.168.4.16"
CHAIN = imp.CHAIN


class FakeIptables:
    """Just enough of iptables' filter table to see what the Impairer leaves."""

    def __init__(self):
        self.chains = {"INPUT": []}

    def __call__(self, args):
        assert args[0] == "iptables"
        op, chain, rule = args[1], args[2], args[3:]
        if op == "-N":
            if chain in self.chains:
                return 1
            self.chains[chain] = []
        elif op == "-F":
            if chain not in self.chains:
                return 1
            self.chains[chain] = []
        elif op == "-X":
            # Real iptables refuses to delete a chain that is referenced or not empty.
            if (chain not in self.chains or self.chains[chain]
                    or any(["-j", chain] == r for r in self.chains["INPUT"])):
                return 1
            del self.chains[chain]
        elif op == "-C":
            return 0 if rule in self.chains[chain] else 1
        elif op == "-A":
            self.chains[chain].append(rule)
        elif op == "-I":
            self.chains[chain].insert(int(rule[0]) - 1, rule[1:])
        elif op == "-D":
            if rule not in self.chains[chain]:
                return 1
            self.chains[chain].remove(rule)
        else:
            raise AssertionError(f"unexpected iptables op {op}")
        return 0

    def rules_for(self, ip):
        return [r for r in self.chains.get(CHAIN, []) if ip in r]


@pytest.fixture
def fw():
    return FakeIptables()


@pytest.fixture
def impairer(fw):
    i = imp.Impairer(run=fw, iface=IF)
    yield i
    i.clear()


# ── Validation ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("mode,nbytes,want", [
    ("cut", None, None), ("drop-large", None, 300), ("drop-after", None, 2000),
    ("drop-large", 1, 1), ("drop-after", 65535, 65535),
])
def test_fr040_accepts_modes_and_defaults_the_threshold(mode, nbytes, want):
    assert imp.validate_params(mode, nbytes, None) == (mode, want, None)


@pytest.mark.parametrize("mode,nbytes,duration", [
    ("bogus", None, None), (None, None, None),
    ("drop-large", 0, None), ("drop-large", 65536, None), ("drop-after", "a", None),
    ("drop-large", 2.5, None), ("drop-large", True, None),
    ("cut", 300, None),
    ("cut", None, 0), ("cut", None, 3601), ("cut", None, "x"),
])
def test_fr040_refuses_bad_params(mode, nbytes, duration):
    with pytest.raises(ValueError):
        imp.validate_params(mode, nbytes, duration)


def test_fr040_accepts_a_duration_within_range():
    assert imp.validate_params("cut", None, 1) == ("cut", None, 1.0)
    assert imp.validate_params("cut", None, 3600) == ("cut", None, 3600.0)


# ── Rule shape ───────────────────────────────────────────────────────────

SCOPE = ["-i", IF, "-s", DUT, "-p", "tcp", "--dport", "1883"]


def test_fr040_cut_rule_drops_everything_in_scope():
    assert imp.rule_args(IF, DUT, "cut", None) == SCOPE + ["-j", "DROP"]


def test_fr040_drop_large_rule_matches_ip_length():
    assert imp.rule_args(IF, DUT, "drop-large", 300) == SCOPE + [
        "-m", "length", "--length", "300:65535", "-j", "DROP"]


def test_fr040_drop_after_rule_matches_original_direction_bytes():
    assert imp.rule_args(IF, DUT, "drop-after", 2000) == SCOPE + [
        "-m", "connbytes", "--connbytes", "2000:", "--connbytes-dir", "original",
        "--connbytes-mode", "bytes", "-j", "DROP"]


# ── State ────────────────────────────────────────────────────────────────

def test_fr040_impair_installs_one_rule_and_the_jump(fw, impairer):
    impairer.impair(DUT, "drop-large", 300)
    assert fw.rules_for(DUT) == [imp.rule_args(IF, DUT, "drop-large", 300)]
    assert fw.chains["INPUT"][0] == ["-j", CHAIN]


def test_fr040_jump_is_installed_once(fw, impairer):
    impairer.impair(DUT, "cut", None)
    impairer.impair(OTHER, "cut", None)
    assert fw.chains["INPUT"].count(["-j", CHAIN]) == 1


def test_fr040_impairing_again_replaces_the_rule(fw, impairer):
    impairer.impair(DUT, "drop-large", 300)
    impairer.impair(DUT, "drop-after", 2000)
    assert fw.rules_for(DUT) == [imp.rule_args(IF, DUT, "drop-after", 2000)]
    assert [s["mode"] for s in impairer.status()] == ["drop-after"]


def test_fr040_clear_one_client_leaves_the_other(fw, impairer):
    impairer.impair(DUT, "cut", None)
    impairer.impair(OTHER, "cut", None)
    assert impairer.clear(DUT) == [DUT]
    assert fw.rules_for(DUT) == []
    assert fw.rules_for(OTHER) != []


def assert_no_trace(fw):
    assert CHAIN not in fw.chains
    assert ["-j", CHAIN] not in fw.chains["INPUT"]


def test_fr040_clear_all_removes_the_chain_and_jump(fw, impairer):
    impairer.impair(DUT, "cut", None)
    impairer.impair(OTHER, "drop-large", 300)
    assert sorted(impairer.clear()) == [DUT, OTHER]
    assert_no_trace(fw)
    assert impairer.status() == []


def test_fr040_clearing_the_last_client_removes_the_chain(fw, impairer):
    impairer.impair(DUT, "cut", None)
    impairer.impair(OTHER, "cut", None)
    impairer.clear(DUT)
    assert CHAIN in fw.chains
    impairer.clear(OTHER)
    assert_no_trace(fw)


def test_fr040_chain_comes_back_after_removal(fw, impairer):
    impairer.impair(DUT, "cut", None)
    impairer.clear()
    impairer.impair(DUT, "drop-large", 300)
    assert fw.rules_for(DUT) == [imp.rule_args(IF, DUT, "drop-large", 300)]
    assert fw.chains["INPUT"].count(["-j", CHAIN]) == 1


def test_fr040_clearing_an_unimpaired_client_is_not_an_error(impairer):
    assert impairer.clear(DUT) == []


def test_fr040_duration_lifts_the_impairment(fw, impairer):
    impairer.impair(DUT, "cut", None, duration_s=0.1)
    assert impairer.status()[0]["remaining_s"] is not None
    time.sleep(0.3)
    assert_no_trace(fw)
    assert impairer.status() == []


def test_fr040_replacing_cancels_the_old_timer(fw, impairer):
    impairer.impair(DUT, "cut", None, duration_s=0.1)
    impairer.impair(DUT, "drop-large", 300)
    time.sleep(0.3)
    assert fw.rules_for(DUT) == [imp.rule_args(IF, DUT, "drop-large", 300)]


def test_fr040_no_duration_reports_null_remaining(impairer):
    impairer.impair(DUT, "cut", None)
    assert impairer.status() == [
        {"client_ip": DUT, "mode": "cut", "bytes": None, "remaining_s": None}]


def test_fr040_reset_removes_a_chain_left_by_a_previous_process(fw):
    fw.chains[CHAIN] = [imp.rule_args(IF, DUT, "cut", None)]
    fw.chains["INPUT"] = [["-j", CHAIN], ["-j", CHAIN]]
    imp.Impairer(run=fw, iface=IF).reset()
    assert_no_trace(fw)


def test_fr040_reset_on_a_clean_firewall_creates_nothing(fw):
    imp.Impairer(run=fw, iface=IF).reset()
    assert fw.chains == {"INPUT": []}


def test_fr040_a_failed_install_raises_and_records_nothing(impairer):
    impairer._run = lambda args: 1 if args[1] == "-A" else 0
    with pytest.raises(RuntimeError):
        impairer.impair(DUT, "cut", None)
    assert impairer.status() == []
