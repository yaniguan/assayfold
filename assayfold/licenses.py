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

# "rag" means an index that may serve a commercial product, so non-commercial data is
# blocked there. "rag_research" allows it and returns a research-use-only note.
PURPOSES = ("train_commercial", "train_research", "rag", "rag_research", "redistribute_sample")
COMMERCIAL_PURPOSES = ("train_commercial", "rag")
NC_RESEARCH_NOTE = "non-commercial: research use only"


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
    if purpose in COMMERCIAL_PURPOSES and not i["commercial"]:
        return False, f"{spdx} does not allow commercial use (purpose {purpose})"
    if purpose == "redistribute_sample" and i["non_commercial"]:
        # NC data is never committed to this repo; it is fetched by script only.
        return False, f"{spdx} is non-commercial; not committed, fetch by script only"
    if purpose == "redistribute_sample" and not i["redistribute"]:
        return False, f"{spdx} does not allow redistribution"
    notes = []
    if i["share_alike"]:
        notes.append("share-alike: derived data keeps the same license")
    if i["non_commercial"]:
        notes.append(NC_RESEARCH_NOTE)
    return True, "; ".join(notes) or "ok"


EVAL_ONLY_TAG = "eval_only"
NON_COMMERCIAL_TAG = "non_commercial"

_SOURCES = None


def source_table() -> dict:
    """source_id -> Source from sources/*.yaml, loaded once."""
    global _SOURCES
    if _SOURCES is None:
        from .catalog import load_sources
        _SOURCES = {s.id: s for s in load_sources()}
    return _SOURCES


def allowed(record, purpose: str, sources: dict | None = None) -> tuple[bool, str]:
    """License gate checked against sources/<id>.yaml, plus the benchmark rule.

    The record's own license string is not trusted: its source_id must be known and its
    license must equal the source's license. Eval-only records never enter training.
    """
    src = (source_table() if sources is None else sources).get(record.source_id)
    if src is None:
        return False, f"unknown source_id {record.source_id!r} (no sources/<id>.yaml)"
    if record.license != src.license:
        return False, f"record license {record.license!r} differs from source license {src.license!r}"
    if purpose in COMMERCIAL_PURPOSES and (not src.commercial_use_ok or NON_COMMERCIAL_TAG in record.tags):
        return False, f"non-commercial source or record; blocked for {purpose}"
    if purpose == "redistribute_sample" and not src.redistribution_ok:
        return False, "source does not allow redistribution"
    if purpose.startswith("train") and EVAL_ONLY_TAG in record.tags:
        return False, "benchmark item (eval_only): keep out of training corpora"
    return gate(record.license, purpose)
