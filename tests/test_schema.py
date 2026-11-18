import json

import pytest
from pydantic import ValidationError

from assayfold.schema import (Molecule, Record, Structure, export_json_schema, make_record_id,
                              new_record)


def test_record_round_trip_keeps_hash(mol):
    again = Record.model_validate_json(mol.model_dump_json())
    assert again.record_hash == mol.record_hash == again.content_hash()


def test_record_id_is_deterministic():
    assert make_record_id("a", "b", "1") == make_record_id("a", "b", "1")
    assert make_record_id("a", "b", "1") != make_record_id("a", "b", "2")


def test_hash_changes_with_content(mol):
    other = mol.model_copy(update={"text": "changed"})
    assert other.content_hash() != mol.record_hash


def test_kind_must_match_payload(mol):
    d = json.loads(mol.model_dump_json())
    d["kind"] = "reaction"
    with pytest.raises(ValidationError):
        Record.model_validate(d)


def test_structure_shape_checked():
    with pytest.raises(ValidationError):
        Structure(elements=["C", "H"], coords_angstrom=[[0, 0, 0]])


def test_unknown_field_rejected():
    with pytest.raises(ValidationError):
        Molecule(smiles="C", colour="blue")


def test_json_schema_export(tmp_path):
    paths = export_json_schema(tmp_path)
    names = sorted(p.name for p in paths)
    assert names == ["dataset.schema.json", "record.schema.json", "source.schema.json"]
    schema = json.loads((tmp_path / "record.schema.json").read_text())
    assert "payload" in schema["properties"]


def test_committed_json_schema_is_current(tmp_path):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "schema"
    for p in export_json_schema(tmp_path):
        assert (root / p.name).read_text() == p.read_text(), f"run `assayfold schema` ({p.name})"
