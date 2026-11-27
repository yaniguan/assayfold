"""LabPics Chemistry: chemistry lab photos with vessel, phase, and apparatus segmentation. MIT.

Reads only requested scene folders from the 3.9 GB Zenodo ZIP over HTTP range requests.
Raw image bytes remain in gitignored data/raw/; unified records store SHA-256 BlobRefs and
structured vessel/material/phase segmentation summaries.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from ..canonical import file_sha256
from ..schema import BlobRef, Image, Provenance, new_record
from .base import Connector
from .labpics import summarize

URL = "https://zenodo.org/records/4736111/files/LabPicsChemistry.zip?download=1"
ARCHIVE_ROOT = "LabPics Chemistry"


class LabPicsChemistry(Connector):
    source_id = "labpics_chemistry"
    dataset_id = "labpics-chemistry"
    dataset_version = "Zenodo record 4736111 (LabPicsChemistry.zip)"
    dataset_url = "https://doi.org/10.5281/zenodo.4736111"

    def fetch(self, raw_dir=None, limit=10):
        from ..remote_zip import RangeFile

        d = Path(raw_dir or self.raw_dir())
        z = zipfile.ZipFile(RangeFile(URL))
        folders = sorted(
            {
                "/".join(n.split("/")[1:3])
                for n in z.namelist()
                if len(n.split("/")) >= 4
                and n.split("/")[0] == ARCHIVE_ROOT
                and n.split("/")[1] in ("Train", "Test")
                and n.endswith("/Data.json")
            }
        )
        for folder in folders[: limit or len(folders)]:
            for name in ("Data.json", "Image.jpg"):
                out = d / folder / name
                if not out.exists():
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(z.read(f"{ARCHIVE_ROOT}/{folder}/{name}"))
        return d

    def is_partial(self, raw_dir=None):
        return True

    def convert(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        for k, data_json in enumerate(sorted(d.glob("*/*/Data.json"))):
            if limit is not None and k >= limit:
                break
            folder, img = data_json.parent, data_json.parent / "Image.jpg"
            native = f"{folder.parent.name}/{folder.name}"
            blob = BlobRef(
                sha256=file_sha256(img),
                media_type="image/jpeg",
                size_bytes=img.stat().st_size,
                filename_orig="Image.jpg",
                url=f"{URL}#{ARCHIVE_ROOT}/{native}/Image.jpg",
            )
            ann = summarize(json.loads(data_json.read_text(encoding="utf-8")))
            labels = sorted({c for a in ann for c in a["classes"]})
            yield new_record(
                self.source_id,
                self.dataset_id,
                native,
                Image(blob=blob, annotations=ann),
                license=self.source.license,
                origin="real",
                blobs=[blob],
                text=f"Chemistry lab scene ({native}); labels: {', '.join(labels)}",
                tags=[f"split:{folder.parent.name}"],
                provenance=Provenance(source_url=self.dataset_url),
            )


CONNECTOR = LabPicsChemistry
