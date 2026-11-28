"""BioProBench: protocol QA, ordering, error correction, generation. CC-BY-NC-4.0.

Non-commercial: fetched by script only, never committed, blocked for commercial training.
"""

import json

from ..schema import Provenance, QAItem, new_record
from .base import Connector, download

URL = "https://huggingface.co/datasets/BioProBench/BioProBench/resolve/main/{f}"
FILES = {"PQA": "PQA_test.json", "ORD": "ORD_test.json", "ERR": "ERR_test.json",
         "GEN": "GEN_test.json"}


def to_qa(task: str, x: dict) -> QAItem:
    """Map one BioProBench item to a QAItem. Field names follow the released JSON."""
    if task == "PQA":
        return QAItem(task="bioprobench/PQA", question=x["question"], choices=x["choices"],
                      answer=x["answer"])
    if task == "ORD":
        return QAItem(task="bioprobench/ORD", question=x["question"], choices=x["wrong_steps"],
                      answer=json.dumps(x["correct_steps"]))
    if task == "ERR":
        ctx = json.dumps(x.get("context", {}))
        return QAItem(task="bioprobench/ERR", question=f"Is this step correct? {x['corrupted_text']}",
                      choices=["correct", "incorrect"],
                      answer="correct" if x["is_correct"] else "incorrect", context=ctx)
    return QAItem(task="bioprobench/GEN", question=x["input"], answer="\n".join(x["output"]),
                  context=x.get("instruction"))


class BioProBench(Connector):
    source_id = "bioprobench"
    dataset_id = "bioprobench-test"
    dataset_version = "HF BioProBench/BioProBench main (test files)"
    dataset_url = "https://huggingface.co/datasets/BioProBench/BioProBench"

    def fetch(self, raw_dir=None, limit=None):
        d = raw_dir or self.raw_dir()
        for f in FILES.values():
            download(URL.format(f=f), d / f)
        return d

    def convert(self, raw_dir=None, limit=None):
        d, n = raw_dir or self.raw_dir(), 0
        for task, f in FILES.items():
            for x in json.loads((d / f).read_text()):
                if limit is not None and n >= limit:
                    return
                qa = to_qa(task, x)
                canary = str(x.get("canary") or "").strip() or None
                if canary:
                    qa.canary = canary
                yield new_record(self.source_id, f"{self.dataset_id}/{task}", x["id"], qa,
                                 license=self.source.license, origin="real", text=qa.question,
                                 tags=["eval_only", "non_commercial"], canary=canary,
                                 provenance=Provenance(source_url=URL.format(f=f)))
                n += 1


CONNECTOR = BioProBench
