"""Benchtop Raman spectra of bioprocess analytes (Kaiser RXN1, 785 nm). CC-BY-4.0."""

from pathlib import Path

import pandas as pd

from ..schema import Provenance, Quantity, Spectrum, new_record
from .base import Connector, download

URL = "https://huggingface.co/datasets/chlange/RamanSpectraBioprocessAnalystesKaiser/resolve/main/{f}"
SPLITS = (("train", "train.parquet"), ("val", "val.parquet"), ("test", "test.parquet"))
TARGETS = {
    "Glucose": "glucose_concentration",
    "Acetate": "acetate_concentration",
    "MagnesiumSulfate": "magnesium_sulfate_concentration",
}


class RamanBioprocess(Connector):
    source_id = "raman_bioprocess"
    dataset_id = "raman-bioprocess-kaiser"
    dataset_version = "HF chlange/RamanSpectraBioprocessAnalystesKaiser main"
    dataset_url = "https://huggingface.co/datasets/chlange/RamanSpectraBioprocessAnalystesKaiser"

    def fetch(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        splits = SPLITS[:1] if limit is not None else SPLITS
        for _, fname in splits:
            download(URL.format(f=fname), d / fname)
        return d

    def is_partial(self, raw_dir=None):
        d = Path(raw_dir or self.raw_dir())
        return not all((d / fname).exists() for _, fname in SPLITS)

    def convert(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        n = 0
        for split, fname in SPLITS:
            p = d / fname
            if not p.exists():
                continue
            df = pd.read_parquet(p)
            spec_cols = [c for c in df.columns if c not in TARGETS]
            xs = [round(float(c), 2) for c in spec_cols]
            for idx, row in df.iterrows():
                if limit is not None and n >= limit:
                    return
                ys = [round(float(row[c]), 4) for c in spec_cols]
                props = {
                    "laser_wavelength": Quantity(value=785.0, unit="nm", raw_unit_str="nm"),
                    "exposure_time": Quantity(value=10.0, unit="s", raw_unit_str="s"),
                    "laser_power": Quantity(value=200.0, unit="mW", raw_unit_str="mW"),
                }
                for col, prop_name in TARGETS.items():
                    if col in row and pd.notna(row[col]):
                        props[prop_name] = Quantity(
                            value=round(float(row[col]), 6), unit="g/L", raw_unit_str="g/L"
                        )
                tags = [f"split:{split}", "instrument:Kaiser_RXN1"]
                if split == "test":
                    tags.append("eval_only")
                native_id = f"{split}_{idx}"
                yield new_record(
                    self.source_id,
                    self.dataset_id,
                    native_id,
                    Spectrum(technique="Raman", x_unit="/cm", y_unit="{counts}", x=xs, y=ys),
                    license=self.source.license,
                    origin="real",
                    text=(
                        f"Kaiser RXN1 785 nm Raman spectrum ({native_id}) of aqueous "
                        "glucose/acetate/MgSO4 bioprocess mixture"
                    ),
                    properties=props,
                    tags=tags,
                    provenance=Provenance(source_url=URL.format(f=fname)),
                )
                n += 1


CONNECTOR = RamanBioprocess
