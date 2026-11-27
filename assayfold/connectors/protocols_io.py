"""protocols.io public protocols via the official API (CC-BY for public content).

Needs a free client access token in the PROTOCOLS_IO_TOKEN environment variable
(create one in your protocols.io developer settings). Without a token, fetch() stops.
"""

import json
import os
import re
from pathlib import Path

import requests

from ..schema import Protocol, ProtocolStep, Provenance, new_record
from .base import HEADERS, Connector

API = "https://www.protocols.io/api"


def _headers():
    token = os.environ.get("PROTOCOLS_IO_TOKEN") or os.environ.get("PROTOCOLS_IO_ACCESS_TOKEN")
    if not token:
        raise RuntimeError(
            "set PROTOCOLS_IO_TOKEN or PROTOCOLS_IO_ACCESS_TOKEN (a protocols.io client access token)"
        )
    return {**HEADERS, "Authorization": f"Bearer {token}"}


def strip_markdown(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[*_`#>\[\]]", "", text or "")).strip()


def to_records(source_id, license, proto: dict, steps: list[dict]):
    """Map one API protocol object and its step list to unified records."""
    pid = str(proto["id"])
    url = f"https://www.protocols.io/view/{proto.get('uri', pid)}"
    parent = new_record(source_id, "protocols_io", pid,
                        Protocol(title=proto["title"], n_steps=len(steps), url=url),
                        license=license, origin="real", text=proto["title"],
                        tags=[f"doi:{proto['doi']}"] if proto.get("doi") else [],
                        provenance=Provenance(source_url=url))
    yield parent
    for i, s in enumerate(steps, start=1):
        text = strip_markdown(s.get("step", ""))
        yield new_record(source_id, "protocols_io", f"{pid}#{s.get('guid') or i}",
                         ProtocolStep(index=i, text=text), license=license, origin="real",
                         text=text, parent_id=parent.record_id, provenance=Provenance(source_url=url))


class ProtocolsIO(Connector):
    source_id = "protocols_io"
    dataset_id = "protocols_io"
    dataset_version = "API v3 list + v4 steps (retrieval date in meta)"
    dataset_url = "https://www.protocols.io"
    search_key = "PCR"

    def fetch(self, raw_dir=None, limit=10):
        d = Path(raw_dir or self.raw_dir())
        d.mkdir(parents=True, exist_ok=True)
        h = _headers()
        r = requests.get(f"{API}/v3/protocols", headers=h, timeout=60,
                         params={"filter": "public", "key": self.search_key, "page_size": limit or 10})
        r.raise_for_status()
        for proto in r.json().get("items", []):
            s = requests.get(f"{API}/v4/protocols/{proto['id']}/steps", headers=h, timeout=60,
                             params={"content_format": "markdown"})
            s.raise_for_status()
            (d / f"{proto['id']}.json").write_text(json.dumps({"protocol": proto, "steps": s.json().get("payload", [])}))
        return d

    def convert(self, raw_dir=None, limit=None):
        files = sorted(Path(raw_dir or self.raw_dir()).glob("*.json"))
        for f in files[:limit]:
            data = json.loads(f.read_text())
            yield from to_records(self.source_id, self.source.license, data["protocol"], data["steps"])


CONNECTOR = ProtocolsIO
