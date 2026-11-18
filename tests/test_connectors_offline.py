"""Converters tested on tiny inputs shaped like the real files (no network)."""

import json

from assayfold.connectors import get
from assayfold.connectors.bioprobench import to_qa
from assayfold.connectors.protocols_io import to_records
from assayfold.connectors.qm9 import read_sdf
from assayfold.connectors.wlp import parse_ann
from assayfold.quality import validate


def test_bioprobench_tasks_map_to_qa():
    pqa = to_qa("PQA", {"question": "Add ___ uL", "answer": "5", "choices": ["5", "10"], "id": "T"})
    err = to_qa("ERR", {"corrupted_text": "37 C, 10% CO2", "is_correct": False, "context": {}, "id": "T"})
    assert pqa.answer == "5" and err.answer == "incorrect"


def test_protocols_io_documented_shape():
    proto = {"id": 872, "title": "Lysis Buffer (20 mL)", "uri": "lysis-buffer-20-ml-c4gytv",
             "doi": "dx.doi.org/10.17504/protocols.io.c4gytv"}
    steps = [{"id": 1, "guid": "A", "step": "**Mix** 1 mL Tris"}, {"id": 2, "guid": "B", "step": "Spin"}]
    recs = list(to_records("protocols_io", "CC-BY-4.0", proto, steps))
    assert [r.kind for r in recs] == ["protocol", "protocol_step", "protocol_step"]
    assert recs[1].payload.text == "Mix 1 mL Tris" and recs[1].parent_id == recs[0].record_id
    assert all(validate(r) == [] for r in recs)


def test_wlp_ann_parser():
    ents = parse_ann("T1\tAction 0 5\tWeigh\nE1\tAction:T1\nT2\tAmount 6 12\t5.73 g\n")
    assert ents == [{"id": "T1", "type": "Action", "start": 0, "end": 5, "text": "Weigh"},
                    {"id": "T2", "type": "Amount", "start": 6, "end": 12, "text": "5.73 g"}]


def test_qm9_sdf_reader(tmp_path):
    sdf = ("gdb_1\n  -OEChem-\n\n  2  1  0     0  0  0  0  0  0999 V2000\n"
           "    0.0000    0.0000    0.0000 C   0  0\n    1.0900    0.0000    0.0000 H   0  0\n"
           "  1  2  1  0\nM  END\n$$$$\n")
    (tmp_path / "x.sdf").write_text(sdf)
    assert list(read_sdf(tmp_path / "x.sdf")) == [("gdb_1", ["C", "H"], [[0.0, 0.0, 0.0], [1.09, 0.0, 0.0]])]


def test_uspto_rows(tmp_path):
    (tmp_path / "x.rsmi").write_text(
        "ReactionSmiles\tPatentNumber\tParagraphNum\tYear\tTextMinedYield\tCalculatedYield\n"
        "CCO.CC(=O)O>[H+]>CCOC(C)=O |f:0.1|\tUS0001\t12\t1999\t85%\t\n")
    rec = next(get("uspto").convert(tmp_path))
    assert rec.payload.products == ["CCOC(C)=O"] and rec.payload.yield_percent.value == 85.0
    assert validate(rec) == []


def test_lab_bench_records_are_eval_only(tmp_path):
    import pandas as pd
    pd.DataFrame([{"id": "x", "question": "Q?", "ideal": "A", "distractors": ["B", "C"],
                   "protocol": "Step 1", "canary": "c", "source": None, "subtask": "s"}]
                 ).to_parquet(tmp_path / "ProtocolQA.parquet")
    rec = next(get("lab_bench").convert(tmp_path))
    assert "eval_only" in rec.tags and rec.payload.choices == ["A", "B", "C"]
