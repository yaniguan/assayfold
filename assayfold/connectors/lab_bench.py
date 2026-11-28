"""LAB-Bench: biology research benchmark (CC-BY-SA-4.0). Records are eval_only."""

import pandas as pd

from ..schema import Provenance, QAItem, new_record
from .base import Connector, download

SUBSETS = ["ProtocolQA", "SeqQA", "LitQA2", "DbQA", "SuppQA", "CloningScenarios"]
URL = "https://huggingface.co/api/datasets/futurehouse/lab-bench/parquet/{s}/train/0.parquet"


class LabBench(Connector):
    source_id = "lab_bench"
    dataset_id = "lab-bench"
    dataset_version = "HF futurehouse/lab-bench parquet (train split)"
    dataset_url = "https://huggingface.co/datasets/futurehouse/lab-bench"
    subsets = ["ProtocolQA"]

    def fetch(self, raw_dir=None, limit=None):
        d = raw_dir or self.raw_dir()
        for s in self.subsets:
            download(URL.format(s=s), d / f"{s}.parquet")
        return d

    def convert(self, raw_dir=None, limit=None):
        d, n = raw_dir or self.raw_dir(), 0
        for s in self.subsets:
            for row in pd.read_parquet(d / f"{s}.parquet").to_dict("records"):
                if limit is not None and n >= limit:
                    return
                distractors = row.get("distractors")
                choices = [row["ideal"], *(list(distractors) if distractors is not None else [])]
                raw_canary = row.get("canary")
                canary = (
                    str(raw_canary).strip()
                    if raw_canary is not None and pd.notna(raw_canary) and str(raw_canary).strip()
                    else None
                )
                yield new_record(
                    self.source_id, f"{self.dataset_id}/{s}", row["id"],
                    QAItem(task=f"lab-bench/{s}", question=row["question"], choices=choices,
                           answer=row["ideal"], context=row.get("protocol") or None,
                           canary=canary),
                    license=self.source.license, origin="real",
                    text=row["question"], tags=["eval_only", "canary:lab-bench"],
                    canary=canary,
                    provenance=Provenance(source_url=URL.format(s=s)))
                n += 1


CONNECTOR = LabBench
