"""Connector base class. One small module per open source.

A connector knows three things:
  fetch(raw_dir, limit)   download raw files from the official location (never into git)
  convert(raw_dir, limit) yield unified Records from those raw files
  source                  the checked license and metadata from sources/<id>.yaml
"""

from __future__ import annotations

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


def load_source(source_id: str) -> Source:
    with open(SOURCES_DIR / f"{source_id}.yaml") as f:
        return Source.model_validate(yaml.safe_load(f))


def download(url: str, dest: Path, max_bytes: int | None = None, retries: int = 3) -> Path:
    """Stream a URL to dest. Stops after max_bytes (partial reads of big CSV files)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    for attempt in range(retries):
        try:
            with requests.get(url, headers=HEADERS, stream=True, timeout=60) as r:
                r.raise_for_status()
                n = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        f.write(chunk)
                        n += len(chunk)
                        if max_bytes and n >= max_bytes:
                            break
            return dest
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    return dest


class Connector:
    source_id: str = ""
    dataset_id: str = ""
    dataset_version: str = ""
    dataset_url: str = ""

    def __init__(self):
        self.source = load_source(self.source_id)

    def raw_dir(self) -> Path:
        return RAW_DIR / self.source_id

    def fetch(self, raw_dir: Path | None = None, limit: int | None = None) -> Path:
        raise NotImplementedError

    def convert(self, raw_dir: Path | None = None, limit: int | None = None) -> Iterator[Record]:
        raise NotImplementedError

    def files_sha256(self, raw_dir: Path | None = None) -> dict:
        d = Path(raw_dir or self.raw_dir())
        return {p.name: file_sha256(p) for p in sorted(d.glob("*")) if p.is_file()}
