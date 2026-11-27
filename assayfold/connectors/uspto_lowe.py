"""USPTO patent chemical reactions (D. M. Lowe / Syntheseus USPTO-50K). CC0-1.0.

Reads stoichiometric US patent reactions (reactants, agents, products, yields in %,
temperatures in Cel/K, and durations normalized to s) from the Lowe 1976 USPTO patent
grants Parquet shard (without requiring ord-schema via a lightweight pure-Python wire
decoder), as well as Syntheseus / USPTO-50K atom-mapped Parquet and Lowe CML/RSMI files.
"""

from __future__ import annotations

import csv
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from .. import units
from ..quality import smiles_ok
from ..schema import Provenance, Quantity, Reaction, new_record
from .base import Connector, download

ORD_USPTO_1976_URL = (
    "https://huggingface.co/datasets/open-reaction-database/ord-data/resolve/main/"
    "data/ca/ord_dataset-ca811a23e9d44f4f0a65d6456701856e.parquet"
)
USPTO_50K_VAL_URL = (
    "https://huggingface.co/datasets/pingzhili/uspto-50k/resolve/main/"
    "data/validation-00000-of-00001.parquet"
)
ATOM_MAP_RE = re.compile(r":\d+(?=\])")

TEMP_ENUM = {1: ("Cel", "CELSIUS"), 3: ("K", "KELVIN")}
TIME_ENUM = {
    1: ("h", "HOUR"),
    2: ("min", "MINUTE"),
    3: ("s", "SECOND"),
    4: ("d", "DAY"),
}


def strip_atom_mapping(smiles: str) -> str:
    """Remove atom-mapping indices such as [CH3:8] -> [CH3] while keeping charge/H-counts."""
    clean = ATOM_MAP_RE.sub("", smiles.strip().split(" ")[0])
    # Simplify trivial bracketed neutral organic atoms like [c:1] -> c when uncharged
    clean = re.sub(r"\[([cnosCBNOFPSI])\]", r"\1", clean)
    return clean


def _read_varint(buf: bytes, pos: int) -> tuple[int, int]:
    res, shift = 0, 0
    while True:
        b = buf[pos]
        pos += 1
        res |= (b & 0x7F) << shift
        if not (b & 0x80):
            return res, pos
        shift += 7


def _iter_pb_fields(buf: bytes):
    """Yield (field_number, wire_type, value) from a protobuf message buffer."""
    pos, n = 0, len(buf)
    while pos < n:
        tag, pos = _read_varint(buf, pos)
        fn, wt = tag >> 3, tag & 7
        if wt == 0:
            val, pos = _read_varint(buf, pos)
            yield fn, wt, val
        elif wt == 1:
            val = struct.unpack("<d", buf[pos : pos + 8])[0]
            pos += 8
            yield fn, wt, val
        elif wt == 2:
            ln, pos = _read_varint(buf, pos)
            yield fn, wt, buf[pos : pos + ln]
            pos += ln
        elif wt == 5:
            val = struct.unpack("<f", buf[pos : pos + 4])[0]
            pos += 4
            yield fn, wt, val
        else:
            break


def _parse_identifier_smiles(buf: bytes) -> str | None:
    id_type, val = 0, None
    for fn, wt, v in _iter_pb_fields(buf):
        if fn == 1 and wt == 0:
            id_type = v
        elif fn == 3 and wt == 2:
            val = v.decode("utf-8", "ignore").strip()
    return val if id_type == 2 and val else None


def _parse_compound(buf: bytes) -> tuple[str | None, int]:
    smiles, role = None, 0
    for fn, wt, v in _iter_pb_fields(buf):
        if fn == 1 and wt == 2 and smiles is None:
            smiles = _parse_identifier_smiles(v)
        elif fn == 3 and wt == 0:
            role = v
    return smiles, role


def _parse_scalar_unit(buf: bytes) -> tuple[float | None, int]:
    val, unit_enum = None, 0
    for fn, wt, v in _iter_pb_fields(buf):
        if fn == 1 and wt == 5:
            val = round(float(v), 4)
        elif fn == 3 and wt == 0:
            unit_enum = v
    return val, unit_enum


def decode_ord_reaction_pb(blob: bytes) -> dict:
    """Decode an ord_schema.Reaction protobuf into plain Python fields without ord-schema."""
    reactants, agents, products = [], [], []
    temp_q, time_q, yield_q = None, None, None
    patent, procedure = None, None

    for fn, wt, v in _iter_pb_fields(blob):
        if fn == 2 and wt == 2:  # Reaction.inputs map entry (2 -> ReactionInput)
            for mfn, mwt, mv in _iter_pb_fields(v):
                if mfn == 2 and mwt == 2:
                    for ifn, iwt, iv in _iter_pb_fields(mv):
                        if ifn == 1 and iwt == 2:
                            smi, role = _parse_compound(iv)
                            if smi:
                                smi = strip_atom_mapping(smi)
                                if role == 1:
                                    reactants.append(smi)
                                elif role in (2, 3, 4):
                                    agents.append(smi)
        elif fn == 4 and wt == 2:  # ReactionConditions
            for cfn, cwt, cv in _iter_pb_fields(v):
                if cfn == 1 and cwt == 2:  # TemperatureConditions
                    for tfn, twt, tv in _iter_pb_fields(cv):
                        if tfn == 2 and twt == 2:  # setpoint
                            tval, tenum = _parse_scalar_unit(tv)
                            if tval is not None and tenum in TEMP_ENUM:
                                u_code, u_raw = TEMP_ENUM[tenum]
                                temp_q = Quantity(value=tval, unit=u_code, raw_unit_str=u_raw)
        elif fn == 5 and wt == 2:  # ReactionNotes
            for nfn, nwt, nv in _iter_pb_fields(v):
                if nfn == 9 and nwt == 2:
                    procedure = nv.decode("utf-8", "ignore").strip() or None
        elif fn == 8 and wt == 2:  # ReactionOutcome
            for ofn, owt, ov in _iter_pb_fields(v):
                if ofn == 1 and owt == 2 and time_q is None:  # reaction_time
                    rval, renum = _parse_scalar_unit(ov)
                    if rval is not None and renum in TIME_ENUM:
                        u_code, u_raw = TIME_ENUM[renum]
                        if u_code == "d":
                            sec_val = round(rval * 86400.0, 2)
                        else:
                            sec_val = round(units.convert(rval, u_code, "s"), 2)
                        time_q = Quantity(value=sec_val, unit="s", raw_unit_str=u_raw)
                elif ofn == 3 and owt == 2:  # ProductCompound
                    psmi = None
                    for pfn, pwt, pv in _iter_pb_fields(ov):
                        if pfn == 1 and pwt == 2 and psmi is None:
                            psmi = _parse_identifier_smiles(pv)
                        elif pfn == 3 and pwt == 2 and yield_q is None:  # ProductMeasurement
                            mtype, pct_val = 0, None
                            for mfn, mwt, mv in _iter_pb_fields(pv):
                                if mfn == 2 and mwt == 0:
                                    mtype = mv
                                elif mfn == 8 and mwt == 2:
                                    for pct_fn, pct_wt, pct_v in _iter_pb_fields(mv):
                                        if pct_fn == 1 and pct_wt == 5:
                                            pct_val = round(float(pct_v), 2)
                            if mtype == 3 and pct_val is not None and 0.0 <= pct_val <= 100.0:
                                yield_q = Quantity(value=pct_val, unit="%", raw_unit_str="%")
                    if psmi:
                        products.append(strip_atom_mapping(psmi))
        elif fn == 9 and wt == 2:  # ReactionProvenance
            for pfn, pwt, pv in _iter_pb_fields(v):
                if pfn == 5 and pwt == 2:
                    patent = pv.decode("utf-8", "ignore").strip() or None

    agents = list(dict.fromkeys(agents))
    return {
        "reactants": reactants,
        "agents": agents,
        "products": products,
        "temperature": temp_q,
        "reaction_time": time_q,
        "yield_percent": yield_q,
        "patent": patent,
        "procedure": procedure,
    }


def parse_cml_reactions(xml_path: Path):
    """Yield reaction dicts from a Lowe USPTO CML XML file."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    for idx, rxn_el in enumerate(root.iter()):
        if not rxn_el.tag.endswith("reaction"):
            continue
        reactants, agents, products = [], [], []
        yield_q, temp_q, time_q = None, None, None
        patent = None
        for child in rxn_el.iter():
            tag = child.tag.split("}")[-1]
            if tag == "identifier" and "smiles" in (child.attrib.get("dictRef") or "").lower():
                # Handled under parent role lists below
                pass
            elif tag == "documentId":
                patent = (child.text or "").strip() or patent
            elif tag == "amount" and "percentyield" in (child.attrib.get("units") or "").lower():
                try:
                    yield_q = Quantity(value=float(child.text), unit="%", raw_unit_str="%")
                except (TypeError, ValueError):
                    pass
            elif tag == "parameter":
                dref = (child.attrib.get("dictRef") or "").lower()
                for sc in child:
                    if sc.tag.split("}")[-1] == "scalar" and sc.text:
                        u_raw = (sc.attrib.get("units") or "").split(":")[-1]
                        try:
                            val = float(sc.text)
                        except ValueError:
                            continue
                        if "temp" in dref:
                            u_code = "K" if u_raw.lower().startswith("k") else "Cel"
                            temp_q = Quantity(value=val, unit=u_code, raw_unit_str=u_raw or u_code)
                        elif "time" in dref:
                            u_code = units.to_code(u_raw or "s", strict=False)
                            if u_code in ("s", "min", "h"):
                                sec = round(units.convert(val, u_code, "s"), 2)
                                time_q = Quantity(value=sec, unit="s", raw_unit_str=u_raw or "s")
        for role_tag, bucket in (
            ("reactantList", reactants),
            ("spectatorList", agents),
            ("productList", products),
        ):
            for lst in rxn_el.iter():
                if lst.tag.split("}")[-1] == role_tag:
                    for ident in lst.iter():
                        if ident.tag.split("}")[-1] == "identifier" and "smiles" in (
                            ident.attrib.get("dictRef") or ""
                        ).lower():
                            if ident.text and ident.text.strip():
                                bucket.append(strip_atom_mapping(ident.text.strip()))
        if reactants and products:
            yield {
                "native_id": f"{patent or xml_path.stem}#{idx}",
                "reactants": reactants,
                "agents": list(dict.fromkeys(agents)),
                "products": products,
                "temperature": temp_q,
                "reaction_time": time_q,
                "yield_percent": yield_q,
                "patent": patent,
            }


class USPTOLowe(Connector):
    source_id = "uspto_lowe"
    dataset_id = "uspto-lowe-patents"
    dataset_version = "Lowe USPTO 1976-2016 (doi:10.6084/m9.figshare.5104873.v1)"
    dataset_url = "https://doi.org/10.6084/m9.figshare.5104873.v1"

    def fetch(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        download(ORD_USPTO_1976_URL, d / "uspto_grants_1976.parquet")
        return d

    def is_partial(self, raw_dir=None):
        return True

    def _build_record(self, native_id: str, info: dict, extra_tags: list[str] | None = None):
        reac = [s for s in info["reactants"] if smiles_ok(s)]
        prod = [s for s in info["products"] if smiles_ok(s)]
        agents = [s for s in info.get("agents", []) if smiles_ok(s)]
        if not reac or not prod:
            return None
        cond = {}
        if info.get("temperature") is not None:
            cond["temperature"] = info["temperature"]
        if info.get("reaction_time") is not None:
            cond["reaction_time"] = info["reaction_time"]
        rsmi = f"{'.'.join(reac)}>{'.'.join(agents)}>{'.'.join(prod)}"
        patent = info.get("patent")
        tags = list(extra_tags or [])
        if patent:
            tags.append(f"patent:{patent}")
        text = (
            info.get("procedure")
            or (f"USPTO patent reaction ({patent})" if patent else f"USPTO reaction {native_id}")
        )
        if len(text) > 280:
            text = text[:277].rstrip() + "..."
        return new_record(
            self.source_id,
            self.dataset_id,
            native_id,
            Reaction(
                reactants=reac,
                products=prod,
                agents=agents,
                reaction_smiles=rsmi,
                conditions=cond,
                yield_percent=info.get("yield_percent"),
            ),
            license=self.source.license,
            origin="real",
            text=text,
            tags=tags,
            provenance=Provenance(source_url=self.dataset_url),
        )

    def convert(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        n = 0

        # 1. Lowe USPTO patent grants Parquet shard (with stoichiometric SMILES, %, Cel/K, s)
        pq_path = d / "uspto_grants_1976.parquet"
        if pq_path.exists():
            table = pq.read_table(pq_path)
            rids = table.column("reaction_id").to_pylist()
            blobs = table.column("reaction").to_pylist()
            for rid, blob in zip(rids, blobs):
                if limit is not None and n >= limit:
                    return
                info = decode_ord_reaction_pb(blob)
                # When sampling with a limit, prioritize complete condition+yield records
                if limit is not None and (
                    info["yield_percent"] is None
                    or info["temperature"] is None
                    or info["reaction_time"] is None
                ):
                    continue
                rec = self._build_record(rid, info)
                if rec is not None:
                    yield rec
                    n += 1

        # 2. Syntheseus / USPTO-50K flat Parquet files (rxn_smiles, class, id)
        for p50 in sorted(d.glob("*50k*.parquet")):
            for idx, row in pd.read_parquet(p50).iterrows():
                if limit is not None and n >= limit:
                    return
                raw_rxn = str(row.get("rxn_smiles") or row.get("ReactionSmiles") or "")
                reac_s, agent_s, prod_s = (raw_rxn.split(">") + ["", ""])[:3]
                info = {
                    "reactants": [strip_atom_mapping(s) for s in reac_s.split(".") if s],
                    "agents": [strip_atom_mapping(s) for s in agent_s.split(".") if s],
                    "products": [strip_atom_mapping(s) for s in prod_s.split(".") if s],
                    "patent": str(row.get("id") or "").strip() or None,
                    "temperature": None,
                    "reaction_time": None,
                    "yield_percent": None,
                }
                if row.get("temperature_K") is not None and pd.notna(row.get("temperature_K")):
                    info["temperature"] = Quantity(
                        value=float(row["temperature_K"]), unit="K", raw_unit_str="K"
                    )
                if row.get("duration_s") is not None and pd.notna(row.get("duration_s")):
                    info["reaction_time"] = Quantity(
                        value=float(row["duration_s"]), unit="s", raw_unit_str="s"
                    )
                if row.get("yield") is not None and pd.notna(row.get("yield")):
                    info["yield_percent"] = Quantity(
                        value=float(row["yield"]), unit="%", raw_unit_str="%"
                    )
                tags = []
                if row.get("class") is not None and pd.notna(row.get("class")):
                    tags.append(f"rxn_class:{int(row['class'])}")
                rec = self._build_record(f"{row.get('id', 'u50k')}#{idx}", info, tags)
                if rec is not None:
                    yield rec
                    n += 1

        # 3. Lowe CML XML files
        for xml_p in sorted(d.glob("*.xml")) + sorted(d.glob("*.cml")):
            for info in parse_cml_reactions(xml_p):
                if limit is not None and n >= limit:
                    return
                rec = self._build_record(info["native_id"], info)
                if rec is not None:
                    yield rec
                    n += 1

        # 4. Tab-separated RSMI files
        for rsmi_p in sorted(d.glob("*.rsmi")) + sorted(d.glob("*.tsv")):
            with open(rsmi_p, newline="", encoding="utf-8") as f:
                for idx, row in enumerate(csv.DictReader(f, delimiter="\t")):
                    if limit is not None and n >= limit:
                        return
                    rsmi = (row.get("ReactionSmiles") or "").split(" ")[0]
                    reac_s, agent_s, prod_s = (rsmi.split(">") + ["", ""])[:3]
                    yld = None
                    raw_y = (row.get("TextMinedYield") or row.get("CalculatedYield") or "").strip().rstrip("%")
                    if raw_y:
                        try:
                            yld = Quantity(value=float(raw_y), unit="%", raw_unit_str="%")
                        except ValueError:
                            pass
                    temp_q = None
                    if row.get("Temperature"):
                        v, u_code, u_raw = units.parse_quantity(row["Temperature"])
                        temp_q = Quantity(value=v, unit=u_code, raw_unit_str=u_raw)
                    time_q = None
                    if row.get("Duration"):
                        v, u_code, u_raw = units.parse_quantity(row["Duration"])
                        sec = round(units.convert(v, u_code, "s"), 2) if u_code != "s" else v
                        time_q = Quantity(value=sec, unit="s", raw_unit_str=u_raw)
                    patent = (row.get("PatentNumber") or "").strip() or None
                    info = {
                        "reactants": [strip_atom_mapping(s) for s in reac_s.split(".") if s],
                        "agents": [strip_atom_mapping(s) for s in agent_s.split(".") if s],
                        "products": [strip_atom_mapping(s) for s in prod_s.split(".") if s],
                        "temperature": temp_q,
                        "reaction_time": time_q,
                        "yield_percent": yld,
                        "patent": patent,
                    }
                    rec = self._build_record(f"{patent or 'rsmi'}#{idx}", info)
                    if rec is not None:
                        yield rec
                        n += 1


CONNECTOR = USPTOLowe
