#!/usr/bin/env python3
"""
Plain RFC2217 server using pyserial's standard PortManager.

Required for ESP32-C3 native USB Serial/JTAG (ttyACM) devices,
where DTR/RTS must pass through directly for bootloader entry.

Espressif's esp_rfc2217_server uses EspPortManager which intercepts
DTR/RTS and runs its own reset sequence in a separate thread. This
works for UART bridge chips (ttyUSB / CP2102 / CH340) but breaks
ESP32-C3 native USB because the chip's USB controller handles
bootloader entry internally via DTR/RTS signals.

This server uses pyserial's standard serial.rfc2217.PortManager
which passes DTR/RTS directly to the serial device — exactly what
the C3 native USB needs.

The portal detects ttyACM devices and launches this server instead
of esp_rfc2217_server automatically.
"""
import argparse
import logging
import socket
import termios
import threading
import time

import serial
import serial.rfc2217



# On a native-USB ESP32 (USB-Serial/JTAG) the control lines are not modem
# lines: RTS=1 with DTR=0 holds the chip in reset, DTR=1 with RTS=0 only
# selects download mode, which is latched at reset and so harmless to a
# running chip, and (1,1) and (0,0) are both idle. The kernel's CDC ACM driver
# raises both lines on open, so the port starts at (1,1). Dropping DTR first
# passes through (RTS=1, DTR=0) -- a reset -- which restarted every board
# that woke from deep sleep, since the portal reopens the port each time the
# board re-enumerates. Always drop RTS first: (1,1) -> (DTR=1, RTS=0) -> (0,0)
# never enters the reset state. esptool walks the same path for the same
# reason ("go through (1,1) instead of (0,0)").


def release_control_lines(ser) -> None:
    """Drop RTS, then DTR, so the port never passes through reset."""
    ser.rts = False
    ser.dtr = False


def quiet_open_settings(ser) -> None:
    """Prepare *ser* so that open() leaves DTR alone and only drops RTS.

    pyserial's open() writes DTR before RTS. With dsrdtr set it skips DTR
    (on POSIX the flag does nothing else), so open() moves (1,1) only to
    (DTR=1, RTS=0); release_control_lines() then drops DTR. The caller clears
    dsrdtr after that.
    """
    ser.dsrdtr = True
    ser.rts = False
    ser.dtr = False


def main():
    parser = argparse.ArgumentParser(
        description="Plain RFC2217 server (direct DTR/RTS passthrough)")
    parser.add_argument("SERIALPORT")
    parser.add_argument("-p", "--localport", type=int, default=2217)
    parser.add_argument("-m", "--monitor-port", type=int, default=0,
                        help="plain read-only fan-out port (0 disables)")
    parser.add_argument("-b", "--baud", type=int, default=115200,
                        help="line rate when no client has negotiated one")
    parser.add_argument("-v", "--verbose", dest="verbosity",
                        action="count", default=0)
    args = parser.parse_args()

    level = (logging.WARNING, logging.INFO, logging.DEBUG, logging.NOTSET)[
        min(args.verbosity, 3)]
    logging.basicConfig(format="%(levelname)s: %(message)s",
                        level=logging.INFO)
    logging.getLogger("rfc2217").setLevel(level)

    # Exclusive: TIOCEXCL makes the kernel refuse a second open, so a stray
    # client fails loudly instead of silently stealing bytes or asserting the
    # control lines. Nothing on this bench opens the devnode while the proxy
    # holds it — every portal path that needs it stops the proxy first, and
    # ModemManager and brltty are inactive — but a bench where something does
    # would otherwise fail to start, so fall back and say so rather than
    # leaving a slot dead.
    ser = serial.serial_for_url(args.SERIALPORT, do_not_open=True,
                                exclusive=True)
    ser.timeout = 3
    # A write with no deadline blocks forever when the device stops accepting
    # bytes, and this is the thread that owns the one RFC2217 client slot —
    # so one stuck write wedges the port for every later client, which then
    # sees "the port is busy or doesn't exist".
    ser.write_timeout = 10
    # pyserial defaults to 9600, and the port sits at whatever it was last set
    # to whenever no client is attached — so the permanent drain, and every
    # observer on the fan-out, would read an ESP32 console at the wrong rate
    # and see only noise. Default to the rate these devices actually use.
    ser.baudrate = args.baud
    quiet_open_settings(ser)
    try:
        ser.open()
    except Exception as exc:
        logging.warning("exclusive open of %s refused (%s) — retrying "
                        "non-exclusively; another process holds this device",
                        args.SERIALPORT, exc)
        ser = serial.serial_for_url(args.SERIALPORT, do_not_open=True,
                                    exclusive=False)
        ser.timeout = 3
        ser.write_timeout = 10
        ser.baudrate = args.baud
        quiet_open_settings(ser)
        ser.open()
    if hasattr(ser, 'fd'):
        attrs = termios.tcgetattr(ser.fd)
        attrs[2] &= ~termios.HUPCL  # cflag: clear HUPCL
        termios.tcsetattr(ser.fd, termios.TCSANOW, attrs)
    release_control_lines(ser)
    ser.dsrdtr = False
    time.sleep(0.1)
    settings = ser.get_settings()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("", args.localport))
    srv.listen(1)
    logging.info("Listening on port %d for %s", args.localport,
                 args.SERIALPORT)

    # ---- read-only fan-out -------------------------------------------------
    #
    # RFC2217 stays single-client, because negotiation applies control-line
    # changes to the port: a second RFC2217 client could assert DTR or RTS,
    # which on a native-USB ESP32 means download mode or reset. So observers
    # get a separate plain port instead — raw bytes, no negotiation, no way to
    # touch the device. Reading is then free and unlimited, and nothing that
    # merely watches can disturb what it is watching.
    monitors: list = []
    monitors_lock = threading.Lock()

    def monitor_acceptor(msrv):
        while True:
            try:
                conn, addr = msrv.accept()
            except OSError:
                return
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with monitors_lock:
                monitors.append(conn)
            logging.info("Monitor attached from %s (%d total)", addr, len(monitors))

    if args.monitor_port:
        msrv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        msrv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        msrv.bind(("", args.monitor_port))
        msrv.listen(8)
        threading.Thread(target=monitor_acceptor, args=(msrv,), daemon=True).start()
        logging.info("Monitor fan-out on port %d", args.monitor_port)

    def fan_out(data: bytes):
        if not data:
            return
        dead = []
        with monitors_lock:
            for conn in monitors:
                try:
                    conn.sendall(data)
                except (BrokenPipeError, OSError):
                    dead.append(conn)
            for conn in dead:
                monitors.remove(conn)
                try:
                    conn.close()
                except OSError:
                    pass
        if dead:
            logging.info("Monitor detached (%d remain)", len(monitors))

    # The control client, when one is attached. Guarded because the drain
    # thread runs whether or not anybody is connected.
    control = {"conn": None, "pm": None}
    control_lock = threading.Lock()
    # serial.rfc2217.PortManager is NOT thread-safe, and there are now two
    # threads touching it: the permanent drain calls escape() on whatever the
    # device emits, while the client thread calls filter() on whatever the
    # client sends. Interleaving them corrupts the telnet state machine and a
    # write is silently swallowed — intermittently, because it only happens
    # when the device emits at the moment a client writes.
    pm_lock = threading.Lock()

    def drain():
        """Read the device forever and distribute.

        Permanent, not per-connection: the port is open for the life of this
        process, so a device that logs would otherwise fill its buffer with
        nobody reading. Draining always also means the fan-out has something
        to fan.
        """
        while True:
            try:
                data = ser.read(ser.in_waiting or 1)
            except Exception as exc:
                logging.warning("serial read failed: %s", exc)
                time.sleep(0.2)
                continue
            if not data:
                continue
            fan_out(data)
            with control_lock:
                conn, pm = control["conn"], control["pm"]
            if conn is not None:
                try:
                    with pm_lock:
                        escaped = b"".join(pm.escape(data))
                    conn.sendall(escaped)
                except (BrokenPipeError, OSError):
                    with control_lock:
                        control["conn"] = None

    threading.Thread(target=drain, daemon=True).start()

    while True:
        srv.settimeout(5)
        conn = None
        try:
            while conn is None:
                try:
                    conn, addr = srv.accept()
                except TimeoutError:
                    pass
        except KeyboardInterrupt:
            break

        logging.info("Client connected from %s", addr)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # Neither this socket nor the serial write had a deadline, so a client
        # that stopped reading — an esptool killed mid-flash — left this
        # thread blocked and the connection in CLOSE-WAIT. The proxy stayed
        # alive and kept reporting `running`, and refused every later client.
        # A bench reset did not help: the process was healthy, only wedged.
        conn.settimeout(30)

        class Sender:
            def write(self_, data):
                try:
                    conn.sendall(data)
                except (BrokenPipeError, OSError):
                    pass

        try:
            pm = serial.rfc2217.PortManager(
                ser, Sender(),
                logger=logging.getLogger("rfc2217") if args.verbosity > 0
                else None,
            )
        except (BrokenPipeError, OSError):
            logging.info("Client disconnected during negotiation")
            conn.close()
            continue

        with control_lock:
            control["conn"], control["pm"] = conn, pm

        try:
            while True:
                try:
                    data = conn.recv(1024)
                except TimeoutError:
                    continue          # idle client, not a dead one
                if not data:
                    break
                with pm_lock:
                    payload = b"".join(pm.filter(data))
                if payload:
                    ser.write(payload)
        except Exception as exc:
            logging.info("Client dropped: %s", exc)

        with control_lock:
            control["conn"], control["pm"] = None, None
        conn.close()
        logging.info("Client disconnected")
        release_control_lines(ser)
        ser.apply_settings(settings)


if __name__ == "__main__":
    main()
