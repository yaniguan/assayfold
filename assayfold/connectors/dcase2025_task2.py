"""DCASE 2025 Task 2: machine anomalous sound detection WAV audio. CC-BY-NC-SA-4.0."""

import csv
import wave
import zipfile
from pathlib import Path

from ..canonical import file_sha256
from ..schema import BlobRef, Observation, Provenance, Quantity, new_record
from .base import Connector

MACHINES = ["valve", "fan", "bearing", "gearbox", "slider", "ToyCar", "ToyTrain"]
URL = "https://zenodo.org/records/15097779/files/dev_{m}.zip?download=1"


def _load_attributes(machine_dir: Path) -> dict[str, dict]:
    out = {}
    for p in sorted(machine_dir.glob("attributes_*.csv")):
        with open(p, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                fn = (row.get("file_name") or "").strip()
                if fn:
                    out[Path(fn).name] = row
    return out


class DCASE2025Task2(Connector):
    source_id = "dcase2025_task2"
    dataset_id = "dcase2025-task2-dev"
    dataset_version = "Zenodo record 15097779 (DCASE 2025 Task 2 Development Dataset)"
    dataset_url = "https://doi.org/10.5281/zenodo.15097779"
    machines = ["valve"]

    def fetch(self, raw_dir=None, limit=10):
        from ..remote_zip import RangeFile

        d = Path(raw_dir or self.raw_dir())
        n_per = limit or 10
        for m in self.machines:
            z = zipfile.ZipFile(RangeFile(URL.format(m=m)))
            for csv_member in [x for x in z.namelist() if x.endswith(".csv")]:
                out = d / csv_member
                if not out.exists():
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(z.read(csv_member))
            wavs = sorted(x for x in z.namelist() if x.endswith(".wav") and "/train/" in x)
            if not wavs:
                wavs = sorted(x for x in z.namelist() if x.endswith(".wav"))
            for member in wavs[:n_per]:
                out = d / member
                if not out.exists():
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(z.read(member))
        return d

    def is_partial(self, raw_dir=None):
        return True

    def convert(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        n = 0
        attrs_cache: dict[str, dict] = {}
        for wav_path in sorted(d.rglob("*.wav")):
            if limit is not None and n >= limit:
                break
            rel = wav_path.relative_to(d).as_posix()
            parts = rel.split("/")
            machine = parts[0] if len(parts) > 1 else "unknown"
            split = parts[1] if len(parts) > 2 else "train"
            if machine not in attrs_cache and (d / machine).is_dir():
                attrs_cache[machine] = _load_attributes(d / machine)
            with wave.open(str(wav_path), "rb") as wf:
                sr = wf.getframerate()
                nframes = wf.getnframes()
                nch = wf.getnchannels()
            duration_s = round(nframes / sr, 6) if sr > 0 else 0.0
            fname = wav_path.name
            cond = "anomaly" if "anomaly" in fname else ("normal" if "normal" in fname else "unlabeled")
            domain = "target" if "target" in fname else ("source" if "source" in fname else "supplemental")
            blob = BlobRef(
                sha256=file_sha256(wav_path),
                media_type="audio/wav",
                size_bytes=wav_path.stat().st_size,
                filename_orig=fname,
                url=f"{URL.format(m=machine)}#{rel}",
            )
            tags = [
                "non_commercial",
                f"machine:{machine}",
                f"split:{split}",
                f"domain:{domain}",
                f"condition:{cond}",
            ]
            if split == "test":
                tags.append("eval_only")
            attr_row = attrs_cache.get(machine, {}).get(fname)
            if attr_row and attr_row.get("d1p"):
                tags.append(f"attr:{attr_row['d1p']}={attr_row.get('d1v', '')}")
            yield new_record(
                self.source_id,
                self.dataset_id,
                rel.removesuffix(".wav"),
                Observation(
                    property="sample_rate",
                    value=Quantity(value=float(sr), unit="Hz", raw_unit_str="Hz"),
                    method="single-channel machine acoustic recording",
                ),
                license=self.source.license,
                origin="real",
                text=f"DCASE 2025 Task 2 {machine} ({split}, {domain}, {cond}): {fname}",
                properties={
                    "duration": Quantity(value=duration_s, unit="s", raw_unit_str="s"),
                    "channels": Quantity(value=float(nch), unit="1"),
                },
                blobs=[blob],
                tags=tags,
                provenance=Provenance(source_url=self.dataset_url),
            )
            n += 1


CONNECTOR = DCASE2025Task2
