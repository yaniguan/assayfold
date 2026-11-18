import json

import pandas as pd

from assayfold.export import export_jsonl, export_parquet, export_rag_chunks
from assayfold.io import read_jsonl


def test_jsonl_round_trip(tmp_path, mol, rxn):
    card = export_jsonl([mol, rxn], tmp_path / "out.jsonl")
    back = list(read_jsonl(tmp_path / "out.jsonl"))
    assert [r.record_hash for r in back] == [mol.record_hash, rxn.record_hash]
    assert card["n_records"] == 2 and (tmp_path / "out.jsonl.card.json").exists()


def test_parquet_has_flat_columns(tmp_path, mol, rxn):
    export_parquet([mol, rxn], tmp_path / "out.parquet")
    df = pd.read_parquet(tmp_path / "out.parquet")
    assert list(df["kind"]) == ["molecule", "reaction"]
    assert json.loads(df.loc[0, "properties_json"])["log_solubility"]["unit"] == "[logS]"


def test_rag_chunk_cites_source(tmp_path, mol):
    export_rag_chunks([mol], tmp_path / "rag.jsonl", homepages={"aqsoldb": "https://x"})
    chunk = json.loads((tmp_path / "rag.jsonl").read_text())
    assert "License: CC0-1.0" in chunk["text"] and mol.record_id in chunk["text"]


def test_nc_and_eval_only_excluded_from_training(tmp_path, mol, nc_item):
    card = export_jsonl([mol, nc_item], tmp_path / "t.jsonl", purpose="train_commercial")
    assert card["n_records"] == 1 and card["blocked"]
