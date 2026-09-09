"""
MQTT Controller — manages a mosquitto broker for ESP32 MQTT client testing.

Used by the portal to start/stop a local MQTT broker accessible to devices
on the testbench WiFi AP, and to take part in the traffic on it: the bench
can publish, subscribe, and keep what it hears in a buffer a test can
assert against.
"""

import collections
import logging
import os
import re
import subprocess
import threading
import time
from datetime import datetime, timezone

try:
    import paho.mqtt.client as mqtt
except ImportError:                                  # optional dependency
    mqtt = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MQTT_PORT = 1883
WORK_DIR = "/tmp/mqtt-tester"
MOSQUITTO_CONF = os.path.join(WORK_DIR, "mosquitto.conf")
MOSQUITTO_LOG = os.path.join(WORK_DIR, "mosquitto.log")
MSG_BUF_MAXLEN = 1000
PUBLISH_TIMEOUT = 5.0

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_active = False
_proc = None

# The bench's own client on its own broker. Kept separate from the broker
# state above and never touched while `_lock` is held: stopping it joins
# paho's network thread, and joining a thread under a lock that thread might
# want is how a status poll hangs the whole portal.
_internal_client = None

# A bounded deque, like the activity log and the UDP log in portal.py.
# `append` on a maxlen deque drops the oldest in one atomic step, so the
# network thread needs no lock to record a message and cannot be blocked by
# a reader.
_messages: collections.deque = collections.deque(maxlen=MSG_BUF_MAXLEN)

# What we asked the broker for. paho reconnects on its own after a drop and
# comes back subscribed to nothing, so the set is replayed in on_connect —
# otherwise the buffer quietly stops filling and every later assertion reads
# as "the device published nothing".
_subscriptions: set = set()
_sub_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_work_dir():
    os.makedirs(WORK_DIR, exist_ok=True)


def _kill_proc(proc, timeout=5.0):
    """Terminate a subprocess, SIGKILL if it won't die."""
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.terminate()
    except OSError:
        return
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except OSError:
            pass


def _kill_existing():
    """Kill a previously-started *test* broker, and only that (best effort).

    The pattern is matched against our own config path, not the bare word
    "mosquitto". A broad `pkill -f mosquitto` also kills a system
    `mosquitto.service` or any other broker on the host — a test fixture must
    never take down infrastructure it does not own.

    This reclaims the port after a portal restart, where the old broker is still
    running but `_proc` no longer refers to it.
    """
    try:
        subprocess.run(
            ["pkill", "-f", f"mosquitto -c {MOSQUITTO_CONF}"],
            capture_output=True, timeout=5, check=False,
        )
        time.sleep(0.3)
    except Exception:
        pass


def _port_owner() -> str:
    """Describe what is listening on MQTT_PORT, or '' if nothing is."""
    try:
        out = subprocess.run(
            ["ss", "-tlnp", f"sport = :{MQTT_PORT}"],
            capture_output=True, timeout=5, check=False,
        ).stdout.decode(errors="replace")
    except Exception:
        return ""
    lines = [ln for ln in out.splitlines()[1:] if ln.strip()]
    return lines[0].strip() if lines else ""


# ---------------------------------------------------------------------------
# The bench's own client
# ---------------------------------------------------------------------------

def _on_connect(client, userdata, flags, rc, properties=None):
    """Replay the subscriptions — this also runs after an automatic reconnect."""
    with _sub_lock:
        topics = sorted(_subscriptions)
    for topic in topics:
        try:
            client.subscribe(topic)
        except Exception as e:
            logger.error("MQTT re-subscribe to %s failed: %s", topic, e)
    if topics:
        logger.info("MQTT internal client subscribed to %s", ", ".join(topics))


def _on_message(client, userdata, msg):
    """Record one message. Runs on paho's network thread — takes no lock."""
    try:
        _messages.append({
            "topic": msg.topic,
            "payload": msg.payload.decode(errors="replace"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.error("MQTT on_message failed: %s", e)


def _start_internal_client():
    """Connect the bench's own client. Never call this holding `_lock`."""
    global _internal_client
    if mqtt is None:
        logger.warning("paho-mqtt is not installed — publish/subscribe disabled")
        return
    try:
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:                       # paho 1.x
            client = mqtt.Client()
        client.on_connect = _on_connect
        client.on_message = _on_message
        client.connect("127.0.0.1", MQTT_PORT, 60)
        client.loop_start()
        _internal_client = client
        logger.info("MQTT internal client started")
    except Exception as e:
        _internal_client = None
        logger.error("MQTT internal client failed to start: %s", e)


def _stop_internal_client():
    """Disconnect the bench's own client. Never call this holding `_lock`."""
    global _internal_client
    client, _internal_client = _internal_client, None
    if client is None:
        return
    try:
        client.loop_stop()
        client.disconnect()
    except Exception as e:
        logger.error("MQTT internal client failed to stop cleanly: %s", e)
    logger.info("MQTT internal client stopped")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start():
    """Start the mosquitto MQTT broker. Returns dict with port."""
    global _active, _proc

    with _lock:
        already_up = _active and _proc is not None and _proc.poll() is None

        if not already_up:
            _ensure_work_dir()
            _kill_existing()

            # If something still holds the port it is not ours, so refuse rather
            # than kill it. Silently killing a broker we did not start is how a
            # test run takes down a service somebody else depends on.
            owner = _port_owner()
            if owner:
                raise RuntimeError(
                    f"port {MQTT_PORT} is already in use by a broker this service "
                    f"did not start; stop it first. Listener: {owner}")

            # Write mosquitto config — open broker, no auth, all interfaces
            conf_lines = [
                f"listener {MQTT_PORT}",
                "allow_anonymous true",
                f"log_dest file {MOSQUITTO_LOG}",
                "log_type all",
            ]
            with open(MOSQUITTO_CONF, "w") as f:
                f.write("\n".join(conf_lines) + "\n")

            # Start mosquitto
            _proc = subprocess.Popen(
                ["mosquitto", "-c", MOSQUITTO_CONF],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )

            # Wait for it to initialise
            time.sleep(1.0)
            if _proc.poll() is not None:
                out = _proc.stdout.read().decode(errors="replace")
                _active = False
                raise RuntimeError(f"mosquitto failed to start: {out[:500]}")

            _active = True
            logger.info("MQTT broker started on port %d", MQTT_PORT)

    # Everything below runs outside the lock on purpose — see
    # `_internal_client`.
    if already_up:
        # Idempotent: the broker keeps running and the buffer keeps its
        # history. Only revive the client if it has gone away underneath.
        if _internal_client is None:
            _start_internal_client()
        return {"port": MQTT_PORT}

    # A fresh broker has heard nothing, so the buffer and the subscriptions
    # start empty as well.
    _stop_internal_client()
    _messages.clear()
    with _sub_lock:
        _subscriptions.clear()
    _start_internal_client()
    return {"port": MQTT_PORT}


def stop():
    """Stop the mosquitto broker."""
    global _active, _proc

    _stop_internal_client()
    with _lock:
        _kill_proc(_proc)
        _proc = None
        _active = False
        logger.info("MQTT broker stopped")


def status():
    """Return broker status dict."""
    global _active

    with _lock:
        running = _active and _proc is not None and _proc.poll() is None
        # If process died unexpectedly, update state
        died = _active and not running
        if died:
            _active = False
        result = {
            "running": running,
            "port": MQTT_PORT if running else None,
        }

    # The client outlives a broker that died under it and would go on trying
    # to reconnect to nothing. Torn down here, after the lock.
    if died:
        _stop_internal_client()

    result["internal_client"] = {
        "running": _internal_client is not None,
        "library_available": mqtt is not None,
    }
    return result


def publish(topic, payload, qos=0, retain=False):
    """Publish one message from the bench."""
    client = _internal_client
    if client is None:
        raise RuntimeError(
            "MQTT internal client is not running — start the broker first"
            + ("" if mqtt is not None else " (paho-mqtt is not installed)"))

    info = client.publish(topic, payload, qos=qos, retain=retain)
    # An unbounded wait here is a portal request thread parked forever on a
    # broker that has stopped answering.
    info.wait_for_publish(timeout=PUBLISH_TIMEOUT)
    if not info.is_published():
        raise RuntimeError(
            f"broker did not confirm the publish within {PUBLISH_TIMEOUT:g}s")
    return {"ok": True, "topic": topic, "qos": qos, "retain": retain}


def subscribe(topic):
    """Subscribe the bench's client to *topic*.

    Nothing is subscribed by default: a bench-wide `#` would fill the buffer
    with every other consumer's traffic and make a test's own messages hard
    to find. A test asks for what it wants to hear.
    """
    client = _internal_client
    if client is None:
        raise RuntimeError(
            "MQTT internal client is not running — start the broker first"
            + ("" if mqtt is not None else " (paho-mqtt is not installed)"))

    with _sub_lock:
        _subscriptions.add(topic)
    client.subscribe(topic)
    return {"ok": True, "topic": topic}


def get_messages(topic_filter=None, content_filter=None, limit=100,
                 use_regex=False):
    """Return buffered messages, newest last, optionally filtered.

    Filters are substring matches by default, regular expressions when
    `use_regex` is set. A malformed expression raises `re.error`: returning
    the unfiltered buffer instead would let an assertion pass on messages it
    never actually matched.
    """
    messages = list(_messages)

    if topic_filter:
        if use_regex:
            pattern = re.compile(topic_filter)
            messages = [m for m in messages if pattern.search(m["topic"])]
        else:
            messages = [m for m in messages if topic_filter in m["topic"]]

    if content_filter:
        if use_regex:
            pattern = re.compile(content_filter)
            messages = [m for m in messages if pattern.search(m["payload"])]
        else:
            messages = [m for m in messages if content_filter in m["payload"]]

    return messages[-limit:] if limit else messages


def clear_messages():
    """Empty the message buffer, keeping the subscriptions."""
    _messages.clear()
    return {"ok": True}
