"""Read and write unified records as JSON Lines."""

import json
from pathlib import Path

from .schema import Record


def write_jsonl(records, path) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w") as f:
        for r in records:
            f.write(r.model_dump_json(exclude_none=True) + "\n")
            n += 1
    return n


def read_jsonl(path, as_dict: bool = False):
    with open(path) as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                yield d if as_dict else Record.model_validate(d)
