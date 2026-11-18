"""Export unified records for training (JSONL, Parquet) and retrieval (RAG chunks).

Every export runs the license gate for its purpose and writes a dataset card next to
the output: sources, licenses, counts, and the sha256 of the output file.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd

from . import licenses
from .canonical import file_sha256
from .io import write_jsonl
from .schema import Record, utc_now


def gate_records(records, purpose: str):
    kept, blocked = [], Counter()
    for r in records:
        ok, why = licenses.allowed(r, purpose)
        if ok:
            kept.append(r)
        else:
            blocked[f"{r.source_id}: {why}"] += 1
    return kept, blocked


def _card(path: Path, records, purpose: str, blocked: Counter, fmt: str) -> dict:
    card = {
        "file": path.name, "format": fmt, "purpose": purpose, "created_utc": utc_now(),
        "sha256": file_sha256(path), "n_records": len(records),
        "by_source": dict(Counter(r.source_id for r in records)),
        "licenses": dict(Counter(r.license for r in records)),
        "by_kind": dict(Counter(r.kind for r in records)),
        "blocked": dict(blocked),
        "note": "Each record keeps its source license. Share-alike sources require the "
                "same license on derived data. Attribution text is in sources/<id>.yaml.",
    }
    Path(str(path) + ".card.json").write_text(json.dumps(card, indent=2) + "\n")
    return card


def export_jsonl(records, path, purpose: str = "train_research") -> dict:
    kept, blocked = gate_records(records, purpose)
    write_jsonl(kept, path)
    return _card(Path(path), kept, purpose, blocked, "jsonl")


def _flat_row(r: Record) -> dict:
    p = r.payload
    return {
        "record_id": r.record_id, "source_id": r.source_id, "dataset_id": r.dataset_id,
        "native_id": r.native_id, "kind": r.kind, "parent_id": r.parent_id,
        "license": r.license, "origin": r.origin, "text": r.text,
        "smiles": getattr(p, "smiles", None),
        "payload_json": p.model_dump_json(exclude_none=True),
        "properties_json": json.dumps({k: v.model_dump(exclude_none=True)
                                       for k, v in r.properties.items()}),
        "record_hash": r.record_hash, "schema_version": r.schema_version,
    }


def export_parquet(records, path, purpose: str = "train_research") -> dict:
    kept, blocked = gate_records(records, purpose)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([_flat_row(r) for r in kept]).to_parquet(path, index=False)
    return _card(Path(path), kept, purpose, blocked, "parquet")


def chunk_text(r: Record, homepage: str = "") -> str:
    """Deterministic text for one record, ending with a citation line."""
    p = r.payload
    lines = [f"[{r.kind}] {r.text}" if r.text else f"[{r.kind}]"]
    if p.kind == "molecule":
        lines.append(f"SMILES: {p.smiles}" + (f" ({p.name})" if p.name else ""))
    elif p.kind == "reaction":
        lines.append(f"Reaction: {'.'.join(p.reactants)} >> {'.'.join(p.products)}")
    elif p.kind == "structure":
        counts = Counter(p.elements)
        formula = "".join(f"{el}{n if n > 1 else ''}" for el, n in sorted(counts.items()))
        lines.append(f"Structure: {formula}, {len(p.elements)} atoms (xyz in Angstrom in payload)")
    elif p.kind == "protocol_step":
        lines.append(f"Step {p.index}: {p.text}")
    elif p.kind == "protocol":
        lines.append(f"Protocol: {p.title}")
    elif p.kind == "qa_item":
        lines.append(f"Q: {p.question}")
        if p.choices:
            lines.append("Choices: " + " | ".join(p.choices))
    elif p.kind == "observation":
        lines.append(f"{p.property} = {p.value.value} {p.value.unit}")
    for k, q in sorted(r.properties.items()):
        lines.append(f"{k} = {q.value} {q.unit}")
    lines.append(f"Source: {r.source_id} | License: {r.license} | id: {r.record_id}"
                 + (f" | {homepage}" if homepage else ""))
    return "\n".join(lines)


def export_rag_chunks(records, path, purpose: str = "rag", homepages: dict | None = None) -> dict:
    kept, blocked = gate_records(records, purpose)
    homepages = homepages or {}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in kept:
            f.write(json.dumps({"id": r.record_id, "text": chunk_text(r, homepages.get(r.source_id, "")),
                                "source_id": r.source_id, "license": r.license, "kind": r.kind,
                                "parent_id": r.parent_id}) + "\n")
    return _card(Path(path), kept, purpose, blocked, "rag-jsonl")
