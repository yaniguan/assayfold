"""Raman Open Database (ROD): CIF 2.0 mineral and crystal Raman spectra linked to COD. CC0-1.0."""

import re
from pathlib import Path

import requests

from ..schema import Provenance, Quantity, Spectrum, new_record
from .base import HEADERS, Connector, download

LIST_URL = "https://solsa.crystallography.net/rod/result.php?format=urls&limit={n}"
ENTRY_URL = "https://solsa.crystallography.net/rod/{rod_id}.rod"
DEFAULT_IDS = [str(1000000 + i) for i in range(1, 26)]


def _tag_value(text: str, tag: str) -> str | None:
    m = re.search(rf"(?m)^{re.escape(tag)}\s+('([^']*)'|\"([^\"]*)\"|(\S+))", text)
    if not m:
        return None
    val = m.group(2) if m.group(2) is not None else (m.group(3) if m.group(3) is not None else m.group(4))
    val = val.strip()
    return None if val in ("?", ".", "") else val


def parse_rod_cif(text: str) -> dict:
    """Extract metadata, COD cross-reference, and (raman_shift, intensity) arrays from a .rod CIF."""
    rod_id = _tag_value(text, "_rod_database.code")
    if not rod_id:
        m_data = re.search(r"(?m)^data_(\S+)", text)
        rod_id = m_data.group(1) if m_data else "unknown"
    mineral = _tag_value(text, "_chemical_name_mineral")
    systematic = _tag_value(text, "_chemical_name_systematic")
    formula = _tag_value(text, "_chemical_formula_sum") or _tag_value(text, "_chemical_formula_structural")
    method = (_tag_value(text, "_raman_determination_method") or "experimental").lower()
    laser_nm = _tag_value(text, "_raman_measurement_device.excitation_laser_wavelength")
    temp_k = _tag_value(text, "_raman_measurement.temperature")
    power_mw = _tag_value(text, "_raman_measurement_device.power_on_sample")

    cod_id = None
    m_cod = re.search(r"(?m)^\d+\s+(\d+)\s+COD\s+\S+", text)
    if m_cod:
        cod_id = m_cod.group(1)

    xs, ys = [], []
    lines = text.splitlines()
    in_spec = False
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s == "loop_":
            in_spec = False
            continue
        if s == "_raman_spectrum.intensity":
            in_spec = True
            continue
        if in_spec:
            if s.startswith("_") or s.startswith("data_") or s == ";":
                break
            parts = s.split()
            if len(parts) >= 2:
                try:
                    xs.append(round(float(parts[0]), 4))
                    ys.append(round(float(parts[1]), 4))
                except ValueError:
                    break
    return {
        "rod_id": rod_id,
        "mineral": mineral,
        "systematic": systematic,
        "formula": formula,
        "method": method,
        "laser_nm": laser_nm,
        "temp_k": temp_k,
        "power_mw": power_mw,
        "cod_id": cod_id,
        "x": xs,
        "y": ys,
    }


def _num_float(raw: str | None) -> float | None:
    if not raw:
        return None
    cleaned = re.sub(r"\([^)]*\)$", "", raw.strip())
    try:
        return float(cleaned)
    except ValueError:
        return None


class ROD(Connector):
    source_id = "rod"
    dataset_id = "rod-cif"
    dataset_version = "ROD CIF 2.0 (solsa.crystallography.net/rod)"
    dataset_url = "https://solsa.crystallography.net/rod/"

    def fetch(self, raw_dir=None, limit=12):
        d = Path(raw_dir or self.raw_dir())
        n_want = limit or 25
        try:
            r = requests.get(LIST_URL.format(n=max(n_want + 5, 20)), headers=HEADERS, timeout=30)
            r.raise_for_status()
            ids = [
                u.rsplit("/", 1)[-1].removesuffix(".rod")
                for u in r.text.splitlines()
                if u.strip().endswith(".rod")
            ]
        except requests.RequestException:
            ids = list(DEFAULT_IDS)
        ids = [i for i in ids if i != "1000000"][:n_want] or DEFAULT_IDS[:n_want]
        for rod_id in ids:
            download(ENTRY_URL.format(rod_id=rod_id), d / f"{rod_id}.rod")
        return d

    def is_partial(self, raw_dir=None):
        return True

    def convert(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        n = 0
        for p in sorted(d.glob("*.rod")):
            if limit is not None and n >= limit:
                break
            parsed = parse_rod_cif(p.read_text(encoding="utf-8", errors="replace"))
            if not parsed["x"]:
                continue
            props = {
                "raman_shift_min": Quantity(
                    value=min(parsed["x"]), unit="/cm", raw_unit_str="cm^-1"
                ),
                "raman_shift_max": Quantity(
                    value=max(parsed["x"]), unit="/cm", raw_unit_str="cm^-1"
                ),
            }
            wl = _num_float(parsed["laser_nm"])
            if wl is not None:
                props["laser_wavelength"] = Quantity(value=wl, unit="nm", raw_unit_str="nm")
            tk = _num_float(parsed["temp_k"])
            if tk is not None:
                props["temperature"] = Quantity(value=tk, unit="K", raw_unit_str="K")
            pw = _num_float(parsed["power_mw"])
            if pw is not None:
                props["laser_power"] = Quantity(value=pw, unit="mW", raw_unit_str="mW")

            tags = []
            if parsed["mineral"]:
                tags.append(f"mineral:{parsed['mineral']}")
            if parsed["formula"]:
                tags.append(f"formula:{parsed['formula'].replace(' ', '')}")
            if parsed["cod_id"]:
                tags.append(f"cod:{parsed['cod_id']}")
            label = parsed["mineral"] or parsed["systematic"] or parsed["formula"] or parsed["rod_id"]
            origin = "simulated" if parsed["method"] in ("theoretical", "calculated", "dft") else "real"
            rod_id = parsed["rod_id"]
            yield new_record(
                self.source_id,
                self.dataset_id,
                rod_id,
                Spectrum(
                    technique="Raman",
                    x_unit="/cm",
                    y_unit="{counts}",
                    x=parsed["x"],
                    y=parsed["y"],
                ),
                license=self.source.license,
                origin=origin,
                text=f"ROD Raman spectrum {rod_id}: {label}",
                properties=props,
                tags=tags,
                provenance=Provenance(source_url=ENTRY_URL.format(rod_id=rod_id)),
            )
            n += 1


CONNECTOR = ROD
