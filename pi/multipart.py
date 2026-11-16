"""Split a multipart/form-data body into its parts, byte-exact.

The portal's upload endpoints (/api/flash, /api/firmware/upload, /api/ota,
_parse_multipart) used to call part.strip() on each raw part. That removed the
CRLF that belongs to the next delimiter, but also any whitespace bytes at the
end of the uploaded file (0x09-0x0d, 0x20). A binary ending in such a byte -
an ESP-IDF app image ends in its SHA-256, so roughly one in 40 does - lost
those bytes, failed its hash check and did not boot or OTA-update.

RFC 2046 section 5.1.1: the CRLF before "--boundary" belongs to the
delimiter, everything else is content. Only that CRLF (and the line break
after the delimiter line) is removed here.
"""


def split_parts(body: bytes, boundary: str):
    """Yields (header_section, content) as bytes for each part of 'body'.

    header_section is the raw header block (without the blank line), content
    is the part's payload exactly as sent. Parts without a header/body
    separator are skipped. Bare LF line breaks are accepted as well as CRLF.
    """
    delimiter = b"--" + boundary.encode()
    chunks = body.split(delimiter)
    for chunk in chunks[1:]:                     # chunks[0] is the preamble
        if chunk.startswith(b"--"):              # close delimiter "--boundary--"
            break
        # Rest of the delimiter line: optional transport padding, then CRLF.
        eol = chunk.find(b"\n")
        if eol < 0:
            continue
        chunk = chunk[eol + 1:]
        # The line break before the next delimiter is part of that delimiter.
        if chunk.endswith(b"\r\n"):
            chunk = chunk[:-2]
        elif chunk.endswith(b"\n"):
            chunk = chunk[:-1]
        if chunk.startswith(b"\r\n"):            # no headers at all
            yield b"", chunk[2:]
        elif b"\r\n\r\n" in chunk:
            yield tuple(chunk.split(b"\r\n\r\n", 1))
        elif b"\n\n" in chunk:
            yield tuple(chunk.split(b"\n\n", 1))
