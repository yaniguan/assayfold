"""Transition1x: DFT energies and forces on and around reaction pathways. MIT.

Read from the ColabFit Exchange copy on Hugging Face (colabfit/Transition1x-test; also
-train and -validation). ColabFit units: energy in eV, forces in eV/Angstrom, positions
in Angstrom.
"""

import json
from pathlib import Path

import pandas as pd

from ..schema import Provenance, Quantity, Structure, new_record
from .base import Connector, download

REPO = "colabfit/Transition1x-test"
ROWS = "https://datasets-server.huggingface.co/rows?dataset={r}&config=default&split=train&offset={o}&length={n}"
PARQUET = "https://huggingface.co/datasets/{r}/resolve/main/co/co_0.parquet"


def _arr(v):
    return json.loads(v) if isinstance(v, str) else (v.tolist() if hasattr(v, "tolist") else v)


class Transition1x(Connector):
    source_id = "transition1x"
    dataset_id = "transition1x-test"
    dataset_version = "ColabFit DS_zzfaosyakwom_0 (HF colabfit/Transition1x-test)"
    dataset_url = "https://doi.org/10.6084/m9.figshare.19614657.v4"

    def fetch(self, raw_dir=None, limit=None):
        """With a limit, page through the rows API; without one, download the Parquet file."""
        import requests
        d = Path(raw_dir or self.raw_dir())
        d.mkdir(parents=True, exist_ok=True)
        if limit is None:
            return download(PARQUET.format(r=REPO), d / "co_0.parquet")
        rows, offset = [], 0
        while offset < limit:
            n = min(100, limit - offset)
            r = requests.get(ROWS.format(r=REPO, o=offset, n=n), timeout=60)
            r.raise_for_status()
            rows += [x["row"] for x in r.json()["rows"]]
            offset += n
        (d / "rows.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
        return d

    def _rows(self, d: Path):
        if (d / "co_0.parquet").exists():
            yield from pd.read_parquet(d / "co_0.parquet").to_dict("records")
        else:
            with open(d / "rows.jsonl") as f:
                yield from (json.loads(line) for line in f)

    def convert(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        for k, row in enumerate(self._rows(d)):
            if limit is not None and k >= limit:
                break
            elements = [None, "H", None, None, None, None, "C", "N", "O", "F"]
            z = _arr(row["atomic_numbers"])
            names = str(row.get("names") or "")
            rxn = names.split("_")[0].strip("['\"") if "rxn" in names else None
            yield new_record(
                self.source_id, self.dataset_id, row["configuration_id"] + "/" + row["property_id"],
                Structure(elements=[elements[i] for i in z], coords_angstrom=_arr(row["positions"]),
                          multiplicity=int(row["multiplicity"]), forces=_arr(row["atomic_forces"]),
                          forces_unit="eV/Ao"),
                license=self.source.license, origin="simulated",
                text=f"Transition1x configuration {row['chemical_formula_hill']}"
                     + (f" from {rxn}" if rxn else "") + ", wB97x/6-31G(d)",
                properties={"energy": Quantity(value=float(row["energy"]), unit="eV")},
                tags=[t for t in [f"reaction:{rxn}" if rxn else None, f"software:{row['software']}"] if t],
                provenance=Provenance(source_url=f"https://huggingface.co/datasets/{REPO}"))


CONNECTOR = Transition1x
