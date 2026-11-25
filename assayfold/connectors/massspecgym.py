"""MassSpecGym: experimental MS/MS tandem mass spectra for molecular discovery. MIT."""

import csv
import math
import sys
from pathlib import Path

from ..quality import smiles_ok
from ..schema import Provenance, Quantity, Spectrum, new_record
from .base import Connector, download, partial_path

URL = "https://huggingface.co/datasets/roman-bushuiev/MassSpecGym/resolve/main/data/MassSpecGym.tsv"
FILE = "MassSpecGym.tsv"
HEAD_BYTES = 1_000_000


class MassSpecGym(Connector):
    source_id = "massspecgym"
    dataset_id = "massspecgym-v1"
    dataset_version = "HF roman-bushuiev/MassSpecGym main (data/MassSpecGym.tsv)"
    dataset_url = "https://huggingface.co/datasets/roman-bushuiev/MassSpecGym"

    def fetch(self, raw_dir=None, limit=None):
        full = Path(raw_dir or self.raw_dir()) / FILE
        if limit is None or full.exists():
            return download(URL, full)
        return download(URL, full, max_bytes=HEAD_BYTES)

    def tsv_path(self, raw_dir=None) -> Path:
        full = Path(raw_dir or self.raw_dir()) / FILE
        return full if full.exists() else partial_path(full, HEAD_BYTES)

    def raw_files(self, raw_dir=None):
        return [self.tsv_path(raw_dir)]

    def is_partial(self, raw_dir=None):
        return self.tsv_path(raw_dir).name != FILE

    def _record(self, row: dict):
        smi = (row.get("smiles") or "").strip()
        if smi and not smiles_ok(smi):
            raise ValueError(f"invalid SMILES {smi!r}")
        mzs = [float(v) for v in row["mzs"].split(",") if v.strip()]
        intensities = [float(v) for v in row["intensities"].split(",") if v.strip()]
        if not mzs or len(mzs) != len(intensities):
            raise ValueError("empty or mismatched m/z and intensity arrays")
        props = {
            "precursor_mz": Quantity(
                value=float(row["precursor_mz"]), unit="[m/z]", raw_unit_str="m/z"
            ),
        }
        pm_raw = (row.get("parent_mass") or "").strip()
        if pm_raw:
            pm = float(pm_raw)
            if math.isfinite(pm):
                props["parent_mass"] = Quantity(value=pm, unit="g/mol", raw_unit_str="Da")
        ce_raw = (row.get("collision_energy") or "").strip()
        if ce_raw:
            try:
                ce = float(ce_raw)
                if math.isfinite(ce):
                    props["collision_energy"] = Quantity(value=ce, unit="eV", raw_unit_str="eV")
            except ValueError:
                pass
        fold = (row.get("fold") or "train").strip()
        adduct = (row.get("adduct") or "").strip()
        inchikey = (row.get("inchikey") or "").strip()
        inst = (row.get("instrument_type") or "").strip()
        tags = [f"split:{fold}"]
        if adduct:
            tags.append(f"adduct:{adduct}")
        if inst:
            tags.append(f"instrument:{inst}")
        if inchikey:
            tags.append(f"inchikey:{inchikey}")
        if smi:
            tags.append(f"smiles:{smi}")
        if fold == "test":
            tags.append("eval_only")
        formula = (row.get("formula") or smi or row["identifier"]).strip()
        return new_record(
            self.source_id,
            self.dataset_id,
            row["identifier"].strip(),
            Spectrum(technique="MS/MS", x_unit="[m/z]", y_unit="1", x=mzs, y=intensities),
            license=self.source.license,
            origin="real",
            text=f"MS/MS spectrum {row['identifier'].strip()} ({formula}, {adduct})",
            properties=props,
            tags=tags,
            provenance=Provenance(source_url=self.dataset_url),
        )

    def convert(self, raw_dir=None, limit=None):
        path, partial = self.tsv_path(raw_dir), self.is_partial(raw_dir)
        self.skipped_rows, n = 0, 0
        with open(path, "rb") as fb:
            fb.seek(0, 2)
            ends_with_newline = fb.tell() == 0 or (fb.seek(-1, 2) or fb.read(1) == b"\n")
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            row = next(reader, None)
            while row is not None:
                line, nxt = reader.line_num, next(reader, None)
                last = nxt is None
                if limit is not None and n >= limit:
                    return
                try:
                    rec = self._record(row)
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    if not last:
                        raise ValueError(
                            f"{path.name} line {line}: malformed row ({e!r})"
                        ) from e
                    rec = None
                if rec is None or (last and partial and not ends_with_newline):
                    self.skipped_rows += 1
                    print(f"massspecgym: skipped last row of {path.name} (line {line})", file=sys.stderr)
                else:
                    yield rec
                    n += 1
                row = nxt


CONNECTOR = MassSpecGym
