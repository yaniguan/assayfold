"""RGD1: ~176k computed organic reactions (C, H, N, O) with DFT barriers. CC-BY-4.0.

Uses DFT_reaction_info.csv (B3LYP-D3/TZVP energies). Geometries live in RGD1_CHNO.h5
(1.3 GB), which is not fetched by default.
"""

import csv
from pathlib import Path

from ..schema import Provenance, Quantity, Reaction, new_record
from .base import Connector, download

URL = "https://ndownloader.figshare.com/files/40273231"   # DFT_reaction_info.csv
UNIT = "kcal/mol"  # CSV headers carry no unit; the paper reports these energies in kcal/mol
FIELDS = {"DE_F": "barrier_electronic_forward", "DE_B": "barrier_electronic_backward",
          "DG_F": "barrier_gibbs_forward", "DG_B": "barrier_gibbs_backward",
          "DH": "reaction_enthalpy"}


class RGD1(Connector):
    source_id = "rgd1"
    dataset_id = "rgd1-chno"
    dataset_version = "figshare doi:10.6084/m9.figshare.21066901.v9"
    dataset_url = "https://doi.org/10.6084/m9.figshare.21066901"

    def fetch(self, raw_dir=None, limit=None):
        # With a limit, read only the first 2 MB of the 33 MB CSV.
        return download(URL, Path(raw_dir or self.raw_dir()) / "DFT_reaction_info.csv",
                        max_bytes=2_000_000 if limit else None)

    def convert(self, raw_dir=None, limit=None):
        path = Path(raw_dir or self.raw_dir()) / "DFT_reaction_info.csv"
        n = 0
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                if limit is not None and n >= limit:
                    return
                try:
                    props = {name: Quantity(value=float(row[k]), unit=UNIT) for k, name in FIELDS.items()}
                except (TypeError, ValueError, KeyError):
                    continue          # a cut-off last line from a partial download
                payload = Reaction(reactants=row["reactant"].split("."), products=row["product"].split("."),
                                   reaction_smiles=f"{row['reactant']}>>{row['product']}")
                yield new_record(self.source_id, self.dataset_id, row["channel"], payload,
                                 license=self.source.license, origin="simulated",
                                 text=f"Computed reaction {row['channel']} ({row['type']}), B3LYP-D3/TZVP",
                                 properties=props, tags=[f"type:{row['type']}"],
                                 provenance=Provenance(source_url=self.dataset_url))
                n += 1


CONNECTOR = RGD1
