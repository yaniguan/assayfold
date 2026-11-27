"""Open FT-IR chemometrics spectra (olive oil, coffee, fresh meat) from Quadram Institute. CC0-1.0.

Reads mid-infrared ATR-FTIR and DRIFT absorbance spectra from the official QIBChemometrics
open repositories (Olive Oil geographic origin, Arabica/Robusta Coffee, and Chicken/Pork/Turkey
Fresh Meat), normalizing wavenumbers to `/cm` and absorbance to dimensionless `1`.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from ..schema import Provenance, Quantity, Spectrum, new_record
from .base import Connector, download

FILES = {
    "FTIR_Spectra_olive_oils.csv": (
        "https://raw.githubusercontent.com/QIBChemometrics/FTIR-Spectra-Olive-Oils/"
        "main/FTIR_Spectra_olive_oils.csv"
    ),
    "FreshMeatFTIR.csv": (
        "https://raw.githubusercontent.com/QIBChemometrics/fresh-meat-ftir/"
        "main/FreshMeatFTIR.csv"
    ),
    "FTIR_Library_Spectra.csv": (
        "https://raw.githubusercontent.com/QIBChemometrics/FTIR-food-library/"
        "main/FTIR_Library_Spectra.csv"
    ),
}


def _make_spectrum_record(
    source_id: str,
    dataset_id: str,
    native_id: str,
    label: str,
    matrix: str,
    xs: list[float],
    ys: list[float],
    license_id: str,
    source_url: str,
):
    return new_record(
        source_id,
        dataset_id,
        native_id,
        Spectrum(technique="FT-IR", x_unit="/cm", y_unit="1", x=xs, y=ys),
        license=license_id,
        origin="real",
        text=f"Mid-infrared FT-IR absorbance spectrum of {label} ({matrix})",
        properties={
            "wavenumber_min": Quantity(value=min(xs), unit="/cm", raw_unit_str="cm^-1"),
            "wavenumber_max": Quantity(value=max(xs), unit="/cm", raw_unit_str="cm^-1"),
        },
        tags=[f"matrix:{matrix}", f"sample_class:{label.lower().replace(' ', '_')[:40]}"],
        provenance=Provenance(source_url=source_url),
    )


def parse_olive_oil_csv(path: Path) -> list[tuple[str, str, str, list[float], list[float]]]:
    """Parse FTIR_Spectra_olive_oils.csv (rows 0-2: Sample Number, Group Code, Region)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    sample_nums = rows[0][1:]
    regions = rows[2][1:]
    n_cols = len(regions)
    xs: list[float] = []
    y_cols: list[list[float]] = [[] for _ in range(n_cols)]
    for r in rows[3:]:
        if not r or not r[0].strip():
            continue
        wn = round(float(r[0]), 4)
        xs.append(wn)
        for j in range(n_cols):
            y_cols[j].append(round(float(r[j + 1]), 6))
    out = []
    seen_rep: dict[str, int] = {}
    for j in range(n_cols):
        snum = sample_nums[j].strip()
        seen_rep[snum] = seen_rep.get(snum, 0) + 1
        region = regions[j].strip()
        nid = f"olive_oil_{region.lower()}_s{snum}_r{seen_rep[snum]}"
        out.append((nid, f"extra virgin olive oil ({region})", "olive_oil", xs, y_cols[j]))
    return out


def parse_fresh_meat_csv(path: Path) -> list[tuple[str, str, str, list[float], list[float]]]:
    """Parse FreshMeatFTIR.csv (header row has sample descriptors, col 0 has wavenumbers)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    headers = [h.strip() for h in rows[0][1:]]
    n_cols = len(headers)
    xs: list[float] = []
    y_cols: list[list[float]] = [[] for _ in range(n_cols)]
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        xs.append(round(float(r[0]), 4))
        for j in range(n_cols):
            y_cols[j].append(round(float(r[j + 1]), 6))
    out = []
    for j, hdr in enumerate(headers):
        species = hdr.split("_")[0].replace("Fresh", "").strip() or "Meat"
        nid = f"meat_{hdr.lower()}_{j}"
        out.append((nid, f"fresh {species.lower()} ({hdr})", "fresh_meat", xs, y_cols[j]))
    return out


def parse_food_library_coffee_csv(
    path: Path,
) -> list[tuple[str, str, str, list[float], list[float]]]:
    """Extract Coffee FT-IR spectra from FTIR_Library_Spectra.csv (paired wavenumber/absorbance cols)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    hdr = rows[0]
    out = []
    for col in range(0, len(hdr) - 1, 2):
        desc = hdr[col + 1].strip()
        if "coffee" not in desc.lower() and "caffeine" not in desc.lower():
            continue
        xs, ys = [], []
        for r in rows[1:]:
            if col + 1 >= len(r):
                continue
            sx, sy = r[col].strip(), r[col + 1].strip()
            if not sx or not sy:
                continue
            vx, vy = float(sx), float(sy)
            if math.isfinite(vx) and math.isfinite(vy):
                xs.append(round(vx, 4))
                ys.append(round(vy, 6))
        if xs:
            nid = f"coffee_col{col}_{desc.lower().split('(')[0].strip().replace(' ', '_').replace('-', '_')}"
            nid = nid.strip("_")
            out.append((nid, desc, "coffee", xs, ys))
    return out


class UCRFTIRChemometrics(Connector):
    source_id = "ucr_ftir_chemometrics"
    dataset_id = "qib-ftir-chemometrics"
    dataset_version = "QIBChemometrics main (olive oil, coffee, fresh meat)"
    dataset_url = "https://github.com/QIBChemometrics/FTIR-food-library"

    def fetch(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        for fname, url in FILES.items():
            download(url, d / fname)
        return d

    def convert(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        olive = (
            parse_olive_oil_csv(d / "FTIR_Spectra_olive_oils.csv")
            if (d / "FTIR_Spectra_olive_oils.csv").exists()
            else []
        )
        coffee = (
            parse_food_library_coffee_csv(d / "FTIR_Library_Spectra.csv")
            if (d / "FTIR_Library_Spectra.csv").exists()
            else []
        )
        meat = (
            parse_fresh_meat_csv(d / "FreshMeatFTIR.csv")
            if (d / "FreshMeatFTIR.csv").exists()
            else []
        )

        # Interleave distinct geographic origins / coffee varieties / meat species first
        # so a small sample (--limit 10) covers olive oil, coffee, and chicken/pork/turkey.
        olive_reps = [x for i, x in enumerate(olive) if i in (0, 20, 54, 70)]
        meat_reps = [x for i, x in enumerate(meat) if i in (0, 40, 80)]
        featured = olive_reps + coffee[:4] + meat_reps
        seen = {x[0] for x in featured}
        ordered = featured + [x for x in (olive + coffee + meat) if x[0] not in seen]

        for idx, (nid, label, matrix, xs, ys) in enumerate(ordered):
            if limit is not None and idx >= limit:
                return
            src_file = (
                "FTIR_Spectra_olive_oils.csv"
                if matrix == "olive_oil"
                else ("FTIR_Library_Spectra.csv" if matrix == "coffee" else "FreshMeatFTIR.csv")
            )
            yield _make_spectrum_record(
                self.source_id,
                self.dataset_id,
                nid,
                label,
                matrix,
                xs,
                ys,
                self.source.license,
                FILES[src_file],
            )


CONNECTOR = UCRFTIRChemometrics
