"""EHRSQL-2024 clinical lab & EHR text-to-SQL benchmark over MIMIC-IV Demo v2.2. ODbL-1.0.

Evaluation-only benchmark (`eval_only` tag on every record): training exports and committed
samples are strictly blocked by the license gate, while retrieval exports propagate the
ODbL-1.0 ShareAlike obligation.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..schema import Provenance, QAItem, new_record
from .base import Connector, download

RAW_BASE = "https://raw.githubusercontent.com/glee4810/ehrsql-2024/master/data/mimic_iv"
FILES = {
    "tables.json": f"{RAW_BASE}/tables.json",
    "mimic_iv.sql": f"{RAW_BASE}/mimic_iv.sql",
    "valid_data.json": f"{RAW_BASE}/valid/data.json",
    "valid_label.json": f"{RAW_BASE}/valid/label.json",
}


def _schema_summary(tables_path: Path) -> str | None:
    if not tables_path.exists():
        return None
    raw = json.loads(tables_path.read_text(encoding="utf-8"))
    db = raw[0] if isinstance(raw, list) and raw else (raw if isinstance(raw, dict) else {})
    names = db.get("table_names_original") or db.get("table_names") or []
    return "MIMIC-IV Demo v2.2 SQLite tables: " + ", ".join(names) if names else None


def _iter_split_items(data_obj, labels_obj: dict):
    if isinstance(data_obj, dict) and "data" in data_obj:
        items = data_obj["data"]
    elif isinstance(data_obj, list):
        items = data_obj
    else:
        items = []
    for row in items:
        qid = str(row.get("id") or "")
        question = str(row.get("question") or "").strip()
        sql = row.get("query")
        if sql is None and qid in labels_obj:
            sql = labels_obj[qid]
        yield qid, question, sql


class EHRSQLMimicIVDemo(Connector):
    source_id = "ehrsql_mimic_iv_demo"
    dataset_id = "ehrsql-2024-mimic-iv-demo"
    dataset_version = "glee4810/ehrsql-2024 master + MIMIC-IV Demo v2.2"
    dataset_url = "https://github.com/glee4810/ehrsql-2024"

    def fetch(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        for fname, url in FILES.items():
            download(url, d / fname)
        return d

    def is_partial(self, raw_dir=None):
        return True

    def convert(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        ctx = _schema_summary(d / "tables.json")
        labels = {}
        if (d / "valid_label.json").exists():
            labels = json.loads((d / "valid_label.json").read_text(encoding="utf-8"))

        data_files = [
            p for p in [d / "valid_data.json", d / "annotated.json"] if p.exists()
        ]
        n = 0
        for p in data_files:
            raw = json.loads(p.read_text(encoding="utf-8"))
            for qid, question, sql in _iter_split_items(raw, labels):
                if not question:
                    continue
                if limit is not None and n >= limit:
                    return
                unanswerable = sql is None or str(sql).strip().lower() in ("", "null", "none")
                answer = "ABSTAIN" if unanswerable else str(sql).strip()
                tags = [
                    "eval_only",
                    "benchmark:ehrsql_2024",
                    "db:mimic_iv_demo_v2.2",
                    "answerable:false" if unanswerable else "answerable:true",
                ]
                yield new_record(
                    self.source_id,
                    self.dataset_id,
                    qid or f"q_{n}",
                    QAItem(
                        task="ehrsql_2024/text_to_sql",
                        question=question,
                        answer=answer,
                        context=ctx,
                    ),
                    license=self.source.license,
                    origin="real",
                    text=question,
                    tags=tags,
                    provenance=Provenance(source_url=self.dataset_url),
                )
                n += 1


CONNECTOR = EHRSQLMimicIVDemo
