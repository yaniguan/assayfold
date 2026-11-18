"""Build catalog.csv and the README table from sources/*.yaml and samples/<id>/meta.json."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import yaml

from .schema import Source

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ["id", "name", "modalities", "kinds", "license", "commercial_use_ok",
           "redistribution_ok", "size_full", "n_sample_records", "status", "homepage",
           "license_evidence"]
START, END = "<!-- catalog:start -->", "<!-- catalog:end -->"


def load_sources(root: Path = ROOT) -> list[Source]:
    return [Source.model_validate(yaml.safe_load(p.read_text()))
            for p in sorted((root / "sources").glob("*.yaml"))]


def rows(root: Path = ROOT) -> list[dict]:
    out = []
    for s in load_sources(root):
        meta = root / "samples" / s.id / "meta.json"
        n = json.loads(meta.read_text())["n_records"] if meta.exists() else 0
        out.append({"id": s.id, "name": s.name, "modalities": ";".join(s.modalities),
                    "kinds": ";".join(s.kinds), "license": s.license,
                    "commercial_use_ok": s.commercial_use_ok,
                    "redistribution_ok": s.redistribution_ok, "size_full": s.size_full or "",
                    "n_sample_records": n, "status": s.status, "homepage": s.homepage,
                    "license_evidence": s.license_evidence})
    return out


def to_csv(rs) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rs)
    return buf.getvalue()


def to_markdown(rs) -> str:
    lines = ["| Source | Modalities | License | Commercial use | Full size | Sample records | Status |",
             "|---|---|---|---|---|---|---|"]
    for r in rs:
        lic = r["license"] + (" (non-commercial)" if not r["commercial_use_ok"] else "")
        lines.append(f"| [{r['name']}]({r['homepage']}) | {r['modalities'].replace(';', ', ')} | "
                     f"[{lic}]({r['license_evidence']}) | {'yes' if r['commercial_use_ok'] else 'no'} | "
                     f"{r['size_full']} | {r['n_sample_records']} | {r['status']} |")
    return "\n".join(lines)


def _readme_with(text: str, table: str) -> str:
    a, b = text.index(START) + len(START), text.index(END)
    return text[:a] + "\n" + table + "\n" + text[b:]


def build(root: Path = ROOT, check: bool = False) -> bool:
    """Write catalog.csv and the README table. With check=True, only report staleness."""
    rs = rows(root)
    csv_text, readme_p = to_csv(rs), root / "README.md"
    readme_new = _readme_with(readme_p.read_text(), to_markdown(rs))
    stale = ((root / "catalog.csv").read_text() if (root / "catalog.csv").exists() else "") != csv_text \
        or readme_p.read_text() != readme_new
    if check:
        return not stale
    (root / "catalog.csv").write_text(csv_text)
    readme_p.write_text(readme_new)
    return True
