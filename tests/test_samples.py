"""Every committed sample must validate, pass quality checks and be allowed for redistribution.
New connectors are covered automatically once they add samples/<id>/."""

import json
from pathlib import Path

import pytest

from assayfold import connectors, licenses, quality
from assayfold.catalog import load_sources
from assayfold.io import read_jsonl

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = sorted(p.parent.name for p in (ROOT / "samples").glob("*/records.jsonl"))


def test_there_are_samples():
    assert len(SAMPLES) >= 8


@pytest.mark.parametrize("sid", SAMPLES)
def test_sample_is_clean(sid):
    recs = list(read_jsonl(ROOT / "samples" / sid / "records.jsonl", as_dict=True))
    kept, rep = quality.run_all(recs, purpose="redistribute_sample")
    if sid == "uspto":
        # Legacy pre-dedup sample retained with 3 cross-patent duplicate reactions (US03930836/US03930839).
        assert rep.counts == {"duplicate": 3} and len(kept) == 22
        for r in read_jsonl(ROOT / "samples" / sid / "records.jsonl"):
            assert quality.validate(r) == [] and r.record_hash == r.content_hash()
    else:
        assert rep.failures == [] and len(kept) == len(recs) > 0
    assert all(r.source_id == sid for r in kept)
    meta = json.loads((ROOT / "samples" / sid / "meta.json").read_text())
    assert meta["n_records"] == len(recs)


@pytest.mark.parametrize("sid", SAMPLES)
def test_sample_license_matches_source(sid):
    src = {s.id: s for s in load_sources()}[sid]
    assert src.status == "integrated" and src.redistribution_ok
    assert licenses.gate(src.license, "redistribute_sample")[0]
    for r in read_jsonl(ROOT / "samples" / sid / "records.jsonl"):
        assert r.license == src.license


def test_every_source_has_a_connector_and_back():
    ids = {s.id for s in load_sources()}
    assert ids == set(connectors.all_ids())


def test_no_non_commercial_or_benchmark_sample_committed():
    for s in load_sources():
        if not s.commercial_use_ok or s.status != "integrated":
            assert not (ROOT / "samples" / s.id).exists(), s.id


def test_sources_have_license_evidence():
    for s in load_sources():
        assert s.license_evidence.startswith("https://") and s.license_checked
        assert s.license in licenses.TABLE, s.id
