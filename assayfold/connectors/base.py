"""Connector base class. One small module per open source.

A connector knows three things:
  fetch(raw_dir, limit)   download raw files from the official location (never into git)
  convert(raw_dir, limit) yield unified Records from those raw files
  source                  the checked license and metadata from sources/<id>.yaml
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Iterator

import requests
import yaml

from ..canonical import file_sha256
from ..schema import Record, Source

ROOT = Path(__file__).resolve().parents[2]
SOURCES_DIR = ROOT / "sources"
RAW_DIR = ROOT / "data" / "raw"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; assayfold/0.1; open data converter)"}


class IncompleteDownload(IOError):
    """Fewer bytes arrived than the server announced."""


def load_source(source_id: str) -> Source:
    with open(SOURCES_DIR / f"{source_id}.yaml") as f:
        return Source.model_validate(yaml.safe_load(f))


def partial_path(dest: Path, max_bytes: int) -> Path:
    """Where a head-only read of dest is stored, e.g. data.head2000000.csv.
    Never the real filename, so a later full fetch is not mistaken for done."""
    return dest.with_name(f"{dest.stem}.head{max_bytes}{dest.suffix}")


def download(url: str, dest: Path, max_bytes: int | None = None, retries: int = 3,
             sha256: str | None = None) -> Path:
    """Stream a URL to dest and return the path written.

    Bytes go to dest.with_suffix(".part") first and are renamed only after a complete,
    checked read, so an interrupted download never looks finished. A full read is checked
    against Content-Length (when the body is not content-encoded) and against `sha256`
    when one is pinned. With max_bytes only the first max_bytes are kept, stored under
    partial_path(dest, max_bytes) instead of dest.
    """
    if max_bytes:
        dest = partial_path(dest, max_bytes)
        sha256 = None
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        if sha256 and file_sha256(dest) != sha256:
            raise ValueError(f"{dest} is cached but its sha256 is not the pinned {sha256}; delete it")
        return dest
    part = dest.with_suffix(".part")
    for attempt in range(retries):
        try:
            with requests.get(url, headers=HEADERS, stream=True, timeout=60) as r:
                r.raise_for_status()
                n, h = 0, hashlib.sha256()
                with open(part, "wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        if max_bytes:
                            chunk = chunk[: max_bytes - n]
                        f.write(chunk)
                        h.update(chunk)
                        n += len(chunk)
                        if max_bytes and n >= max_bytes:
                            break
                length = r.headers.get("Content-Length")
                encoded = r.headers.get("Content-Encoding", "identity") != "identity"
                if not max_bytes and length and not encoded and n != int(length):
                    raise IncompleteDownload(f"{url}: got {n} bytes, Content-Length is {length}")
            if sha256 and h.hexdigest() != sha256:
                raise ValueError(f"{url}: sha256 {h.hexdigest()} is not the pinned {sha256}")
            part.replace(dest)
            return dest
        except (requests.RequestException, IncompleteDownload):
            part.unlink(missing_ok=True)
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
        except BaseException:
            part.unlink(missing_ok=True)
            raise
    return dest


class Connector:
    source_id: str = ""
    dataset_id: str = ""
    dataset_version: str = ""
    dataset_url: str = ""
    skipped_rows: int = 0     # rows convert() skipped; set by converters that may skip

    def __init__(self):
        self.source = load_source(self.source_id)

    def raw_dir(self) -> Path:
        return RAW_DIR / self.source_id

    def fetch(self, raw_dir: Path | None = None, limit: int | None = None) -> Path:
        raise NotImplementedError

    def convert(self, raw_dir: Path | None = None, limit: int | None = None) -> Iterator[Record]:
        raise NotImplementedError

    def raw_files(self, raw_dir: Path | None = None) -> list[Path]:
        """Files convert() reads. Default: every file under raw_dir, except unfinished .part files."""
        d = Path(raw_dir or self.raw_dir())
        return sorted(p for p in d.rglob("*") if p.is_file() and p.suffix != ".part")

    def is_partial(self, raw_dir: Path | None = None) -> bool:
        """True when convert() reads a head or a page of the source, not the published file."""
        return False

    def files_sha256(self, raw_dir: Path | None = None) -> dict:
        """Relative path -> sha256 of the files convert() reads (see raw_files)."""
        d = Path(raw_dir or self.raw_dir())
        return {p.relative_to(d).as_posix(): file_sha256(p) for p in self.raw_files(d) if p.is_file()}
