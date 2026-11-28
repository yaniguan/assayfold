"""Export unified records for training (JSONL, Parquet) and retrieval (RAG chunks).

Every export runs the same checks as `assayfold check` and `sample` (quality.run_all:
sealing, integrity, schema, units, SMILES, periodic-table/force checks, license + eval_only
gate for its purpose, and content-level dedup) and writes a dataset card next to the output:
sources, licenses, counts, cross-source duplicate pairs, eval-item flags, quality summary,
and the sha256 of the output file.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

from . import licenses, quality
from .canonical import file_sha256
from .io import write_jsonl
from .schema import Record, utc_now


def check_records(
    records,
    purpose: str,
    scope: str = "source",
    *,
    allow_eval_in_rag: bool = False,
    allow_unsealed: bool = False,
):
    """Run quality.run_all for `purpose`. Returns (kept, QualityReport, blocked-by-license)."""
    kept, report = quality.run_all(
        records,
        purpose=purpose,
        scope=scope,
        allow_eval_in_rag=allow_eval_in_rag,
        allow_unsealed=allow_unsealed,
    )
    blocked = Counter(reason for _, check, reason in report.failures if check == "license")
    return kept, report, blocked


def _license_notes(records, purpose: str) -> dict:
    """source_id -> gate note (share-alike, non-commercial research use) for kept records."""
    notes = {}
    for r in records:
        if r.source_id not in notes:
            why = licenses.gate(r.license, purpose)[1]
            if why != "ok":
                notes[r.source_id] = why
    return notes


def _card(
    path: Path,
    records,
    purpose: str,
    report,
    blocked: Counter,
    fmt: str,
    scope: str = "source",
) -> dict:
    n_eval = sum(1 for r in records if licenses.EVAL_ONLY_TAG in r.tags)
    card = {
        "file": path.name,
        "format": fmt,
        "purpose": purpose,
        "dedup_scope": scope,
        "created_utc": utc_now(),
        "sha256": file_sha256(path),
        "n_records": len(records),
        "contains_eval_items": bool(n_eval > 0),
        "n_eval_items": n_eval,
        "by_source": dict(Counter(r.source_id for r in records)),
        "licenses": dict(Counter(r.license for r in records)),
        "license_notes": _license_notes(records, purpose),
        "by_kind": dict(Counter(r.kind for r in records)),
        "duplicates_by_source_pair": dict(report.duplicates_by_source_pair),
        "quality": report.summary(),
        "blocked": dict(blocked),
        "note": "Each record keeps its source license. Share-alike sources require the "
                "same license on derived data. Attribution text is in sources/<id>.yaml.",
    }
    Path(str(path) + ".card.json").write_text(json.dumps(card, indent=2) + "\n")
    return card


def export_jsonl(
    records,
    path,
    purpose: str = "train_research",
    *,
    scope: str = "source",
    allow_eval_in_rag: bool = False,
    allow_unsealed: bool = False,
) -> dict:
    kept, report, blocked = check_records(
        records,
        purpose,
        scope=scope,
        allow_eval_in_rag=allow_eval_in_rag,
        allow_unsealed=allow_unsealed,
    )
    write_jsonl(kept, path)
    return _card(Path(path), kept, purpose, report, blocked, "jsonl", scope=scope)


def _flat_row(r: Record) -> dict:
    p = r.payload
    return {
        "record_id": r.record_id,
        "source_id": r.source_id,
        "dataset_id": r.dataset_id,
        "native_id": r.native_id,
        "kind": r.kind,
        "parent_id": r.parent_id,
        "license": r.license,
        "origin": r.origin,
        "text": r.text,
        "smiles": getattr(p, "smiles", None),
        "canary": r.canary,
        "payload_json": p.model_dump_json(exclude_none=True),
        "properties_json": json.dumps({k: v.model_dump(exclude_none=True)
                                       for k, v in r.properties.items()}),
        "record_hash": r.record_hash,
        "schema_version": r.schema_version,
    }


def export_parquet(
    records,
    path,
    purpose: str = "train_research",
    *,
    scope: str = "source",
    allow_eval_in_rag: bool = False,
    allow_unsealed: bool = False,
) -> dict:
    kept, report, blocked = check_records(
        records,
        purpose,
        scope=scope,
        allow_eval_in_rag=allow_eval_in_rag,
        allow_unsealed=allow_unsealed,
    )
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([_flat_row(r) for r in kept]).to_parquet(path, index=False)
    return _card(Path(path), kept, purpose, report, blocked, "parquet", scope=scope)


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
    elif p.kind == "spectrum":
        lines.append(f"Spectrum ({p.technique}): {len(p.x)} points, x in {p.x_unit}, y in {p.y_unit}")
    for k, q in sorted(r.properties.items()):
        lines.append(f"{k} = {q.value} {q.unit}")
    if r.canary:
        lines.append(f"Canary: {r.canary}")
    lines.append(f"Source: {r.source_id} | License: {r.license} | id: {r.record_id}"
                 + (f" | {homepage}" if homepage else ""))
    return "\n".join(lines)


def export_rag_chunks(
    records,
    path,
    purpose: str = "rag",
    homepages: dict | None = None,
    *,
    scope: str = "source",
    allow_eval_in_rag: bool = False,
    allow_unsealed: bool = False,
) -> dict:
    kept, report, blocked = check_records(
        records,
        purpose,
        scope=scope,
        allow_eval_in_rag=allow_eval_in_rag,
        allow_unsealed=allow_unsealed,
    )
    homepages = homepages or {}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in kept:
            row = {
                "id": r.record_id,
                "text": chunk_text(r, homepages.get(r.source_id, "")),
                "source_id": r.source_id,
                "license": r.license,
                "kind": r.kind,
                "parent_id": r.parent_id,
            }
            if r.canary:
                row["canary"] = r.canary
            f.write(json.dumps(row) + "\n")
    return _card(Path(path), kept, purpose, report, blocked, "rag-jsonl", scope=scope)


def _norm_scan(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def _load_export_entries(export_path: Path) -> list[tuple[str, str, set[str]]]:
    """Return [(entry_id, normalized_blob, explicit_canaries)] from a JSONL, Parquet, or text export."""
    entries = []
    if export_path.suffix.lower() == ".parquet":
        df = pd.read_parquet(export_path)
        for idx, row in df.iterrows():
            d = row.to_dict()
            eid = str(d.get("record_id") or d.get("id") or f"row_{idx}")
            canaries = set()
            if d.get("canary") and pd.notna(d.get("canary")):
                canaries.add(_norm_scan(str(d["canary"])))
            pj = d.get("payload_json")
            if isinstance(pj, str) and pj.strip():
                try:
                    pobj = json.loads(pj)
                    if isinstance(pobj, dict) and pobj.get("canary"):
                        canaries.add(_norm_scan(str(pobj["canary"])))
                except json.JSONDecodeError:
                    pass
            parts = [str(v) for v in d.values() if v is not None and pd.notna(v)]
            entries.append((eid, _norm_scan(" ".join(parts)), canaries))
        return entries

    with open(export_path, encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            canaries = set()
            eid = f"line_{idx}"
            parts = [s]
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                obj = None
            if isinstance(obj, dict):
                eid = str(obj.get("record_id") or obj.get("id") or eid)
                if obj.get("canary"):
                    canaries.add(_norm_scan(str(obj["canary"])))
                if obj.get("text"):
                    parts.append(str(obj["text"]))
                pl = obj.get("payload")
                if isinstance(pl, dict):
                    if pl.get("canary"):
                        canaries.add(_norm_scan(str(pl["canary"])))
                    if pl.get("question"):
                        parts.append(str(pl["question"]))
            entries.append((eid, _norm_scan(" ".join(parts)), canaries))
    return entries


def _iter_eval_items(eval_paths) -> list[tuple[str, str, str]]:
    """Yield (eval_id, norm_question, norm_canary) from one or more JSONL files."""
    if isinstance(eval_paths, (str, Path)):
        eval_paths = [eval_paths]
    items = []
    for ep in eval_paths:
        with open(ep, encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                d = json.loads(line)
                pl = d.get("payload") if isinstance(d.get("payload"), dict) else {}
                eid = str(d.get("record_id") or d.get("native_id") or d.get("id") or f"{Path(ep).name}:{idx}")
                question = pl.get("question") or d.get("question") or d.get("text") or ""
                canary = d.get("canary") or pl.get("canary") or ""
                items.append((eid, _norm_scan(str(question)), _norm_scan(str(canary))))
    return items


def scan_contamination(export_path, eval_paths) -> dict:
    """Check whether any eval item's normalized question or canary appears in `export_path`."""
    export_p = Path(export_path)
    entries = _load_export_entries(export_p)
    eval_items = _iter_eval_items(eval_paths)
    hits = []
    for eval_id, norm_q, norm_c in eval_items:
        matched_in = None
        reason = None
        for entry_id, blob, explicit_canaries in entries:
            if norm_c and (
                norm_c in explicit_canaries
                or f"canary: {norm_c}" in blob
                or (len(norm_c) >= 8 and norm_c in blob)
            ):
                matched_in, reason = entry_id, "canary"
                break
            if norm_q and norm_q in blob:
                matched_in, reason = entry_id, "question"
                break
        if matched_in is not None:
            hits.append({"eval_id": eval_id, "export_entry": matched_in, "reason": reason})
    return {
        "export": str(export_p),
        "n_eval_checked": len(eval_items),
        "n_hits": len(hits),
        "contaminated": len(hits) > 0,
        "hits": hits,
    }
