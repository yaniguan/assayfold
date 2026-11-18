"""Read a few members of a large remote ZIP with HTTP range requests (no full download)."""

import io

import requests

from .connectors.base import HEADERS


class RangeFile(io.RawIOBase):
    """A read-only, seekable file over HTTP. zipfile only needs seek, tell and read."""

    def __init__(self, url: str):
        self.url, self.pos = url, 0
        r = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=60)
        r.raise_for_status()
        self.size = int(r.headers["content-length"])
        self.bytes_read = 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=io.SEEK_SET):
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.pos, io.SEEK_END: self.size}[whence]
        self.pos = max(0, base + offset)
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        end = min(self.size, self.pos + n) - 1
        h = {**HEADERS, "Range": f"bytes={self.pos}-{end}"}
        r = requests.get(self.url, headers=h, timeout=120)
        r.raise_for_status()
        data = r.content
        self.pos += len(data)
        self.bytes_read += len(data)
        return data
