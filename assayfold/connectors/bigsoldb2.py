"""BigSolDB 2.0: multi-solvent, temperature-dependent organic solubility. CC-BY-4.0."""

import csv
import sys
from pathlib import Path

from ..quality import smiles_ok
from ..schema import Observation, Provenance, Quantity, new_record
from .base import Connector, download, partial_path

URL = "https://zenodo.org/api/records/15094979/files/BigSolDBv2.0.csv/content"
FILE = "BigSolDBv2.0.csv"
HEAD_BYTES = 1_500_000


class BigSolDB2(Connector):
    source_id = "bigsoldb2"
    dataset_id = "bigsoldb-v2.0"
    dataset_version = "Zenodo doi:10.5281/zenodo.15094979 (BigSolDBv2.0.csv)"
    dataset_url = "https://doi.org/10.5281/zenodo.15094979"

    def fetch(self, raw_dir=None, limit=None):
        full = Path(raw_dir or self.raw_dir()) / FILE
        if limit is None or full.exists():
            return download(URL, full)
        return download(URL, full, max_bytes=HEAD_BYTES)

    def csv_path(self, raw_dir=None) -> Path:
        full = Path(raw_dir or self.raw_dir()) / FILE
        return full if full.exists() else partial_path(full, HEAD_BYTES)

    def raw_files(self, raw_dir=None):
        return [self.csv_path(raw_dir)]

    def is_partial(self, raw_dir=None):
        return self.csv_path(raw_dir).name != FILE

    def _record(self, idx: int, row: dict):
        solute_smi = row["SMILES_Solute"].strip()
        solvent_smi = (row.get("SMILES_Solvent") or "").strip()
        if not smiles_ok(solute_smi):
            raise ValueError(f"invalid solute SMILES {solute_smi!r}")
        if solvent_smi and not smiles_ok(solvent_smi):
            raise ValueError(f"invalid solvent SMILES {solvent_smi!r}")
        temp_k = float(row["Temperature_K"])
        mole_frac = float(row["Solubility(mole_fraction)"])
        props = {
            "temperature": Quantity(value=temp_k, unit="K", raw_unit_str="K"),
            "solubility_mole_fraction": Quantity(
                value=mole_frac, unit="1", raw_unit_str="mole_fraction"
            ),
        }
        mol_l_raw = (row.get("Solubility(mol/L)") or "").strip()
        if mol_l_raw:
            props["solubility_molar"] = Quantity(
                value=float(mol_l_raw), unit="mol/L", raw_unit_str="mol/L"
            )
        logs_raw = (row.get("LogS(mol/L)") or "").strip()
        if logs_raw:
            obs = Observation(
                property="log_solubility",
                value=Quantity(value=float(logs_raw), unit="[logS]", raw_unit_str="LogS(mol/L)"),
                method="experimental",
            )
        else:
            obs = Observation(
                property="solubility_mole_fraction",
                value=Quantity(value=mole_frac, unit="1", raw_unit_str="mole_fraction"),
                method="experimental",
            )
        name = (row.get("Compound_Name") or solute_smi).strip()
        solvent = (row.get("Solvent") or "unknown").strip()
        doi = (row.get("Source") or "").strip()
        src_url = f"https://doi.org/{doi}" if doi and doi.startswith("10.") else self.dataset_url
        tags = [f"solvent:{solvent}", f"solute_smiles:{solute_smi}"]
        if solvent_smi:
            tags.append(f"solvent_smiles:{solvent_smi}")
        return new_record(
            self.source_id,
            self.dataset_id,
            f"row_{idx}",
            obs,
            license=self.source.license,
            origin="real",
            text=f"Solubility of {name} ({solute_smi}) in {solvent} at {temp_k} K",
            properties=props,
            tags=tags,
            provenance=Provenance(source_url=src_url),
        )

    def convert(self, raw_dir=None, limit=None):
        path, partial = self.csv_path(raw_dir), self.is_partial(raw_dir)
        self.skipped_rows, n = 0, 0
        with open(path, "rb") as fb:
            fb.seek(0, 2)
            ends_with_newline = fb.tell() == 0 or (fb.seek(-1, 2) or fb.read(1) == b"\n")
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader, None)
            idx = 0
            while row is not None:
                line, nxt = reader.line_num, next(reader, None)
                last = nxt is None
                if limit is not None and n >= limit:
                    return
                try:
                    rec = self._record(idx, row)
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    if not last:
                        raise ValueError(
                            f"{path.name} line {line}: malformed row ({e!r})"
                        ) from e
                    rec = None
                if rec is None or (last and partial and not ends_with_newline):
                    self.skipped_rows += 1
                    print(f"bigsoldb2: skipped last row of {path.name} (line {line})", file=sys.stderr)
                else:
                    yield rec
                    n += 1
                idx += 1
                row = nxt


CONNECTOR = BigSolDB2
