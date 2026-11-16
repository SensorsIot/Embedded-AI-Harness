"""Host tier: multipart/form-data parsing of the upload endpoints
(/api/flash, /api/firmware/upload, /api/ota). Pure logic only.

Before this, each part went through bytes.strip(): a file ending in a
whitespace byte (0x09-0x0d, 0x20) arrived shorter than sent. ESP-IDF app
images end in their SHA-256, so about one in 40 was cut and then failed
its hash check on the device.
"""
import uuid

import pytest

import multipart

WHITESPACE_ENDINGS = [b"\n", b"\r\n", b" ", b"\t", b"\r", b"\x0b", b"\x0c", b"  \n\n"]


def encode(fields, files, boundary, eol=b"\r\n"):
    """Builds a body the way curl / requests / urllib clients do."""
    out = b""
    for name, value in fields.items():
        out += (b"--" + boundary.encode() + eol
                + f'Content-Disposition: form-data; name="{name}"'.encode() + eol + eol
                + value.encode() + eol)
    for name, filename, data in files:
        out += (b"--" + boundary.encode() + eol
                + f'Content-Disposition: form-data; name="{name}"; filename="{filename}"'.encode() + eol
                + b"Content-Type: application/octet-stream" + eol + eol
                + data + eol)
    return out + b"--" + boundary.encode() + b"--" + eol


def parts(body, boundary):
    return [(h.decode(), c) for h, c in multipart.split_parts(body, boundary)]


@pytest.mark.parametrize("ending", WHITESPACE_ENDINGS)
def test_file_content_keeps_trailing_whitespace(ending):
    data = bytes(range(256)) + ending
    b = uuid.uuid4().hex
    got = parts(encode({"project": "p"}, [("file", "fw.bin", data)], b), b)
    assert got[1][1] == data


@pytest.mark.parametrize("starting", [b"\n", b"\r\n", b" ", b"\r\n\r\n"])
def test_file_content_keeps_leading_whitespace(starting):
    data = starting + b"payload"
    b = uuid.uuid4().hex
    assert parts(encode({}, [("file", "f", data)], b), b)[0][1] == data


def test_fields_and_several_files_in_order():
    b = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = encode({"slot": "SLOT1", "chip": "esp32c6"},
                  [("bootloader.bin", "bootloader.bin", b"\x01\x02\n"), ("app.bin", "app.bin", b"\xff\x20")], b)
    got = parts(body, b)
    assert [c for _, c in got] == [b"SLOT1", b"esp32c6", b"\x01\x02\n", b"\xff\x20"]
    assert 'name="slot"' in got[0][0]
    assert 'filename="app.bin"' in got[3][0]


def test_empty_file():
    b = uuid.uuid4().hex
    assert parts(encode({}, [("file", "empty", b"")], b), b)[0][1] == b""


def test_bare_lf_line_breaks():
    b = uuid.uuid4().hex
    body = encode({"project": "p"}, [("file", "f", b"data \n")], b, eol=b"\n")
    assert [c for _, c in parts(body, b)] == [b"p", b"data \n"]


def test_preamble_and_epilogue_are_ignored():
    b = uuid.uuid4().hex
    body = b"preamble\r\n" + encode({"a": "1"}, [], b) + b"epilogue\r\n"
    assert [c for _, c in parts(body, b)] == [b"1"]


def test_part_without_header_separator_is_skipped():
    b = "xyz"
    body = b"--xyz\r\nno separator here\r\n--xyz\r\nContent-Disposition: form-data; name=\"a\"\r\n\r\nv\r\n--xyz--\r\n"
    assert [c for _, c in parts(body, b)] == [b"v"]
