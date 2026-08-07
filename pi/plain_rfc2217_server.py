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
    parser.add_argument("-v", "--verbose", dest="verbosity",
                        action="count", default=0)
    args = parser.parse_args()

    level = (logging.WARNING, logging.INFO, logging.DEBUG, logging.NOTSET)[
        min(args.verbosity, 3)]
    logging.basicConfig(format="%(levelname)s: %(message)s",
                        level=logging.INFO)
    logging.getLogger("rfc2217").setLevel(level)

    ser = serial.serial_for_url(args.SERIALPORT, do_not_open=True,
                                exclusive=False)
    # Read timeout doubles as the reader thread's shutdown latency (it only
    # re-checks its alive flag between blocking reads), which in turn gates
    # how soon the next client can attach after a disconnect. Keep it short.
    ser.timeout = 0.25
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

        handle_client(conn, addr, ser, settings, args.verbosity)


def handle_client(conn, addr, ser, settings, verbosity):
    """One client session. All session state (conn, PortManager, alive
    flag) lives in this call's scope, and the reader thread is joined
    before returning.

    These used to be main()-loop variables shared across sessions via the
    reader closure, and the reader was never joined — a reader blocked in
    ser.read() (3s port timeout) survived its own session's teardown, and
    when the next client attached within those 3s the loop's rebinding of
    alive/conn/pm resurrected it against the NEW session's socket. Two
    readers then raced the same serial port, interleaving chunks
    (transposed characters in the client's capture) and splitting RFC2217
    escape sequences badly enough to wedge the client's telnet parser into
    permanent silence. Reproduced deterministically on a live bench
    2026-07-18: a monitor session started <3s after the previous one
    always corrupted, >3s always clean.
    """
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
            logger=logging.getLogger("rfc2217") if verbosity > 0
            else None,
        )
    except (BrokenPipeError, OSError):
        logging.info("Client disconnected during negotiation")
        conn.close()
        return

    # Drop bytes that arrived between sessions — they belong to no client,
    # and a stale partial line would otherwise mangle this session's first
    # captured line.
    try:
        ser.reset_input_buffer()
    except Exception:
        pass

    alive = True

    def reader():
        nonlocal alive
        while alive:
            try:
                data = ser.read(ser.in_waiting or 1)
                if data:
                    conn.sendall(b"".join(pm.escape(data)))
            except Exception:
                break
        alive = False

    t = threading.Thread(target=reader, daemon=True)
    t.start()

    try:
        while alive:
            data = conn.recv(1024)
            if not data:
                break
            ser.write(b"".join(pm.filter(data)))
    except Exception:
        pass

    alive = False
    conn.close()
    # The reader wakes from its blocking ser.read() within the port's read
    # timeout, sees alive=False, and exits. Waiting for it here guarantees
    # exactly one reader ever touches the port, no matter how quickly the
    # next client attaches.
    t.join(timeout=1)
    logging.info("Client disconnected")
    ser.dtr = False
    ser.rts = False
    ser.apply_settings(settings)


if __name__ == "__main__":
    main()
