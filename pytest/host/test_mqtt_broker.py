"""Host tier for the FR-029 test broker's config. Pure logic only."""
import mqtt_controller as mq


def test_fr029_broker_logs_to_stdout_not_a_file():
    # mosquitto drops to user `mosquitto` and cannot create a file in the
    # root-owned work dir, so `log_dest file` silently logged nothing. The
    # portal (root) redirects the broker's stdout to MOSQUITTO_LOG instead.
    lines = mq.broker_config(1883).splitlines()
    assert "log_dest stdout" in lines
    assert not any(ln.startswith("log_dest file") for ln in lines)


def test_fr029_broker_listens_open_on_the_port():
    lines = mq.broker_config(1883).splitlines()
    assert "listener 1883" in lines
    assert "allow_anonymous true" in lines
