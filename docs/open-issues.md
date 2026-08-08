# Open issues

Decisions that are unresolved, and limitations that are known and not yet
fixed. A requirement belongs in the FSD; a question about what the requirement
should be belongs here until it is answered.

## OI-01 — Why does the RFC2217 proxy open non-exclusively?

`pi/plain_rfc2217_server.py` opens the device with `exclusive=False`, which
disables `TIOCEXCL` and permits a second process to open the same tty. Setting
it to `True` would make the kernel refuse a second opener outright, turning
FR-034's *detection* into *enforcement* for the serial side.

The setting is explicit, so it was chosen deliberately, and the reason is not
recorded. It is not being changed until the reason is established: a path may
depend on the non-exclusive open, and altering a setting whose purpose is
unknown is how a working bench acquires a silent fault.

**To resolve:** identify what, if anything, opens a slot's devnode while its
proxy is running. If nothing does, `exclusive=True` and FR-034 gains kernel
enforcement.

## OI-02 — A boot-time marker is unobservable on a native-USB part

`POST /api/serial/reset` has two paths. The DTR/RTS path stops the proxy, opens
the device directly and **captures the boot output** (FR-008). The JTAG path,
used automatically whenever a debug session is active and required for
native-USB parts where DTR/RTS mean download-mode and reset, sends `reset run`
over OpenOCD's telnet interface and returns OpenOCD's output. It resets through
a separate channel while nothing is draining the serial port, so the device's
start-up output is emitted into a port no consumer is reading.

The consequence is that no test can observe a marker printed once at start-up
on an ESP32-C3 — a firmware's "init complete" line, or an identifier logged at
boot. Projects must either make such markers periodic, which distorts the
firmware to suit the instrument, or leave the requirement unverified.

**To resolve:** give the JTAG path the capture the DTR/RTS path already has —
stop the proxy, open the device, issue the OpenOCD reset over its own channel,
read boot lines, restart the proxy. The two channels are independent, so this
composes. An alternative that solves it more broadly is to have the proxy
always drain the device into a timestamped ring buffer, in which case boot
output after *any* reset is available without either path capturing anything.

## OI-03 — The proxy serves one client at a time

`srv.listen(1)`: a slot's RFC2217 port accepts a single client. The portal's
own monitor and an external `idf.py` cannot coexist, and a client whose reader
thread dies holds the slot until the proxy is restarted.

FR-032's lease bounds the damage. It does not remove the limit.

**To resolve:** fan out reads. The proxy drains the device continuously and
copies received bytes to every connected client and to a ring buffer, while
write access stays exclusive to one client. Reading then costs nothing and
contends with nothing.

## OI-04 — The FSD carries no `shall` statements

Requirements in this document are feature specifications — endpoint, request,
procedure, response — rather than atomic obligations. Verification contracts
have been added to §3 (FR-001–FR-009, FR-031–FR-035), so what must be true is
now falsifiable there, but the requirement text itself is not atomic in the
sense the method's quality gate expects.

**To resolve:** decide whether this document adopts atomic `shall` requirements
throughout, or whether an API specification is a legitimate alternative form
for an instrument whose behaviour *is* its API. This is a question about the
method, not only about this file.
