"""FreeSolv: experimental and calculated hydration free energies (kcal/mol). CC-BY-4.0."""

import json

from ..schema import Molecule, Provenance, Quantity, Uncertainty, new_record
from .base import Connector, download

URL = "https://raw.githubusercontent.com/MobleyLab/FreeSolv/master/database.json"


def _q(value, err, method):
    return Quantity(value=value, unit="kcal/mol",
                    uncertainty=Uncertainty(kind="std", std=err, method=method))


class FreeSolv(Connector):
    source_id = "freesolv"
    dataset_id = "freesolv"
    dataset_version = "github master database.json"
    dataset_url = "https://github.com/MobleyLab/FreeSolv"

    def fetch(self, raw_dir=None, limit=None):
        return download(URL, (raw_dir or self.raw_dir()) / "database.json")

    def convert(self, raw_dir=None, limit=None):
        data = json.loads(((raw_dir or self.raw_dir()) / "database.json").read_text())
        for i, key in enumerate(sorted(data)):
            if limit is not None and i >= limit:
                break
            d = data[key]
            yield new_record(
                self.source_id, self.dataset_id, key,
                Molecule(smiles=d["smiles"], name=d["iupac"].strip()),
                license=self.source.license, origin="real",
                text=f"Hydration free energy of {d['iupac'].strip()} in water",
                properties={
                    "hydration_free_energy_expt": _q(d["expt"], d["d_expt"], "experimental, as curated"),
                    "hydration_free_energy_calc": _q(d["calc"], d["d_calc"], "GAFF/TIP3P alchemical (calc)"),
                },
                tags=[f"expt_ref:{d['expt_reference']}"],
                provenance=Provenance(source_url=self.dataset_url),
            )


CONNECTOR = FreeSolv
