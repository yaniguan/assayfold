"""AstraZeneca ChEMBL3301361 octanol/water distribution coefficient (logD7.4). CC-BY-SA-3.0."""

from __future__ import annotations

import csv
from pathlib import Path

from ..schema import Molecule, Provenance, Quantity, new_record
from .base import Connector, download

URL = "https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/Lipophilicity.csv"
FILE = "Lipophilicity.csv"


class TDCLipophilicity(Connector):
    source_id = "tdc_lipophilicity"
    dataset_id = "chembl3301361-lipophilicity"
    dataset_version = "ChEMBL3301361 / MoleculeNet Lipophilicity.csv"
    dataset_url = "https://doi.org/10.6019/CHEMBL3301361"

    def fetch(self, raw_dir=None, limit=None):
        return download(URL, Path(raw_dir or self.raw_dir()) / FILE)

    def convert(self, raw_dir=None, limit=None):
        path = Path(raw_dir or self.raw_dir()) / FILE
        with open(path, newline="", encoding="utf-8") as f:
            for i, row in enumerate(csv.DictReader(f)):
                if limit is not None and i >= limit:
                    break
                chembl_id = row["CMPD_CHEMBLID"].strip()
                smi = row["smiles"].strip()
                logd = float(row["exp"])
                yield new_record(
                    self.source_id,
                    self.dataset_id,
                    chembl_id,
                    Molecule(smiles=smi, name=chembl_id),
                    license=self.source.license,
                    origin="real",
                    text=f"Experimental octanol/buffer logD7.4 of {chembl_id} at pH 7.4",
                    properties={
                        "logd_ph7_4": Quantity(value=logd, unit="[logD]", raw_unit_str="logD7.4"),
                        "ph": Quantity(value=7.4, unit="[pH]", raw_unit_str="pH"),
                    },
                    tags=[f"chembl:{chembl_id}", "assay:shake_flask_logD7.4"],
                    provenance=Provenance(source_url=self.dataset_url),
                )


CONNECTOR = TDCLipophilicity
