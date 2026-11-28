"""Quality checks: schema validation, unit normalization, dedup, license gate.

Failures are reported with record ids and reasons. Nothing is dropped silently.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from pydantic import ValidationError

from . import licenses, units
from .canonical import canonical_json, sha256_hex
from .schema import ELEMENT_SET, Quantity, Record

try:  # optional
    from rdkit import Chem, RDLogger
    RDLogger.DisableLog("rdApp.*")
except ImportError:  # pragma: no cover
    Chem = None

DEDUP_SCOPES = ("source", "global")
_ATOM_MAP_RE = re.compile(r":\d+(?=\])")


@dataclass
class QualityReport:
    n_in: int = 0
    n_out: int = 0
    counts: Counter = field(default_factory=Counter)
    failures: list = field(default_factory=list)   # (record_id, check, reason)
    duplicates_by_source_pair: Counter = field(default_factory=Counter)

    def fail(self, rid, check, reason):
        self.counts[check] += 1
        self.failures.append((rid, check, reason))

    def summary(self) -> dict:
        out = {
            "n_in": self.n_in,
            "n_out": self.n_out,
            "failed_checks": dict(self.counts),
            "n_failures": len(self.failures),
        }
        if self.duplicates_by_source_pair:
            out["duplicates_by_source_pair"] = dict(self.duplicates_by_source_pair)
        return out


def smiles_ok(smiles: str) -> bool:
    """RDKit parse when available; otherwise a cheap bracket and charset check."""
    if not smiles:
        return False
    if Chem is not None:
        return Chem.MolFromSmiles(smiles) is not None
    if smiles.count("(") != smiles.count(")") or smiles.count("[") != smiles.count("]"):
        return False
    return all(ch.isalnum() or ch in "()[]=#@+-\\/%.:*$~" for ch in smiles)


def canonical_smiles(smiles: str, *, strip_atom_map: bool = False):
    clean = str(smiles).strip().split(" ")[0]
    if strip_atom_map:
        clean = _ATOM_MAP_RE.sub("", clean)
    if Chem is None:
        return clean
    m = Chem.MolFromSmiles(clean)
    if m is None:
        return None
    if strip_atom_map:
        for atom in m.GetAtoms():
            atom.SetAtomMapNum(0)
    return Chem.MolToSmiles(m)


def _smiles_key(smiles: str, *, strip_atom_map: bool = False) -> str:
    c = canonical_smiles(smiles, strip_atom_map=strip_atom_map)
    if c is not None:
        return c
    raw = str(smiles).strip().split(" ")[0]
    return _ATOM_MAP_RE.sub("", raw) if strip_atom_map else raw


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def _round_float(v: float, ndigits: int = 4) -> float:
    return round(float(v), ndigits) + 0.0


def _canon_quantity(q: Quantity) -> list:
    u = units.to_code(q.unit, strict=False)
    v = q.value
    if v is not None and math.isfinite(v):
        if u == "Cel":
            v, u = units.convert(v, "Cel", "K"), "K"
        elif u in ("ms", "us", "min", "h", "d"):
            v, u = units.convert(v, u, "s"), "s"
        v = _round_float(v, 4)
    return [v, u]


def _canon_quantity_map(qmap: dict[str, Quantity]) -> list:
    return [[k, *_canon_quantity(qmap[k])] for k in sorted(qmap)]


def _quantities(rec: Record):
    yield from rec.properties.values()
    p = rec.payload
    if p.kind == "observation":
        yield p.value
    if p.kind == "reaction":
        yield from p.conditions.values()
        if p.yield_percent:
            yield p.yield_percent
    if p.kind == "protocol_step":
        yield from (v for v in p.params.values() if isinstance(v, Quantity))


def validate(rec) -> list[str]:
    """Return a list of problems (empty means ok). Accepts a Record or a dict."""
    if isinstance(rec, dict):
        try:
            rec = Record.model_validate(rec)
        except ValidationError as e:
            return [f"schema: {e.errors()[0]['msg']}"]
    problems = []
    p = rec.payload
    for smi in _smiles_of(rec):
        if not smiles_ok(smi):
            problems.append(f"bad SMILES: {smi[:60]}")
    if p.kind == "structure":
        bad_els = [el for el in dict.fromkeys(p.elements) if el not in ELEMENT_SET]
        for el in bad_els:
            problems.append(f"unknown element: {el}")
        if not all(math.isfinite(v) for c in p.coords_angstrom for v in c):
            problems.append("non-finite coordinate")
        if p.forces is not None:
            if len(p.forces) != len(p.elements):
                problems.append("forces and elements differ in length")
            elif any(len(f) != 3 for f in p.forces):
                problems.append("each force vector needs 3 values")
            elif not all(math.isfinite(v) for f in p.forces for v in f):
                problems.append("non-finite force")
            if not p.forces_unit:
                problems.append("missing forces_unit")
            elif not units.is_known(p.forces_unit):
                problems.append(f"unknown unit: {p.forces_unit}")
        elif p.forces_unit is not None and not units.is_known(p.forces_unit):
            problems.append(f"unknown unit: {p.forces_unit}")
    if p.kind == "spectrum":
        if not units.is_known(p.x_unit):
            problems.append(f"unknown unit: {p.x_unit}")
        if not units.is_known(p.y_unit):
            problems.append(f"unknown unit: {p.y_unit}")
        if len(p.x) != len(p.y):
            problems.append("spectrum x and y differ in length")
        if not all(math.isfinite(v) for v in p.x) or not all(math.isfinite(v) for v in p.y):
            problems.append("non-finite spectrum value")
    for q in _quantities(rec):
        if not units.is_known(q.unit):
            problems.append(f"unknown unit: {q.unit}")
        if q.value is not None and not math.isfinite(q.value):
            problems.append("non-finite value")
    if rec.record_hash:
        try:
            ch = rec.content_hash()
        except ValueError:
            if not any(p.startswith("non-finite") for p in problems):
                problems.append("non-finite value")
        else:
            if rec.record_hash != ch:
                problems.append("record_hash mismatch")
    return problems


def _smiles_of(rec: Record):
    p = rec.payload
    if p.kind == "molecule":
        yield p.smiles
    elif p.kind == "reaction":
        yield from (s for s in p.reactants + p.products if s)
    elif p.kind == "structure" and p.smiles:
        yield p.smiles


def normalize_units(rec: Record) -> Record:
    """Map raw unit strings to canonical codes in place (lenient: unknown stays as is)."""
    if rec.payload.kind == "spectrum":
        rec.payload.x_unit = units.to_code(rec.payload.x_unit, strict=False)
        rec.payload.y_unit = units.to_code(rec.payload.y_unit, strict=False)
    elif rec.payload.kind == "structure" and rec.payload.forces_unit is not None:
        rec.payload.forces_unit = units.to_code(rec.payload.forces_unit, strict=False)
    for q in _quantities(rec):
        code = units.to_code(q.unit, strict=False)
        if code != q.unit:
            q.raw_unit_str = q.raw_unit_str or q.unit
            q.unit = code
    try:
        return rec.sealed()
    except ValueError:
        return rec


def content_key(rec: Record) -> str:
    """Content-level identity per kind, independent of record_id, native_id, and provenance."""
    p = rec.payload
    if p.kind == "molecule":
        return f"mol|{_smiles_key(p.smiles)}"
    if p.kind == "reaction":
        reac = ".".join(sorted(_smiles_key(s, strip_atom_map=True) for s in p.reactants if s))
        ag = ".".join(sorted(_smiles_key(s, strip_atom_map=True) for s in p.agents if s))
        prod = ".".join(sorted(_smiles_key(s, strip_atom_map=True) for s in p.products if s))
        key = f"rxn|{reac}>{ag}>{prod}"
        if p.conditions:
            key += "|cond:" + sha256_hex(canonical_json(_canon_quantity_map(p.conditions)))[:16]
        if rec.properties:
            key += "|prop:" + sha256_hex(canonical_json(_canon_quantity_map(rec.properties)))[:16]
        return key
    if p.kind == "spectrum":
        ux = units.to_code(p.x_unit, strict=False)
        uy = units.to_code(p.y_unit, strict=False)
        xs = [_round_float(v, 4) for v in p.x]
        ys = [_round_float(v, 4) for v in p.y]
        xy_hash = sha256_hex(canonical_json([xs, ys]))
        return f"spectrum|{_norm_text(p.technique)}|{ux}|{uy}|{xy_hash}"
    if p.kind == "structure":
        coords = [[_round_float(v, 4) for v in c] for c in p.coords_angstrom]
        geom_hash = sha256_hex(canonical_json([p.elements, coords]))
        return f"structure|{geom_hash}"
    if p.kind == "qa_item":
        choices = sorted(_norm_text(c) for c in p.choices)
        qa_hash = sha256_hex(canonical_json([_norm_text(p.question), choices]))
        return f"qa_item|{qa_hash}"
    if p.kind == "protocol_step":
        if rec.parent_id is not None:
            return f"protocol_step|{p.index}|{_norm_text(p.text)}"
        return f"protocol_step|{_norm_text(p.text)}"
    if p.kind == "protocol":
        return f"protocol|{_norm_text(p.title)}|{p.n_steps}"
    if p.kind == "experiment":
        return f"experiment|{_norm_text(p.title)}|{_norm_text(p.description or '')}"
    if p.kind == "observation":
        obs_hash = sha256_hex(
            canonical_json(
                [
                    _norm_text(p.property),
                    _canon_quantity(p.value),
                    _norm_text(p.method or ""),
                    _canon_quantity_map(rec.properties),
                    _norm_text(rec.text or ""),
                    sorted(rec.tags),
                ]
            )
        )
        return f"observation|{obs_hash}"
    if p.kind == "image":
        return f"image|{p.blob.sha256}"
    if p.kind == "trajectory":
        blob_sha = p.frames_blob.sha256 if p.frames_blob is not None else ""
        return f"trajectory|{blob_sha}|{p.n_frames}|{_norm_text(p.method or '')}"
    return rec.content_hash()


def dedup_key(rec: Record, scope: str = "source") -> str:
    """Per-kind content dedup key, scoped to `source` (default) or `global` across sources."""
    if scope not in DEDUP_SCOPES:
        raise ValueError(f"unknown dedup scope {scope!r}; use one of {DEDUP_SCOPES}")
    ckey = content_key(rec)
    return f"{rec.source_id}|{ckey}" if scope == "source" else ckey


def run_all(
    records,
    purpose: str = "train_research",
    scope: str = "source",
    *,
    allow_eval_in_rag: bool = False,
    allow_unsealed: bool = False,
):
    """Check sealing/integrity, validate, normalize, gate, and dedup.

    In `global` scope, valid records are ordered deterministically by
    `(source_id, dataset_id, native_id, record_id)` before deduplication so the kept
    record is independent of input file ordering, and cross-source duplicates are counted
    in `report.duplicates_by_source_pair`.
    """
    if scope not in DEDUP_SCOPES:
        raise ValueError(f"unknown dedup scope {scope!r}; use one of {DEDUP_SCOPES}")
    report, candidates = QualityReport(), []
    for raw in records:
        report.n_in += 1
        rid = raw.get("record_id") if isinstance(raw, dict) else raw.record_id
        try:
            # copy Records so normalize_units does not change the caller's objects
            rec = Record.model_validate(raw) if isinstance(raw, dict) else raw.model_copy(deep=True)
        except ValidationError as e:
            report.fail(rid, "schema", e.errors()[0]["msg"])
            continue
        if not rec.record_hash:
            if not allow_unsealed:
                report.fail(rid, "unsealed", "unsealed: missing record_hash")
                continue
        else:
            try:
                expected_hash = rec.content_hash()
            except ValueError:
                expected_hash = None
            if expected_hash is not None and rec.record_hash != expected_hash:
                report.fail(rid, "record_hash mismatch", "record_hash mismatch: content changed after hashing")
                continue
        rec = normalize_units(rec)
        problems = validate(rec)
        for prob in problems:
            report.fail(rid, prob.split(":")[0], prob)
        if problems:
            continue
        ok, why = licenses.allowed(rec, purpose, allow_eval_in_rag=allow_eval_in_rag)
        if not ok:
            report.fail(rid, "license", f"{rec.source_id}: {why}")
            continue
        candidates.append(rec)

    if scope == "global":
        candidates.sort(key=lambda r: (r.source_id, r.dataset_id, r.native_id, r.record_id))

    kept, seen = [], {}
    for rec in candidates:
        key = dedup_key(rec, scope=scope)
        if key in seen:
            first_rec = seen[key]
            report.fail(rec.record_id, "duplicate", f"same as {first_rec.record_id}")
            if scope == "global" and rec.source_id != first_rec.source_id:
                pair = "|".join(sorted((first_rec.source_id, rec.source_id)))
                report.duplicates_by_source_pair[pair] += 1
            continue
        seen[key] = rec
        kept.append(rec)

    report.n_out = len(kept)
    return kept, report
