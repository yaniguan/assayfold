"""Canonical JSON and sha256 helpers. Hashes depend on this exact format."""

import hashlib
import json
from pathlib import Path


def canonical_json(obj) -> bytes:
    """Sorted keys, no whitespace, UTF-8. Floats use Python's shortest repr."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(Path(path), "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()
