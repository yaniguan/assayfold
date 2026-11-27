"""protocols.io open-access protocol dump + BioProt + optional live token fetcher. CC-BY-4.0.

Without credentials, fetch() downloads open-access public protocols from the official
protocols.io GitHub mirror (protocolsio/protocols) and BioProt (bioplanner/bioplanner).
When PROTOCOLS_IO_ACCESS_TOKEN (or PROTOCOLS_IO_TOKEN) is set in the environment, fetch()
queries the live protocols.io v3/v4 API directly. Step parameters (volumes in uL/mL,
durations in s, temperatures in Cel) are normalized to UCUM Quantity objects.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import requests

from .. import units
from ..schema import Protocol, ProtocolStep, Provenance, Quantity, new_record
from .base import HEADERS, Connector, download

API = "https://www.protocols.io/api"
PIO_RAW = "https://raw.githubusercontent.com/protocolsio/protocols/master/protocols/{f}"
BIOPROT_RAW = "https://raw.githubusercontent.com/bioplanner/bioplanner/main/bioprot/{f}"

OPEN_FILES = [
    ("pio_72068.json", PIO_RAW.format(f="0-01m-phosphate-buffered-saline-1l-cimcuc2w.json")),
    ("pio_53314.json", PIO_RAW.format(f="0-05-m-glycine-bybapsie.json")),
    ("bioprot_10051.json", BIOPROT_RAW.format(f="10051.json")),
    ("bioprot_10157.json", BIOPROT_RAW.format(f="10157.json")),
    ("bioprot_1007.json", BIOPROT_RAW.format(f="1007.json")),
]

# protocols.io numeric unit IDs -> (UCUM code, raw_unit_str, param_prefix)
PIO_UNIT_IDS = {
    1: ("uL", "uL", "volume"),
    2: ("mL", "mL", "volume"),
    3: ("L", "L", "volume"),
    4: ("ug", "ug", "mass"),
    5: ("mg", "mg", "mass"),
    6: ("g", "g", "mass"),
    7: ("kg", "kg", "mass"),
    9: ("Hz", "Hz", "frequency"),
    10: ("Cel", "degC", "temperature"),
    11: ("K", "K", "temperature"),
    25: ("ms", "ms", "duration"),
    28: ("mmol/L", "mM", "concentration"),
    29: ("umol/L", "uM", "concentration"),
    30: ("nmol/L", "nM", "concentration"),
    33: ("{rpm}", "rpm", "speed"),
    34: ("{g-force}", "xg", "centrifugal_force"),
    203: ("nm", "nm", "wavelength"),
    204: ("g/L", "mg/mL", "concentration"),
    1324: ("{g-force}", "rcf", "centrifugal_force"),
}

INLINE_QUANT_RE = re.compile(
    r"(?<![A-Za-z0-9/])([-+]?\d+(?:\.\d+)?)\s*"
    r"(µL|μL|uL|µl|μl|ul|mL|ml|°C|degC|C\b|sec\b|seconds?\b|min\b|minutes?\b|h\b|hr\b|hours?\b|rpm\b)",
)


def _clean_text(text: str) -> str:
    text = (text or "").replace("\u03bc", "u").replace("\u00b5", "u")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f*_`#>\[\]]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_inline_params(text: str, existing: dict) -> dict[str, Quantity]:
    params = dict(existing)
    for m in INLINE_QUANT_RE.finditer(text):
        val = float(m.group(1))
        u_raw = m.group(2).strip()
        u_code = units.to_code(u_raw)
        if u_code in ("uL", "mL", "L"):
            key = "volume" if "volume" not in params else f"volume_{len(params) + 1}"
            params[key] = Quantity(value=val, unit=u_code, raw_unit_str=u_raw)
        elif u_code in ("Cel", "K") and "temperature" not in params:
            params["temperature"] = Quantity(value=val, unit=u_code, raw_unit_str=u_raw)
        elif u_code in ("s", "min", "h") and "duration" not in params:
            sec = round(units.convert(val, u_code, "s"), 2) if u_code != "s" else val
            params["duration"] = Quantity(value=sec, unit="s", raw_unit_str=u_raw)
        elif u_code == "{rpm}" and "speed" not in params:
            params["speed"] = Quantity(value=val, unit="{rpm}", raw_unit_str=u_raw)
    return params


def _parse_draftjs_step(raw_step) -> tuple[str, dict[str, Quantity], list[dict]]:
    """Render Draft.js JSON (blocks + entityMap) or plain markdown into clean text & UCUM params."""
    params: dict[str, Quantity] = {}
    entities: list[dict] = []
    if not raw_step:
        return "", params, entities
    if isinstance(raw_step, str) and raw_step.lstrip().startswith("{"):
        try:
            doc = json.loads(raw_step)
        except json.JSONDecodeError:
            doc = None
        if isinstance(doc, dict) and "blocks" in doc:
            emap = doc.get("entityMap") or {}
            rendered_blocks = []
            for blk in doc.get("blocks") or []:
                btxt = blk.get("text") or ""
                # Replace entity placeholders from right to left so offsets stay valid
                ranges = sorted(
                    blk.get("entityRanges") or [],
                    key=lambda r: int(r.get("offset", 0)),
                    reverse=True,
                )
                for rg in ranges:
                    ent = emap.get(str(rg.get("key"))) or {}
                    etype = ent.get("type") or ""
                    edata = ent.get("data") or {}
                    off = int(rg.get("offset", 0))
                    ln = int(rg.get("length", 0))
                    repl = None
                    if etype == "amount":
                        amt_s = str(edata.get("amount") or "").strip()
                        uid = edata.get("unit")
                        if amt_s and uid in PIO_UNIT_IDS:
                            try:
                                aval = float(amt_s)
                                u_code, u_raw, prefix = PIO_UNIT_IDS[uid]
                                k = prefix if prefix not in params else f"{prefix}_{len(params) + 1}"
                                params[k] = Quantity(value=aval, unit=u_code, raw_unit_str=u_raw)
                                repl = f"{amt_s} {u_raw}"
                            except ValueError:
                                pass
                    elif etype == "reagents":
                        rname = _clean_text(str(edata.get("name") or ""))
                        if rname:
                            repl = rname
                            entities.append({"type": "reagent", "text": rname})
                    elif etype in ("temperature", "duration"):
                        val_s = str(edata.get("temperature") or edata.get("duration") or "").strip()
                        uid = edata.get("unit")
                        if val_s and uid in PIO_UNIT_IDS:
                            try:
                                aval = float(val_s)
                                u_code, u_raw, prefix = PIO_UNIT_IDS[uid]
                                params[prefix] = Quantity(value=aval, unit=u_code, raw_unit_str=u_raw)
                                repl = f"{val_s} {u_raw}"
                            except ValueError:
                                pass
                    if repl is not None and 0 <= off <= len(btxt):
                        btxt = btxt[:off] + repl + btxt[off + ln :]
                if btxt.strip():
                    rendered_blocks.append(btxt.strip())
            text = _clean_text(" ".join(rendered_blocks))
            return text, _extract_inline_params(text, params), entities
    text = _clean_text(str(raw_step))
    return text, _extract_inline_params(text, params), entities


def _split_bioprot_steps(steps_text: str) -> list[str]:
    lines = [ln.strip() for ln in (steps_text or "").splitlines() if ln.strip()]
    out: list[str] = []
    for ln in lines:
        m = re.match(r"^(\d+)[\.\)]\s*(.+)$", ln)
        if m:
            out.append(_clean_text(m.group(2)))
        elif out:
            out[-1] = _clean_text(out[-1] + " " + ln)
        elif len(ln) > 12:
            out.append(_clean_text(ln))
    return [s for s in out if s]


def parse_protocol_bundle(source_id: str, dataset_id: str, license_id: str, data: dict):
    """Yield unified Protocol + ProtocolStep records from a protocols.io or BioProt JSON object."""
    if "protocol" in data and isinstance(data["protocol"], dict):
        proto = data["protocol"]
        raw_steps = data.get("steps") or proto.get("steps") or []
    else:
        proto = data
        raw_steps = data.get("steps") or []

    pid = str(proto.get("id") or proto.get("uri") or "unknown")
    title = _clean_text(str(proto.get("title") or f"Protocol {pid}"))
    url = (
        proto.get("protocols.io url")
        or (f"https://www.protocols.io/view/{proto['uri']}" if proto.get("uri") else None)
        or f"https://www.protocols.io/view/{pid}"
    )
    doi = str(proto.get("doi") or "").strip() or None
    tags = [f"doi:{doi}"] if doi else []

    parsed_steps = []
    if isinstance(raw_steps, str):
        tags.append("subset:bioprot")
        for idx, stext in enumerate(_split_bioprot_steps(raw_steps), start=1):
            params = _extract_inline_params(stext, {})
            parsed_steps.append((str(idx), idx, stext, params, []))
    elif isinstance(raw_steps, list):
        for idx, s in enumerate(raw_steps, start=1):
            stext, params, ents = _parse_draftjs_step(s.get("step"))
            dur = s.get("duration")
            if dur is not None:
                try:
                    dval = float(dur)
                    if dval > 0 and "duration" not in params:
                        params["duration"] = Quantity(value=dval, unit="s", raw_unit_str="s")
                except (TypeError, ValueError):
                    pass
            if stext:
                guid = str(s.get("guid") or s.get("id") or idx)
                parsed_steps.append((guid, idx, stext, params, ents))

    parent = new_record(
        source_id,
        dataset_id,
        pid,
        Protocol(title=title, n_steps=len(parsed_steps), url=url, domain="wet_lab"),
        license=license_id,
        origin="real",
        text=title,
        tags=tags,
        provenance=Provenance(source_url=url),
    )
    yield parent
    for guid, idx, stext, params, ents in parsed_steps:
        yield new_record(
            source_id,
            dataset_id,
            f"{pid}#{guid}",
            ProtocolStep(index=idx, text=stext, params=params, entities=ents),
            license=license_id,
            origin="real",
            parent_id=parent.record_id,
            text=stext,
            tags=list(tags),
            provenance=Provenance(source_url=url),
        )


def fetch_with_token(token: str, out_dir: Path, limit: int = 5, search_key: str = "PCR") -> Path:
    """Query the live protocols.io v3/v4 API using a Bearer access token."""
    out_dir.mkdir(parents=True, exist_ok=True)
    headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    r = requests.get(
        f"{API}/v3/protocols",
        headers=headers,
        timeout=60,
        params={"filter": "public", "key": search_key, "page_size": max(1, limit)},
    )
    r.raise_for_status()
    for proto in r.json().get("items", []):
        pid = proto["id"]
        sr = requests.get(
            f"{API}/v4/protocols/{pid}/steps",
            headers=headers,
            timeout=60,
            params={"content_format": "markdown"},
        )
        sr.raise_for_status()
        bundle = {"protocol": proto, "steps": sr.json().get("payload", [])}
        (out_dir / f"api_{pid}.json").write_text(json.dumps(bundle), encoding="utf-8")
    return out_dir


class ProtocolsIOOpen(Connector):
    source_id = "protocols_io_open"
    dataset_id = "protocols-io-open"
    dataset_version = "protocolsio/protocols master + BioProt main"
    dataset_url = "https://github.com/protocolsio/protocols"
    search_key = "PCR"

    def fetch(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        d.mkdir(parents=True, exist_ok=True)
        token = os.environ.get("PROTOCOLS_IO_ACCESS_TOKEN") or os.environ.get("PROTOCOLS_IO_TOKEN")
        if token:
            return fetch_with_token(token, d, limit=limit or 5, search_key=self.search_key)
        for fname, url in OPEN_FILES:
            download(url, d / fname)
        return d

    def is_partial(self, raw_dir=None):
        return True

    def convert(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        n = 0
        for f in sorted(d.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            for rec in parse_protocol_bundle(
                self.source_id, self.dataset_id, self.source.license, data
            ):
                if limit is not None and n >= limit:
                    return
                yield rec
                n += 1


CONNECTOR = ProtocolsIOOpen
