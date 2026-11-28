"""ChemBench: curated chemistry and lab-safety benchmark (MIT, evaluation only)."""

import ast
import json
from pathlib import Path

import pandas as pd

from ..schema import Provenance, QAItem, new_record
from .base import Connector, download

SUBSETS = [
    "general_chemistry",
    "toxicity_and_safety",
    "organic_chemistry",
    "inorganic_chemistry",
    "physical_chemistry",
    "analytical_chemistry",
    "materials_science",
    "technical_chemistry",
    "chemical_preference",
]
URL = "https://huggingface.co/datasets/jablonkagroup/ChemBench/resolve/main/{s}/train-00000-of-00001.parquet"


def _parse_examples(raw):
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return ast.literal_eval(raw)
    if hasattr(raw, "tolist"):
        return raw.tolist()
    return list(raw)


def _parse_scores(raw):
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return ast.literal_eval(raw)
    return None


def row_to_qa(subset: str, row: dict) -> QAItem:
    examples = _parse_examples(row["examples"])
    ex = examples[0] if examples else {}
    question = str(ex.get("input") or row.get("description") or "").strip()
    scores = _parse_scores(ex.get("target_scores"))
    choices = []
    answer = None
    if scores:
        choices = [str(k) for k in scores.keys()]
        winners = [str(k) for k, v in scores.items() if float(v) > 0]
        answer = "; ".join(winners) if winners else None
    elif ex.get("target") is not None:
        answer = str(ex["target"])
    raw_canary = row.get("canary")
    canary = (
        str(raw_canary).strip()
        if raw_canary is not None and pd.notna(raw_canary) and str(raw_canary).strip()
        else None
    )
    return QAItem(
        task=f"chembench/{subset}",
        question=question,
        choices=choices,
        answer=answer,
        context=str(row.get("description") or "") or None,
        canary=canary,
    )


class ChemBench(Connector):
    source_id = "chembench"
    dataset_id = "chembench"
    dataset_version = "HF jablonkagroup/ChemBench main"
    dataset_url = "https://huggingface.co/datasets/jablonkagroup/ChemBench"
    subsets = ["general_chemistry", "toxicity_and_safety"]

    def fetch(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        for s in self.subsets:
            download(URL.format(s=s), d / f"{s}.parquet")
        return d

    def convert(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        n = 0
        for s in self.subsets:
            p = d / f"{s}.parquet"
            if not p.exists():
                continue
            for row in pd.read_parquet(p).to_dict("records"):
                if limit is not None and n >= limit:
                    return
                qa = row_to_qa(s, row)
                uid = str(row.get("uuid") or row.get("name") or f"{s}_{n}")
                yield new_record(
                    self.source_id,
                    f"{self.dataset_id}/{s}",
                    uid,
                    qa,
                    license=self.source.license,
                    origin="real",
                    text=qa.question,
                    tags=["eval_only", "canary:chembench", f"subset:{s}"],
                    canary=qa.canary,
                    provenance=Provenance(source_url=URL.format(s=s)),
                )
                n += 1


CONNECTOR = ChemBench
