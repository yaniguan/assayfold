"""QM9: 133,885 small organic molecules (C, H, O, N, F) with DFT properties. CC0-1.0.

Reads the MoleculeNet mirror of QM9 (gdb9.tar.gz: gdb9.sdf with 3D coordinates and
gdb9.sdf.csv with properties). Units follow the QM9 paper: energies in Hartree.
"""

import csv
import tarfile
from pathlib import Path

from ..schema import Provenance, Quantity, Structure, new_record
from .base import Connector, download

URL = "https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/gdb9.tar.gz"
OFFICIAL = "https://doi.org/10.6084/m9.figshare.c.978904.v5"
UNITS = {"A": "GHz", "B": "GHz", "C": "GHz", "mu": "[D]", "alpha": "[a0]3", "homo": "[Eh]",
         "lumo": "[Eh]", "gap": "[Eh]", "r2": "[a0]2", "zpve": "[Eh]", "u0": "[Eh]",
         "u298": "[Eh]", "h298": "[Eh]", "g298": "[Eh]", "cv": "cal/(mol.K)"}


def read_sdf(path: Path):
    """Yield (name, elements, coords) from a V2000 SDF file. No external parser needed."""
    with open(path) as f:
        while True:
            name = f.readline()
            if not name:
                return
            f.readline(), f.readline()
            counts = f.readline()
            n_atoms = int(counts[:3])
            elements, coords = [], []
            for _ in range(n_atoms):
                parts = f.readline().split()
                coords.append([float(parts[0]), float(parts[1]), float(parts[2])])
                elements.append(parts[3])
            for line in f:
                if line.startswith("$$$$"):
                    break
            yield name.strip(), elements, coords


class QM9(Connector):
    source_id = "qm9"
    dataset_id = "qm9"
    dataset_version = "MoleculeNet mirror gdb9.tar.gz (QM9 v5 collection)"
    dataset_url = OFFICIAL

    def fetch(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        tgz = download(URL, d / "gdb9.tar.gz")
        if not (d / "gdb9.sdf").exists():
            with tarfile.open(tgz) as t:
                t.extractall(d, filter="data")
        return d

    def convert(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        with open(d / "gdb9.sdf.csv", newline="") as f:
            props = {}
            for i, row in enumerate(csv.DictReader(f)):
                if limit is not None and i >= limit:
                    break
                props[row["mol_id"]] = row
        for name, elements, coords in read_sdf(d / "gdb9.sdf"):
            if name not in props:
                continue
            row = props.pop(name)
            yield new_record(
                self.source_id, self.dataset_id, name,
                Structure(elements=elements, coords_angstrom=coords),
                license=self.source.license, origin="simulated",
                text=f"QM9 molecule {name}, {len(elements)} atoms, B3LYP/6-31G(2df,p)",
                properties={k: Quantity(value=float(row[k]), unit=u) for k, u in UNITS.items()},
                provenance=Provenance(source_url=URL))
            if limit is not None and not props:
                break


CONNECTOR = QM9
