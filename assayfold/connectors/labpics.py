"""LabPics Medical: lab photos with vessel and material segmentation. MIT (Zenodo).

The archive is 281 MB, so fetch() reads only the needed members over HTTP range requests.
Image bytes stay in data/raw; records keep a sha256 BlobRef and the annotation summary.
"""

import json
import zipfile
from pathlib import Path

from ..canonical import file_sha256
from ..schema import BlobRef, Image, Provenance, new_record
from .base import Connector

URL = "https://zenodo.org/records/4736111/files/LabPicsMedical.zip?download=1"
ROOT = "LabPics Medical"


def summarize(data: dict) -> list[dict]:
    """Keep the class names, flags and relations of each vessel and material instance."""
    out = []
    for group in ("Vessels", "MaterialsAndParts"):
        for idx, inst in sorted(data.get(group, {}).items(), key=lambda kv: int(kv[0])):
            out.append({"group": group, "index": int(idx), "classes": inst.get("All_ClassNames", []),
                        "mask": inst.get("MaskFilePath"),
                        "inside_vessels": inst.get("InsideOfVessels_Indx", []),
                        "content": inst.get("VesselContentMaterial_Indx", [])})
    return out


class LabPics(Connector):
    source_id = "labpics"
    dataset_id = "labpics-medical"
    dataset_version = "Zenodo record 4736111 (LabPicsMedical.zip)"
    dataset_url = "https://doi.org/10.5281/zenodo.4736111"

    def fetch(self, raw_dir=None, limit=20):
        from ..remote_zip import RangeFile
        d = Path(raw_dir or self.raw_dir())
        z = zipfile.ZipFile(RangeFile(URL))
        folders = sorted({"/".join(n.split("/")[1:3]) for n in z.namelist()
                          if n.split("/")[1] in ("Train", "Test") and n.endswith("/Data.json")})
        for folder in folders[: limit or len(folders)]:
            for name in ("Data.json", "Image.jpg"):
                out = d / folder / name
                if not out.exists():
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(z.read(f"{ROOT}/{folder}/{name}"))
        return d

    def convert(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        for k, data_json in enumerate(sorted(d.glob("*/*/Data.json"))):
            if limit is not None and k >= limit:
                break
            folder, img = data_json.parent, data_json.parent / "Image.jpg"
            native = f"{folder.parent.name}/{folder.name}"
            blob = BlobRef(sha256=file_sha256(img), media_type="image/jpeg",
                           size_bytes=img.stat().st_size, filename_orig="Image.jpg",
                           url=f"{URL}#{ROOT}/{native}/Image.jpg")
            ann = summarize(json.loads(data_json.read_text()))
            labels = sorted({c for a in ann for c in a["classes"]})
            yield new_record(self.source_id, self.dataset_id, native,
                             Image(blob=blob, annotations=ann), license=self.source.license,
                             origin="real", blobs=[blob],
                             text=f"Lab photo ({native}); labels: {', '.join(labels)}",
                             tags=[f"split:{folder.parent.name}"],
                             provenance=Provenance(source_url=self.dataset_url))


CONNECTOR = LabPics
