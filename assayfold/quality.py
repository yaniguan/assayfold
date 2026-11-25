"""Quality checks: schema validation, unit normalization, dedup, license gate.

Failures are reported with record ids and reasons. Nothing is dropped silently.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from pydantic import ValidationError

from . import licenses, units
from .schema import Quantity, Record

try:  # optional
    from rdkit import Chem, RDLogger
    RDLogger.DisableLog("rdApp.*")
except ImportError:  # pragma: no cover
    Chem = None


@dataclass
class QualityReport:
    n_in: int = 0
    n_out: int = 0
    counts: Counter = field(default_factory=Counter)
    failures: list = field(default_factory=list)   # (record_id, check, reason)

    def fail(self, rid, check, reason):
        self.counts[check] += 1
        self.failures.append((rid, check, reason))

    def summary(self) -> dict:
        return {"n_in": self.n_in, "n_out": self.n_out, "failed_checks": dict(self.counts),
                "n_failures": len(self.failures)}


def smiles_ok(smiles: str) -> bool:
    """RDKit parse when available; otherwise a cheap bracket and charset check."""
    if not smiles:
        return False
    if Chem is not None:
        return Chem.MolFromSmiles(smiles) is not None
    if smiles.count("(") != smiles.count(")") or smiles.count("[") != smiles.count("]"):
        return False
    return all(ch.isalnum() or ch in "()[]=#@+-\\/%.:*$~" for ch in smiles)


def canonical_smiles(smiles: str):
    if Chem is None:
        return smiles
    m = Chem.MolFromSmiles(smiles)
    return Chem.MolToSmiles(m) if m is not None else None


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
        if not all(math.isfinite(v) for c in p.coords_angstrom for v in c):
            problems.append("non-finite coordinate")
    for q in _quantities(rec):
        if not units.is_known(q.unit):
            problems.append(f"unknown unit: {q.unit}")
        if q.value is not None and not math.isfinite(q.value):
            problems.append("non-finite value")
    if rec.record_hash and rec.record_hash != rec.content_hash():
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
    for q in _quantities(rec):
        code = units.to_code(q.unit, strict=False)
        if code != q.unit:
            q.raw_unit_str = q.raw_unit_str or q.unit
            q.unit = code
    return rec.sealed()


def dedup_key(rec: Record) -> str:
    """Molecules dedup by canonical SMILES within a source; others by content hash."""
    if rec.kind == "molecule":
        return f"{rec.source_id}|mol|{canonical_smiles(rec.payload.smiles)}"
    return rec.record_hash or rec.content_hash()


def run_all(records, purpose: str = "train_research"):
    """Check integrity, validate, normalize, gate and dedup. Returns (kept_records, QualityReport)."""
    report, kept, seen = QualityReport(), [], {}
    for raw in records:
        report.n_in += 1
        rid = raw.get("record_id") if isinstance(raw, dict) else raw.record_id
        try:
            # copy Records so normalize_units does not change the caller's objects
            rec = Record.model_validate(raw) if isinstance(raw, dict) else raw.model_copy(deep=True)
        except ValidationError as e:
            report.fail(rid, "schema", e.errors()[0]["msg"])
            continue
        # Integrity is checked on the record as loaded; normalize_units re-seals it below.
        if rec.record_hash and rec.record_hash != rec.content_hash():
            report.fail(rid, "record_hash mismatch", "record_hash mismatch: content changed after hashing")
            continue
        rec = normalize_units(rec)
        problems = validate(rec)
        for prob in problems:
            report.fail(rid, prob.split(":")[0], prob)
        if problems:
            continue
        ok, why = licenses.allowed(rec, purpose)
        if not ok:
            report.fail(rid, "license", f"{rec.source_id}: {why}")
            continue
        key = dedup_key(rec)
        if key in seen:
            report.fail(rid, "duplicate", f"same as {seen[key]}")
            continue
        seen[key] = rid
        kept.append(rec)
    report.n_out = len(kept)
    return kept, report
