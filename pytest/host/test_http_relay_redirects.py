"""#85: POST /api/wifi/http can return a 3xx unfollowed (`follow_redirects: false`).

The relay's opener is fed by an in-memory HTTP handler, so no socket is opened.
"""
import email.message
import io
import urllib.request

import wifi_controller


class _FakeHTTP(urllib.request.BaseHandler):
    """Answers like a captive portal: any path but / -> 302 to http://192.168.4.1/."""

    handler_order = 100          # ahead of the real HTTPHandler

    def http_open(self, req):
        path = req.full_url.split("192.168.4.1", 1)[1] or "/"
        hdrs = email.message.Message()
        if path == "/":
            code, body = 200, b'<form><input name="wifi_ssid"></form>'
            hdrs["Content-Type"] = "text/html"
        else:
            code, body = 302, b""
            hdrs["Location"] = "http://192.168.4.1/"
        resp = urllib.request.addinfourl(io.BytesIO(body), hdrs, req.full_url, code)
        resp.msg = "OK" if code == 200 else "Found"
        resp.getheaders = lambda: list(hdrs.items())    # as http.client.HTTPResponse
        return resp


def _patch(monkeypatch):
    real = urllib.request.build_opener
    monkeypatch.setattr(wifi_controller.urllib.request, "build_opener",
                        lambda *h: real(_FakeHTTP, *h))
    monkeypatch.setattr(wifi_controller, "_check_wifi_testing_mode", lambda: None)


def test_default_follows_the_redirect(monkeypatch):
    _patch(monkeypatch)
    r = wifi_controller.http_relay("GET", "http://192.168.4.1/generate_204")
    assert r["status"] == 200


def test_follow_redirects_false_returns_the_302(monkeypatch):
    _patch(monkeypatch)
    r = wifi_controller.http_relay("GET", "http://192.168.4.1/generate_204",
                                   follow_redirects=False)
    assert r["status"] == 302
    assert r["headers"].get("Location") == "http://192.168.4.1/"


def test_follow_redirects_false_leaves_a_200_alone(monkeypatch):
    _patch(monkeypatch)
    r = wifi_controller.http_relay("GET", "http://192.168.4.1/", follow_redirects=False)
    assert r["status"] == 200
