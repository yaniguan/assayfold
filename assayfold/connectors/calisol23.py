"""CALiSol-23: experimental non-aqueous Li-ion electrolyte conductivities (mS/cm). CC-BY-4.0."""

import csv
from pathlib import Path

from .. import units
from ..schema import Observation, Provenance, Quantity, new_record
from .base import Connector, download

URL = "https://ndownloader.figshare.com/files/43151344"
FILE = "calisol23_DOI_10.11583DTU.c.6929599.csv"
META_COLS = {"", "id", "doi", "k", "T", "c", "salt", "c units", "solvent ratio type"}


class CALiSol23(Connector):
    source_id = "calisol23"
    dataset_id = "calisol-23"
    dataset_version = "DTU Data doi:10.11583/DTU.24559960.v1"
    dataset_url = "https://doi.org/10.11583/DTU.24559960.v1"

    def fetch(self, raw_dir=None, limit=None):
        return download(URL, Path(raw_dir or self.raw_dir()) / FILE)

    def convert(self, raw_dir=None, limit=None):
        path = Path(raw_dir or self.raw_dir()) / FILE
        with open(path, newline="", encoding="utf-8") as f:
            for i, row in enumerate(csv.DictReader(f)):
                if limit is not None and i >= limit:
                    break
                native_id = (row.get("") or row.get("id") or str(i)).strip()
                salt = row["salt"].strip()
                c_raw = (row.get("c units") or "mol/kg").strip()
                c_unit = units.to_code(c_raw)
                ratio_type = (row.get("solvent ratio type") or "w").strip()
                solvents = []
                for col, val in row.items():
                    if col in META_COLS or val is None or str(val).strip() == "":
                        continue
                    frac = float(val)
                    if frac > 0.0:
                        solvents.append(f"{col}:{frac:g}")
                doi = (row.get("doi") or "").strip()
                src_url = f"https://doi.org/{doi}" if doi else self.dataset_url
                solv_desc = ", ".join(solvents) if solvents else "neat"
                yield new_record(
                    self.source_id,
                    self.dataset_id,
                    native_id,
                    Observation(
                        property="ionic_conductivity",
                        value=Quantity(value=float(row["k"]), unit="mS/cm", raw_unit_str="mS/cm"),
                        method="experimental",
                    ),
                    license=self.source.license,
                    origin="real",
                    text=f"Ionic conductivity of {salt} in {solv_desc} ({ratio_type})",
                    properties={
                        "temperature": Quantity(value=float(row["T"]), unit="K", raw_unit_str="K"),
                        "salt_concentration": Quantity(
                            value=float(row["c"]), unit=c_unit, raw_unit_str=c_raw
                        ),
                    },
                    tags=[f"salt:{salt}", f"solvent_ratio_type:{ratio_type}"],
                    provenance=Provenance(source_url=src_url),
                )


CONNECTOR = CALiSol23
