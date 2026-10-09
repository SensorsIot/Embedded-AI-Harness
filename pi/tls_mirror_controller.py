"""
TLS Mirror Controller — the firmware repository served over HTTPS with a
self-signed certificate (FR-038).

A test fixture: a DUT whose TLS client verifies certificates must refuse this
server; one that downloads from it has a broken or disabled check. Started and
stopped on demand by the portal, like the MQTT test broker.

The decision logic (whether to generate a certificate, how to map a request
path to a file) is in pure functions so the host tier can test it.
"""

import hashlib
import http.server
import logging
import os
import ssl
import subprocess
import threading

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TLS_PORT = 8443
TLS_DIR = os.environ.get("TLS_DIR", "/var/lib/rfc2217/tls")
CERT_FILE = "untrusted-cert.pem"
KEY_FILE = "untrusted-key.pem"
CERT_CN = "testbench-untrusted"
CERT_DAYS = 3650
CHUNK = 8192

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_httpd = None
_thread = None
_firmware_dir = None

# ---------------------------------------------------------------------------
# Pure core
# ---------------------------------------------------------------------------


def needs_new_cert(cert_exists: bool, key_exists: bool) -> bool:
    """Generate only when either half is missing; otherwise reuse, so the
    fingerprint a test recorded stays valid across restarts."""
    return not (cert_exists and key_exists)


def openssl_command(cert_path: str, key_path: str) -> list:
    """The openssl invocation that creates the self-signed pair."""
    return [
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-days", str(CERT_DAYS), "-subj", f"/CN={CERT_CN}",
        "-keyout", key_path, "-out", cert_path,
    ]


def resolve_firmware_path(firmware_dir: str, url_path: str):
    """Map `/firmware/<project>/<filename>` to a file under firmware_dir.

    Same rules as the HTTP repository (FR-021): exactly two segments after
    `/firmware/`, none empty, none `..`, none containing a separator. Returns
    the path, or None for anything else.
    """
    path = url_path.split("?", 1)[0]
    parts = path.split("/")
    if len(parts) != 4 or parts[0] != "" or parts[1] != "firmware":
        return None
    project, filename = parts[2], parts[3]
    for seg in (project, filename):
        if not seg or seg in (".", "..") or "\\" in seg or "\x00" in seg:
            return None
    return os.path.join(firmware_dir, project, filename)


def cert_fingerprint(pem_text: str) -> str:
    """SHA-256 fingerprint of a PEM certificate, colon-separated upper hex."""
    der = ssl.PEM_cert_to_DER_cert(pem_text)
    digest = hashlib.sha256(der).hexdigest().upper()
    return ":".join(digest[i:i + 2] for i in range(0, len(digest), 2))

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        fpath = resolve_firmware_path(_firmware_dir or "", self.path)
        if fpath is None or not os.path.isfile(fpath):
            self.send_error(404)
            return
        size = os.path.getsize(fpath)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(size))
        self.end_headers()
        with open(fpath, "rb") as f:
            while True:
                block = f.read(CHUNK)
                if not block:
                    break
                self.wfile.write(block)

    def log_message(self, fmt, *args):
        logger.info("tls-mirror %s - %s", self.address_string(), fmt % args)


class _Server(http.server.ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def handle_error(self, request, client_address):
        # A client that refuses the certificate hangs up mid-connection. That
        # is the outcome this fixture exists to produce, so it is one log line,
        # not a traceback.
        logger.info("tls-mirror: connection from %s ended early", client_address[0])


def _paths():
    return os.path.join(TLS_DIR, CERT_FILE), os.path.join(TLS_DIR, KEY_FILE)


def _ensure_cert():
    cert_path, key_path = _paths()
    if needs_new_cert(os.path.isfile(cert_path), os.path.isfile(key_path)):
        os.makedirs(TLS_DIR, exist_ok=True)
        subprocess.run(openssl_command(cert_path, key_path),
                       capture_output=True, timeout=60, check=True)
        os.chmod(key_path, 0o600)
        logger.info("tls-mirror: generated self-signed certificate in %s", TLS_DIR)
    return cert_path, key_path


def _fingerprint():
    cert_path, _ = _paths()
    with open(cert_path) as f:
        return cert_fingerprint(f.read())


def status() -> dict:
    with _lock:
        running = _httpd is not None
    out = {"running": running, "port": TLS_PORT}
    if running:
        out["sha256"] = _fingerprint()
    return out


def start(firmware_dir: str) -> dict:
    """Start the mirror (idempotent). Raises on certificate or bind failure."""
    global _httpd, _thread, _firmware_dir
    with _lock:
        if _httpd is None:
            cert_path, key_path = _ensure_cert()
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(cert_path, key_path)
            _firmware_dir = firmware_dir
            httpd = _Server(("0.0.0.0", TLS_PORT), _Handler)
            httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
            _thread = threading.Thread(target=httpd.serve_forever,
                                       name="tls-mirror", daemon=True)
            _thread.start()
            _httpd = httpd
            logger.info("tls-mirror: listening on %d", TLS_PORT)
    return status()


def stop() -> bool:
    """Stop the mirror (idempotent). Returns True when it was running."""
    global _httpd, _thread
    with _lock:
        httpd, _httpd = _httpd, None
        thread, _thread = _thread, None
    if httpd is None:
        return False
    httpd.shutdown()
    httpd.server_close()
    if thread is not None:
        thread.join(timeout=5)
    logger.info("tls-mirror: stopped")
    return True
