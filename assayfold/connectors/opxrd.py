"""opXRD: Open Experimental Powder X-ray Diffraction Database (2-theta in deg). CC-BY-4.0."""

import json
import math
import zipfile
from pathlib import Path

from ..schema import Provenance, Quantity, Spectrum, new_record
from .base import Connector

URL = "https://zenodo.org/records/15298026/files/opxrd.zip?download=1"


def _loads_maybe(val):
    if isinstance(val, str):
        return json.loads(val)
    return val or {}


def parse_pattern(native_id: str, data: dict, source_id: str, dataset_id: str,
                  license_id: str, source_url: str):
    raw_x = data["two_theta_values"]
    raw_y = data["intensities"]
    pairs = [
        (round(float(x), 4), round(float(y), 4))
        for x, y in zip(raw_x, raw_y)
        if x is not None and y is not None and math.isfinite(float(x)) and math.isfinite(float(y))
    ]
    if not pairs:
        raise ValueError(f"empty PXRD pattern in {native_id}")
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    label = _loads_maybe(data.get("label"))
    meta = _loads_maybe(data.get("metadata"))
    xray = _loads_maybe(label.get("xray_info"))
    props = {
        "two_theta_min": Quantity(value=min(xs), unit="deg", raw_unit_str="deg 2-theta"),
        "two_theta_max": Quantity(value=max(xs), unit="deg", raw_unit_str="deg 2-theta"),
    }
    wl = xray.get("primary_wavelength")
    if wl is not None and str(wl).strip() != "":
        props["primary_wavelength"] = Quantity(
            value=float(wl), unit="Ao", raw_unit_str="Angstrom"
        )
    wl2 = xray.get("secondary_wavelength")
    if wl2 is not None and str(wl2).strip() != "":
        props["secondary_wavelength"] = Quantity(
            value=float(wl2), unit="Ao", raw_unit_str="Angstrom"
        )
    temp_k = label.get("temp_K")
    if temp_k is not None and str(temp_k).strip() != "":
        props["temperature"] = Quantity(value=float(temp_k), unit="K", raw_unit_str="K")
    cryst_nm = label.get("crystallite_size_nm")
    if cryst_nm is not None and str(cryst_nm).strip() != "":
        props["crystallite_size"] = Quantity(value=float(cryst_nm), unit="nm", raw_unit_str="nm")

    compositions = []
    for ph_raw in label.get("phases") or []:
        ph = _loads_maybe(ph_raw)
        comp = ph.get("chemical_composition")
        if comp:
            compositions.append(str(comp).strip())
    inst = (meta.get("institution") or native_id.split("/")[0]).strip()
    is_sim = bool(label.get("is_simulated", False))
    tags = [f"group:{native_id.split('/')[0]}"]
    for c in compositions:
        tags.append(f"phase:{c}")
    comp_str = ", ".join(compositions) if compositions else "experimental sample"
    return new_record(
        source_id,
        dataset_id,
        native_id,
        Spectrum(technique="PXRD", x_unit="deg", y_unit="{counts}", x=xs, y=ys),
        license=license_id,
        origin="simulated" if is_sim else "real",
        text=f"Powder XRD pattern {native_id} ({comp_str}; {inst})",
        properties=props,
        tags=tags,
        provenance=Provenance(source_url=source_url),
    )


class OpXRD(Connector):
    source_id = "opxrd"
    dataset_id = "opxrd-zenodo"
    dataset_version = "Zenodo record 15298026 (opxrd.zip)"
    dataset_url = "https://doi.org/10.5281/zenodo.15298026"

    def fetch(self, raw_dir=None, limit=12):
        from ..remote_zip import RangeFile

        d = Path(raw_dir or self.raw_dir())
        z = zipfile.ZipFile(RangeFile(URL))
        candidates = sorted(
            (n for n in z.namelist() if n.endswith(".json") and not n.endswith("/")),
            key=lambda n: (0 if n.startswith(("EMPA/", "HKUST/HKUST-A/")) else 1, n),
        )
        selected = candidates[: limit] if limit is not None else candidates
        for member in selected:
            out = d / member
            if not out.exists():
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(z.read(member))
        return d

    def is_partial(self, raw_dir=None):
        return True

    def convert(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        for i, p in enumerate(sorted(d.rglob("*.json"))):
            if limit is not None and i >= limit:
                break
            native_id = p.relative_to(d).as_posix()
            if native_id.endswith(".json"):
                native_id = native_id[:-5]
            data = json.loads(p.read_text(encoding="utf-8"))
            yield parse_pattern(
                native_id, data, self.source_id, self.dataset_id,
                self.source.license, self.dataset_url,
            )


CONNECTOR = OpXRD
