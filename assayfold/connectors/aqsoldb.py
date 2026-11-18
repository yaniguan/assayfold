"""AqSolDB: curated aqueous solubility (LogS, S in mol/L) for ~10k compounds. CC0-1.0."""

import csv

from ..schema import Molecule, Provenance, Quantity, Uncertainty, new_record
from .base import Connector, download

URL = "https://dataverse.harvard.edu/api/access/datafile/3407241?format=original"


class AqSolDB(Connector):
    source_id = "aqsoldb"
    dataset_id = "aqsoldb-curated"
    dataset_version = "Dataverse doi:10.7910/DVN/OVHAW8 (curated-solubility-dataset)"
    dataset_url = "https://doi.org/10.7910/DVN/OVHAW8"

    def fetch(self, raw_dir=None, limit=None):
        return download(URL, (raw_dir or self.raw_dir()) / "curated-solubility-dataset.csv")

    def convert(self, raw_dir=None, limit=None):
        path = (raw_dir or self.raw_dir()) / "curated-solubility-dataset.csv"
        with open(path, newline="") as f:
            for i, row in enumerate(csv.DictReader(f)):
                if limit is not None and i >= limit:
                    break
                sd = float(row["SD"])
                yield new_record(
                    self.source_id, self.dataset_id, row["ID"],
                    Molecule(smiles=row["SMILES"], name=row["Name"], inchikey=row["InChIKey"]),
                    license=self.source.license, origin="real",
                    text=f"Aqueous solubility of {row['Name']}",
                    properties={
                        "log_solubility": Quantity(
                            value=float(row["Solubility"]), unit="[logS]", raw_unit_str="LogS (mol/L)",
                            uncertainty=Uncertainty(kind="std", std=sd, n=int(row["Ocurrences"]),
                                                    method="std over merged sources")),
                        "mol_weight": Quantity(value=float(row["MolWt"]), unit="g/mol"),
                    },
                    tags=[f"reliability_group:{row['Group']}"],
                    provenance=Provenance(source_url=self.dataset_url),
                )


CONNECTOR = AqSolDB
