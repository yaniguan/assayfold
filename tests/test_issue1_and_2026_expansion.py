"""Comprehensive tests for Issue #1 resolution, 27-source catalog parity, UCUM conversions,
ShareAlike/ODbL/eval_only export gates, and protocols.io parser + token client mock."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pandas as pd
import pytest

from assayfold import catalog, connectors, licenses, quality, units
from assayfold.connectors import protocols_io, protocols_io_open
from assayfold.connectors.uspto_lowe import parse_cml_reactions, strip_atom_mapping
from assayfold.export import export_jsonl, export_parquet, export_rag_chunks
from assayfold.io import read_jsonl
from assayfold.schema import Quantity, Uncertainty

ROOT = Path(__file__).resolve().parents[1]

ISSUE1_AND_EXPANSION_SOURCES = {
    "uspto_lowe": ("CC0-1.0", True, True, "integrated"),
    "protocols_io_open": ("CC-BY-4.0", True, True, "integrated"),
    "tdc_lipophilicity": ("CC-BY-SA-3.0", True, True, "integrated"),
    "freesolv": ("CC-BY-4.0", True, True, "integrated"),
    "ucr_ftir_chemometrics": ("CC0-1.0", True, True, "integrated"),
    "ehrsql_mimic_iv_demo": ("ODbL-1.0", True, True, "fetch_only"),
    "labpics_chemistry": ("MIT", True, True, "integrated"),
    "uspto": ("CC0-1.0", True, True, "integrated"),
}


def test_catalog_27_sources_and_readme_100_percent_parity():
    assert catalog.build(ROOT, check=True), "catalog.csv or README.md is out of sync; run `assayfold catalog`"

    sources = catalog.load_sources(ROOT)
    assert len(sources) == 27

    with open(ROOT / "catalog.csv", newline="", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))
    assert len(csv_rows) == len(sources) == 27

    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    start_idx = readme_text.index(catalog.START) + len(catalog.START)
    end_idx = readme_text.index(catalog.END)
    md_block = readme_text[start_idx:end_idx].strip()
    md_lines = [ln.strip() for ln in md_block.splitlines() if ln.strip()]
    # 2 header lines + N data rows
    assert len(md_lines) == len(csv_rows) + 2
    assert md_block == catalog.to_markdown(catalog.rows(ROOT))

    for row, md_line in zip(csv_rows, md_lines[2:]):
        cells = [c.strip() for c in md_line.strip("|").split("|")]
        assert len(cells) == 7
        assert f"[{row['name']}]({row['homepage']})" == cells[0]
        assert row["modalities"].replace(";", ", ") == cells[1]
        assert row["license"] in cells[2]
        assert row["license_evidence"] in cells[2]
        expected_comm = "yes" if row["commercial_use_ok"] == "True" else "no"
        assert cells[3] == expected_comm
        assert cells[4] == row["size_full"]
        assert cells[5] == str(row["n_sample_records"])
        assert cells[6] == row["status"]

    matches = re.findall(r"\b(\d+)\s+(?:open\s+laboratory\s+sources|`sources/\*\.yaml`)", readme_text)
    assert matches, "README.md should state the explicit source count"
    for m in matches:
        assert int(m) == len(csv_rows)


def test_issue1_and_expansion_sources_registered():
    sources = {s.id: s for s in catalog.load_sources(ROOT)}
    reg = set(connectors.all_ids())
    for sid, (lic, comm_ok, redist_ok, status) in ISSUE1_AND_EXPANSION_SOURCES.items():
        assert sid in sources and sid in reg
        s = sources[sid]
        assert s.license == lic
        assert s.commercial_use_ok is comm_ok
        assert s.redistribution_ok is redist_ok
        assert s.status == status
        assert s.license in licenses.TABLE


def test_committed_expansion_samples_contents_and_size_budgets():
    # 1. uspto_lowe: < 50 KB, 25 Reaction records with SMILES, %, Cel/K, s
    uspto_lowe_path = ROOT / "samples" / "uspto_lowe" / "records.jsonl"
    assert uspto_lowe_path.stat().st_size < 50 * 1024
    ul_recs = list(read_jsonl(uspto_lowe_path))
    assert len(ul_recs) == 25
    for r in ul_recs:
        assert r.kind == "reaction"
        assert r.payload.reactants and r.payload.products
        assert r.payload.yield_percent is not None and r.payload.yield_percent.unit == "%"
        assert r.payload.conditions["temperature"].unit in ("Cel", "K")
        assert r.payload.conditions["reaction_time"].unit == "s"
        assert r.record_hash == r.content_hash()

    # 2. protocols_io_open: 15 Protocol + ProtocolStep records with UCUM uL, s, Cel
    pio_recs = list(read_jsonl(ROOT / "samples" / "protocols_io_open" / "records.jsonl"))
    assert len(pio_recs) == 15
    assert {r.kind for r in pio_recs} == {"protocol", "protocol_step"}
    step_units = {
        q.unit
        for r in pio_recs
        if r.kind == "protocol_step"
        for q in r.payload.params.values()
        if isinstance(q, Quantity)
    }
    assert {"uL", "s", "Cel"}.issubset(step_units)

    # 3. tdc_lipophilicity: 25 Molecule records, CC-BY-SA-3.0, [logD] & [pH]
    lipo_recs = list(read_jsonl(ROOT / "samples" / "tdc_lipophilicity" / "records.jsonl"))
    assert len(lipo_recs) == 25
    assert all(r.license == "CC-BY-SA-3.0" for r in lipo_recs)
    assert all(r.properties["logd_ph7_4"].unit == "[logD]" for r in lipo_recs)
    assert all(r.properties["ph"].unit == "[pH]" for r in lipo_recs)
    lipo_notice = (ROOT / "samples" / "tdc_lipophilicity" / "NOTICE.md").read_text(encoding="utf-8")
    assert "Share-alike: this adapted material is licensed under CC-BY-SA-3.0" in lipo_notice

    # 4. freesolv: 25 Molecule records in kcal/mol with experimental uncertainties
    fs_recs = list(read_jsonl(ROOT / "samples" / "freesolv" / "records.jsonl"))
    assert len(fs_recs) == 25
    for r in fs_recs:
        q = r.properties["hydration_free_energy_expt"]
        assert q.unit == "kcal/mol"
        assert q.uncertainty is not None and q.uncertainty.kind == "std" and q.uncertainty.std > 0
        q_kj = units.convert_quantity(q, "kJ/mol")
        assert q_kj.unit == "kJ/mol"
        assert q_kj.value == pytest.approx(q.value * 4.184)
        assert q_kj.uncertainty.std == pytest.approx(q.uncertainty.std * 4.184)

    # 5. ucr_ftir_chemometrics: 10 Spectrum records in /cm and absorbance 1 across matrices
    ftir_recs = list(read_jsonl(ROOT / "samples" / "ucr_ftir_chemometrics" / "records.jsonl"))
    assert len(ftir_recs) == 10
    matrices = {t.split(":", 1)[1] for r in ftir_recs for t in r.tags if t.startswith("matrix:")}
    assert {"olive_oil", "coffee", "fresh_meat"}.issubset(matrices)
    for r in ftir_recs:
        assert r.payload.technique == "FT-IR"
        assert r.payload.x_unit == "/cm"
        assert r.payload.y_unit == "1"
        assert len(r.payload.x) == len(r.payload.y) > 50

    # 6. ehrsql_mimic_iv_demo is fetch_only -> must NOT have a committed sample folder
    assert not (ROOT / "samples" / "ehrsql_mimic_iv_demo").exists()

    # 7. Total new committed samples strictly < 1 MB and SHA-256 sealed in meta.json
    new_sample_bytes = 0
    for sid in ("uspto_lowe", "protocols_io_open", "tdc_lipophilicity", "ucr_ftir_chemometrics", "labpics_chemistry", "uspto"):
        sdir = ROOT / "samples" / sid
        meta = json.loads((sdir / "meta.json").read_text(encoding="utf-8"))
        assert meta["dataset"]["files"], f"missing input file sha256 in {sid}/meta.json"
        for sha in meta["dataset"]["files"].values():
            assert re.fullmatch(r"[0-9a-f]{64}", sha)
        for f in sdir.iterdir():
            if f.is_file():
                new_sample_bytes += f.stat().st_size
    assert new_sample_bytes < 1024 * 1024


def test_ucum_conversions_kcal_kj_cel_kelvin_and_time():
    # kcal/mol <-> kJ/mol
    assert units.convert(-4.72, "kcal/mol", "kJ/mol") == pytest.approx(-4.72 * 4.184)
    assert units.convert(-19.74848, "kJ/mol", "kcal/mol") == pytest.approx(-4.72)

    q_kcal = Quantity(
        value=-2.49,
        unit="kcal/mol",
        uncertainty=Uncertainty(kind="std", std=0.6, low=-3.09, high=-1.89),
    )
    q_kj = units.convert_quantity(q_kcal, "kJ/mol")
    assert q_kj.unit == "kJ/mol"
    assert q_kj.value == pytest.approx(-2.49 * 4.184)
    assert q_kj.uncertainty.std == pytest.approx(0.6 * 4.184)
    q_back = units.convert_quantity(q_kj, "kcal/mol")
    assert q_back.value == pytest.approx(q_kcal.value)
    assert q_back.uncertainty.std == pytest.approx(q_kcal.uncertainty.std)

    # Cel <-> K (std invariant, interval bounds shifted by 273.15)
    assert units.convert(0.0, "Cel", "K") == pytest.approx(273.15)
    assert units.convert(273.15, "K", "Cel") == pytest.approx(0.0)
    assert units.convert(37.0, "degC", "K") == pytest.approx(310.15)
    assert units.convert(310.15, "K", "Cel") == pytest.approx(37.0)

    q_temp = Quantity(
        value=37.0,
        unit="Cel",
        uncertainty=Uncertainty(kind="interval", std=0.5, low=36.5, high=37.5),
    )
    q_kelvin = units.convert_quantity(q_temp, "K")
    assert q_kelvin.unit == "K"
    assert q_kelvin.value == pytest.approx(310.15)
    assert q_kelvin.uncertainty.std == pytest.approx(0.5)
    assert q_kelvin.uncertainty.low == pytest.approx(309.65)
    assert q_kelvin.uncertainty.high == pytest.approx(310.65)
    q_cel_back = units.convert_quantity(q_kelvin, "Cel")
    assert q_cel_back.value == pytest.approx(37.0)
    assert q_cel_back.uncertainty.low == pytest.approx(36.5)

    # Time conversions for reaction & protocol durations
    assert units.convert(2.5, "h", "s") == pytest.approx(9000.0)
    assert units.convert(15.0, "min", "s") == pytest.approx(900.0)
    assert units.convert(120.0, "s", "min") == pytest.approx(2.0)


def test_sharealike_odbl_and_eval_only_export_gates(tmp_path):
    # 1. tdc_lipophilicity (CC-BY-SA-3.0) ShareAlike propagation
    lipo_rec = next(read_jsonl(ROOT / "samples" / "tdc_lipophilicity" / "records.jsonl"))
    ok, note = licenses.allowed(lipo_rec, "train_commercial")
    assert ok and "share-alike" in note

    pq_card = export_parquet([lipo_rec], tmp_path / "lipo.parquet", purpose="train_commercial")
    assert pq_card["n_records"] == 1
    assert "share-alike" in pq_card["license_notes"]["tdc_lipophilicity"]

    # 2. ehrsql_mimic_iv_demo (ODbL-1.0 + eval_only) blocks training & sample redistribution,
    #    allows RAG while propagating ODbL-1.0 ShareAlike notice
    ehr_dir = tmp_path / "ehrsql"
    ehr_dir.mkdir()
    (ehr_dir / "tables.json").write_text(
        json.dumps([{"table_names_original": ["patients", "admissions", "labevents", "d_labitems"]}]),
        encoding="utf-8",
    )
    (ehr_dir / "valid_data.json").write_text(
        json.dumps(
            {
                "data": [
                    {"id": "ehr1", "question": "What was the last serum creatinine lab value for patient 10001?"},
                    {"id": "ehr2", "question": "What is the patient's favorite hobby?"},
                ]
            }
        ),
        encoding="utf-8",
    )
    (ehr_dir / "valid_label.json").write_text(
        json.dumps(
            {
                "ehr1": "SELECT valuenum FROM labevents WHERE itemid = 50912 ORDER BY charttime DESC LIMIT 1",
                "ehr2": "null",
            }
        ),
        encoding="utf-8",
    )
    ehr_recs = list(connectors.get("ehrsql_mimic_iv_demo").convert(ehr_dir))
    assert len(ehr_recs) == 2
    assert ehr_recs[0].license == "ODbL-1.0"
    assert "eval_only" in ehr_recs[0].tags
    assert "SELECT valuenum" in ehr_recs[0].payload.answer
    assert ehr_recs[1].payload.answer == "ABSTAIN"
    assert "answerable:false" in ehr_recs[1].tags

    for blocked_purpose in ("train_research", "train_commercial", "redistribute_sample", "rag", "rag_research"):
        ok_gate, reason = licenses.allowed(ehr_recs[0], blocked_purpose)
        assert not ok_gate and "eval_only" in reason

    train_card = export_jsonl(ehr_recs, tmp_path / "train.jsonl", purpose="train_research")
    assert train_card["n_records"] == 0
    assert train_card["blocked"]

    comm_card = export_jsonl(ehr_recs, tmp_path / "comm.jsonl", purpose="train_commercial")
    assert comm_card["n_records"] == 0
    assert comm_card["blocked"]

    rag_blocked_card = export_rag_chunks(ehr_recs, tmp_path / "rag_blocked.jsonl", purpose="rag_research")
    assert rag_blocked_card["n_records"] == 0
    assert rag_blocked_card["contains_eval_items"] is False
    assert rag_blocked_card["blocked"]

    rag_card = export_rag_chunks(
        ehr_recs, tmp_path / "rag.jsonl", purpose="rag_research", allow_eval_in_rag=True
    )
    assert rag_card["n_records"] == 2
    assert rag_card["contains_eval_items"] is True
    assert rag_card["n_eval_items"] == 2
    assert "share-alike" in rag_card["license_notes"]["ehrsql_mimic_iv_demo"]


def test_protocols_io_parser_and_token_client_mock(tmp_path, monkeypatch):
    # 1. Draft.js entityMap + BioProt parser check
    draft_step = json.dumps(
        {
            "blocks": [
                {
                    "text": "Add   of   and incubate at 37 degC",
                    "entityRanges": [
                        {"key": 0, "offset": 4, "length": 1},
                        {"key": 1, "offset": 9, "length": 1},
                    ],
                }
            ],
            "entityMap": {
                "0": {"type": "amount", "data": {"amount": "20", "unit": 1}},
                "1": {"type": "reagents", "data": {"name": "Taq MasterMix"}},
            },
        }
    )
    bundle = {
        "id": 9901,
        "title": "Colony PCR Amplification",
        "uri": "colony-pcr-amplification-x1",
        "doi": "dx.doi.org/10.17504/protocols.io.x1",
        "steps": [{"id": 10, "guid": "G1", "duration": 45, "step": draft_step}],
    }
    recs = list(
        protocols_io_open.parse_protocol_bundle("protocols_io_open", "pio-test", "CC-BY-4.0", bundle)
    )
    assert [r.kind for r in recs] == ["protocol", "protocol_step"]
    step = recs[1]
    assert "20 uL" in step.payload.text and "Taq MasterMix" in step.payload.text
    assert step.payload.params["volume"].unit == "uL"
    assert step.payload.params["volume"].value == 20.0
    assert step.payload.params["duration"].unit == "s"
    assert step.payload.params["duration"].value == 45.0
    assert step.payload.params["temperature"].unit == "Cel"
    assert step.payload.params["temperature"].value == 37.0
    assert step.payload.entities == [{"type": "reagent", "text": "Taq MasterMix"}]
    kept, rep = quality.run_all(recs, purpose="train_commercial")
    assert len(kept) == 2 and not rep.failures

    # 2. Live API Bearer token client mock (PROTOCOLS_IO_ACCESS_TOKEN)
    calls = []

    class DummyResp:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_get(url, headers=None, timeout=None, params=None):
        calls.append((url, headers, params))
        if url.endswith("/v3/protocols"):
            return DummyResp(
                {
                    "items": [
                        {
                            "id": 4242,
                            "title": "Mocked Token PCR Protocol",
                            "uri": "mocked-token-pcr-4242",
                            "doi": "dx.doi.org/10.17504/protocols.io.4242",
                        }
                    ]
                }
            )
        if "/v4/protocols/4242/steps" in url:
            return DummyResp(
                {
                    "payload": [
                        {"id": 1, "guid": "S1", "duration": 30, "step": "Pipette 10 uL primer mix at 4 degC"},
                    ]
                }
            )
        raise AssertionError(f"unexpected URL {url}")

    monkeypatch.setenv("PROTOCOLS_IO_ACCESS_TOKEN", "pio-mock-bearer-2026")
    monkeypatch.delenv("PROTOCOLS_IO_TOKEN", raising=False)
    monkeypatch.setattr(protocols_io_open.requests, "get", fake_get)
    monkeypatch.setattr(protocols_io.requests, "get", fake_get)

    api_dir = tmp_path / "pio_api"
    conn_open = connectors.get("protocols_io_open")
    conn_open.fetch(api_dir, limit=1)
    assert any(h.get("Authorization") == "Bearer pio-mock-bearer-2026" for _, h, _ in calls)
    conv_recs = list(conn_open.convert(api_dir))
    assert len(conv_recs) == 2
    assert conv_recs[1].payload.params["volume"].unit == "uL"
    assert conv_recs[1].payload.params["duration"].unit == "s"
    assert conv_recs[1].payload.params["temperature"].unit == "Cel"

    # Also verify original protocols_io connector accepts PROTOCOLS_IO_ACCESS_TOKEN
    api_dir_orig = tmp_path / "pio_orig"
    connectors.get("protocols_io").fetch(api_dir_orig, limit=1)
    orig_recs = list(connectors.get("protocols_io").convert(api_dir_orig))
    assert len(orig_recs) == 2


def test_uspto_lowe_cml_and_50k_and_rgd1_structures_offline(tmp_path):
    assert strip_atom_mapping("[CH3:1][CH2:2][OH:3]") == "[CH3][CH2][OH]"

    # Syntheseus / USPTO-50K Parquet offline test
    df = pd.DataFrame(
        [
            {
                "id": "US08188092B2",
                "class": 3,
                "rxn_smiles": "[CH3:1]C(=O)O.CCO>>CCOC(C)=O",
                "temperature_K": 353.15,
                "duration_s": 3600.0,
                "yield": 88.5,
            }
        ]
    )
    df.to_parquet(tmp_path / "uspto_50k_mini.parquet", index=False)

    # Lowe CML XML offline test
    cml = """<?xml version="1.0" encoding="UTF-8"?>
    <reactionList>
      <reaction>
        <source><documentId>US04001234A</documentId></source>
        <reactantList>
          <reactant><molecule><identifier dictRef="cml:smiles" value=""/>
            <identifier dictRef="dl:smiles">c1ccccc1Br</identifier></molecule></reactant>
        </reactantList>
        <spectatorList>
          <spectator><molecule><identifier dictRef="dl:smiles">C1CCOC1</identifier></molecule></spectator>
        </spectatorList>
        <productList>
          <product>
            <molecule><identifier dictRef="dl:smiles">c1ccccc1O</identifier></molecule>
            <amount units="dl:percentYield">76.4</amount>
          </product>
        </productList>
        <parameterList>
          <parameter dictRef="cml:temp"><scalar units="cml:celsius">65.0</scalar></parameter>
          <parameter dictRef="cml:time"><scalar units="cml:hour">2.0</scalar></parameter>
        </parameterList>
      </reaction>
    </reactionList>
    """
    xml_path = tmp_path / "lowe_sample.xml"
    xml_path.write_text(cml, encoding="utf-8")
    parsed_cml = list(parse_cml_reactions(xml_path))
    assert len(parsed_cml) == 1
    assert parsed_cml[0]["yield_percent"].value == pytest.approx(76.4)
    assert parsed_cml[0]["temperature"].unit == "Cel"
    assert parsed_cml[0]["reaction_time"].unit == "s"
    assert parsed_cml[0]["reaction_time"].value == pytest.approx(7200.0)

    recs = list(connectors.get("uspto_lowe").convert(tmp_path))
    assert len(recs) == 2
    kept, rep = quality.run_all(recs, purpose="train_commercial")
    assert len(kept) == 2 and not rep.failures

    # RGD1 _structure_records offline check (works without requiring h5py in CI)
    class FakeDataset:
        def __init__(self, data):
            self._data = data

        def __getitem__(self, item):
            return self._data

    fake_h5_group = {
        "elements": FakeDataset([6, 1, 1, 1, 1]),
        "RG": FakeDataset([[0.0, 0.0, 0.0], [1.09, 0.0, 0.0], [-0.36, 1.03, 0.0], [-0.36, -0.51, 0.89], [-0.36, -0.51, -0.89]]),
        "TSG": FakeDataset([[0.0, 0.0, 0.0], [1.35, 0.0, 0.0], [-0.36, 1.03, 0.0], [-0.36, -0.51, 0.89], [-0.36, -0.51, -0.89]]),
        "PG": FakeDataset([[0.0, 0.0, 0.0], [2.50, 0.0, 0.0], [-0.36, 1.03, 0.0], [-0.36, -0.51, 0.89], [-0.36, -0.51, -0.89]]),
    }
    rgd1_conn = connectors.get("rgd1")
    s_recs = list(rgd1_conn._structure_records(fake_h5_group, "MR_1", "af:parent123"))
    assert [r.payload.role for r in s_recs] == ["reactant", "transition_state", "product"]
    assert all(r.parent_id == "af:parent123" and quality.validate(r) == [] for r in s_recs)
