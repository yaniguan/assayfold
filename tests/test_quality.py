import pytest

from assayfold import quality
from assayfold.schema import Molecule, new_record


def test_clean_records_pass(mol, rxn):
    kept, rep = quality.run_all([mol, rxn])
    assert rep.n_out == 2 and not rep.failures


def test_unit_normalized(rxn):
    rec = quality.normalize_units(rxn)
    q = rec.payload.conditions["temperature"]
    assert q.unit == "Cel" and q.raw_unit_str == "degC"


def test_bad_smiles_flagged():
    bad = new_record("aqsoldb", "t", "2", Molecule(smiles="C1CC(("), license="CC0-1.0", origin="real")
    kept, rep = quality.run_all([bad])
    assert not kept and rep.counts["bad SMILES"] == 1


def test_duplicates_reported(mol):
    dup = new_record("aqsoldb", "t", "other-id", Molecule(smiles="CCO"), license="CC0-1.0", origin="real")
    kept, rep = quality.run_all([mol, dup])
    assert len(kept) == 1 and rep.counts["duplicate"] == 1


def test_duplicates_found_by_canonical_smiles(mol):
    pytest.importorskip("rdkit")
    dup = new_record("aqsoldb", "t", "other-id", Molecule(smiles="OCC"), license="CC0-1.0", origin="real")
    kept, rep = quality.run_all([mol, dup])
    assert len(kept) == 1 and rep.counts["duplicate"] == 1


def test_unknown_unit_flagged(mol):
    mol.properties["x"] = mol.properties["log_solubility"].model_copy(update={"unit": "furlong"})
    kept, rep = quality.run_all([mol.sealed()])
    assert not kept and rep.counts["unknown unit"] == 1


def test_license_gate_in_quality(nc_item):
    kept, rep = quality.run_all([nc_item], purpose="train_commercial")
    assert not kept and rep.counts["license"] == 1


def test_tampered_hash_flagged(mol):
    d = mol.model_dump(mode="json")
    d["text"] = "edited after hashing"
    assert "record_hash mismatch" in quality.validate(d)

def test_tampered_hash_flagged_in_run_all(mol):
    """Integrity must fail in run_all, not only in validate(), even after unit normalization."""
    d = mol.model_dump(mode="json")
    d["text"] = "edited after hashing"
    kept, rep = quality.run_all([d])
    assert not kept and rep.counts["record_hash mismatch"] == 1
