"""License gate. Unknown or missing licenses are always blocked.

This is an engineering guard, not legal advice. Each source's license is checked by a
person and recorded with an evidence URL in sources/<id>.yaml.
"""

# SPDX id -> (redistribute, commercial, share_alike, attribution)
TABLE = {
    "CC0-1.0":      (True, True, False, False),
    "PDDL-1.0":     (True, True, False, False),
    "CC-BY-4.0":    (True, True, False, True),
    "CC-BY-3.0":    (True, True, False, True),
    "CC-BY-SA-3.0": (True, True, True, True),
    "CC-BY-SA-4.0": (True, True, True, True),
    "ODbL-1.0":     (True, True, True, True),
    "MIT":          (True, True, False, True),
    "Apache-2.0":   (True, True, False, True),
    "BSD-3-Clause": (True, True, False, True),
    "CC-BY-NC-4.0": (True, False, False, True),
    "CC-BY-NC-SA-4.0": (True, False, True, True),
}

PURPOSES = ("train_commercial", "train_research", "rag", "redistribute_sample")


def info(spdx: str) -> dict:
    """Return the license flags, or None values when the id is unknown."""
    if spdx not in TABLE:
        return {"known": False}
    r, c, sa, att = TABLE[spdx]
    return {"known": True, "redistribute": r, "commercial": c, "share_alike": sa,
            "attribution": att, "non_commercial": not c}


def gate(spdx: str, purpose: str) -> tuple[bool, str]:
    """Is data under `spdx` allowed for `purpose`? Returns (ok, reason)."""
    if purpose not in PURPOSES:
        raise ValueError(f"unknown purpose {purpose!r}; use one of {PURPOSES}")
    if not spdx:
        return False, "missing license"
    i = info(spdx)
    if not i["known"]:
        return False, f"unknown license {spdx!r}"
    if purpose == "train_commercial" and not i["commercial"]:
        return False, f"{spdx} does not allow commercial use"
    if purpose == "redistribute_sample" and i["non_commercial"]:
        # NC data is never committed to this repo; it is fetched by script only.
        return False, f"{spdx} is non-commercial; not committed, fetch by script only"
    if purpose == "redistribute_sample" and not i["redistribute"]:
        return False, f"{spdx} does not allow redistribution"
    note = "share-alike: derived data keeps the same license" if i["share_alike"] else "ok"
    return True, note


EVAL_ONLY_TAG = "eval_only"


def allowed(record, purpose: str) -> tuple[bool, str]:
    """License gate plus the benchmark rule: eval-only records never enter training."""
    if purpose.startswith("train") and EVAL_ONLY_TAG in record.tags:
        return False, "benchmark item (eval_only): keep out of training corpora"
    return gate(record.license, purpose)
