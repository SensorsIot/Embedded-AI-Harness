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
    # pyserial defaults to 9600, and the port sits at whatever it was last set
    # to whenever no client is attached — so the permanent drain, and every
    # observer on the fan-out, would read an ESP32 console at the wrong rate
    # and see only noise. Default to the rate these devices actually use.
    ser.baudrate = args.baud
    ser.dtr = False
    ser.rts = False
    try:
        ser.open()
    except Exception as exc:
        logging.warning("exclusive open of %s refused (%s) — retrying "
                        "non-exclusively; another process holds this device",
                        args.SERIALPORT, exc)
        ser = serial.serial_for_url(args.SERIALPORT, do_not_open=True,
                                    exclusive=False)
        ser.timeout = 3
        ser.baudrate = args.baud
        ser.dtr = False
        ser.rts = False
        ser.open()
    # Linux CDC ACM driver asserts DTR+RTS on open.  On ESP32-C3 native USB,
    # the USB-Serial/JTAG controller interprets DTR/RTS as reset + boot-mode
    # signals.  DTR=1 → GPIO9 LOW (download mode), RTS=1 → chip in reset.
    #
    # Controlled boot sequence to ensure SPI boot (not download mode):
    #   1. Clear DTR first  → GPIO9 HIGH (SPI boot selected)
    #   2. Brief delay      → let the USB-JTAG controller see DTR=0
    #   3. Clear RTS        → release reset → chip boots in SPI mode
    if hasattr(ser, 'fd'):
        attrs = termios.tcgetattr(ser.fd)
        attrs[2] &= ~termios.HUPCL  # cflag: clear HUPCL
        termios.tcsetattr(ser.fd, termios.TCSANOW, attrs)
    ser.dtr = False          # GPIO9 HIGH — select SPI boot
    time.sleep(0.1)          # Let USB-JTAG controller latch DTR=0
    ser.rts = False          # Release reset — chip boots normally
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
                data = conn.recv(1024)
                if not data:
                    break
                with pm_lock:
                    payload = b"".join(pm.filter(data))
                if payload:
                    ser.write(payload)
        except Exception:
            pass

        with control_lock:
            control["conn"], control["pm"] = None, None
        conn.close()
        logging.info("Client disconnected")
        ser.dtr = False
        ser.rts = False
        ser.apply_settings(settings)


if __name__ == "__main__":
    main()
