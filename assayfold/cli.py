"""Command line: assayfold list|fetch|convert|sample|check|export|scan-contamination|catalog|schema."""

import argparse
import json
import sys
from pathlib import Path

from . import catalog, connectors, licenses, notice, quality
from .export import export_jsonl, export_parquet, export_rag_chunks, scan_contamination
from .io import read_jsonl, write_jsonl
from .schema import Dataset, export_json_schema, utc_now

ROOT = Path(__file__).resolve().parents[1]


def cmd_list(a):
    for s in catalog.load_sources():
        flag = "" if s.commercial_use_ok else "  [non-commercial]"
        print(f"{s.id:14s} {s.license:14s} {s.status:11s} {s.name}{flag}")


def cmd_fetch(a):
    c = connectors.get(a.id)
    print(c.fetch(limit=a.limit))


def cmd_convert(a):
    c = connectors.get(a.id)
    out = a.out or ROOT / "data" / "unified" / f"{a.id}.jsonl"
    n = write_jsonl(c.convert(limit=a.limit), out)
    print(f"wrote {n} records to {out}")


def cmd_sample(a):
    """Write a small committed sample. Refused when the license gate says no."""
    c = connectors.get(a.id)
    ok, why = licenses.gate(c.source.license, "redistribute_sample")
    if not ok or not c.source.redistribution_ok:
        sys.exit(f"refused: {why}")
    if c.source.status != "integrated":
        sys.exit(f"refused: {a.id} is {c.source.status}; see notes in sources/{a.id}.yaml")
    c.fetch(limit=a.limit)
    recs, report = quality.run_all(c.convert(limit=a.limit), purpose="redistribute_sample")
    d = ROOT / "samples" / a.id
    write_jsonl(recs, d / "records.jsonl")
    ds = Dataset(id=c.dataset_id, source_id=c.source_id, name=c.source.name,
                 version=c.dataset_version, url=c.dataset_url, license=c.source.license,
                 files=c.files_sha256())
    meta = {"n_records": len(recs), "quality": report.summary(), "created_utc": utc_now(),
            "dataset": ds.model_dump(mode="json"),
            "partial_read": c.is_partial(),
            "converter_skipped_rows": c.skipped_rows,
            "command": f"assayfold sample {a.id} --limit {a.limit}"}
    (d / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    (d / "NOTICE.md").write_text(notice.notice_text(c.source))
    print(json.dumps(meta["quality"]))


def cmd_check(a):
    bad = 0
    if a.dedup == "global" and len(a.files) > 1:
        recs = [r for p in a.files for r in read_jsonl(p, as_dict=True)]
        _, rep = quality.run_all(
            recs,
            purpose=a.purpose,
            scope=a.dedup,
            allow_eval_in_rag=a.allow_eval_in_rag,
            allow_unsealed=a.allow_unsealed,
        )
        print(" ".join(a.files), json.dumps(rep.summary()))
        for f in rep.failures[:20]:
            print("  ", *f)
        bad += len(rep.failures)
    else:
        for path in a.files:
            _, rep = quality.run_all(
                read_jsonl(path, as_dict=True),
                purpose=a.purpose,
                scope=a.dedup,
                allow_eval_in_rag=a.allow_eval_in_rag,
                allow_unsealed=a.allow_unsealed,
            )
            print(path, json.dumps(rep.summary()))
            for f in rep.failures[:20]:
                print("  ", *f)
            bad += len(rep.failures)
    sys.exit(1 if bad and a.strict else 0)


def cmd_export(a):
    # dicts, so quality.run_all checks record_hash on the records exactly as stored
    recs = [r for p in a.files for r in read_jsonl(p, as_dict=True)]
    purpose = a.purpose or ("rag" if a.format == "rag" else "train_research")
    homepages = {s.id: s.homepage for s in catalog.load_sources()}
    kw = {
        "scope": a.dedup,
        "allow_eval_in_rag": a.allow_eval_in_rag,
        "allow_unsealed": a.allow_unsealed,
    }
    if a.format == "rag":
        card = export_rag_chunks(recs, a.out, purpose, homepages, **kw)
    else:
        fn = {"jsonl": export_jsonl, "parquet": export_parquet}[a.format]
        card = fn(recs, a.out, purpose, **kw)
    print(json.dumps(card, indent=2))


def cmd_scan_contamination(a):
    res = scan_contamination(a.export, a.eval)
    print(json.dumps(res, indent=2))
    sys.exit(1 if res["contaminated"] else 0)


def cmd_catalog(a):
    if a.check:
        ok = catalog.build(check=True)
        print("catalog up to date" if ok else "catalog is stale: run `assayfold catalog`")
        sys.exit(0 if ok else 1)
    catalog.build()
    print("wrote catalog.csv and README table")


def cmd_schema(a):
    for p in export_json_schema(ROOT / "schema"):
        print(p)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="assayfold")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    for name, fn in (("fetch", cmd_fetch), ("convert", cmd_convert), ("sample", cmd_sample)):
        p = sub.add_parser(name)
        p.add_argument("id")
        p.add_argument("--limit", type=int, default=25 if name == "sample" else None)
        if name == "convert":
            p.add_argument("--out")
        p.set_defaults(fn=fn)
    p = sub.add_parser("check")
    p.add_argument("files", nargs="+")
    p.add_argument("--purpose", default="train_research", choices=licenses.PURPOSES)
    p.add_argument("--dedup", default="source", choices=quality.DEDUP_SCOPES)
    p.add_argument("--allow-eval-in-rag", action="store_true")
    p.add_argument("--allow-unsealed", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser("export")
    p.add_argument("files", nargs="+")
    p.add_argument("--format", choices=["jsonl", "parquet", "rag"], default="jsonl")
    p.add_argument("--purpose", choices=licenses.PURPOSES,
                   help="default: rag for --format rag, otherwise train_research")
    p.add_argument("--dedup", default="source", choices=quality.DEDUP_SCOPES)
    p.add_argument("--allow-eval-in-rag", action="store_true")
    p.add_argument("--allow-unsealed", action="store_true")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_export)
    p = sub.add_parser("scan-contamination")
    p.add_argument("export")
    p.add_argument("--eval", action="append", required=True, help="eval JSONL file(s) to scan for")
    p.set_defaults(fn=cmd_scan_contamination)
    p = sub.add_parser("catalog")
    p.add_argument("--check", action="store_true")
    p.set_defaults(fn=cmd_catalog)
    sub.add_parser("schema").set_defaults(fn=cmd_schema)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
