"""Wet Lab Protocols (WLP): 622 protocols with brat action/entity annotations. MIT."""

import io
import zipfile
from pathlib import Path

from ..schema import Protocol, ProtocolStep, Provenance, new_record
from .base import Connector, download

URL = "https://github.com/chaitanya2334/WLP-Dataset/archive/refs/heads/master.zip"


def parse_ann(text: str) -> list[dict]:
    """Read brat 'T' lines: id, type, start, end, surface text."""
    out = []
    for line in text.splitlines():
        if not line.startswith("T"):
            continue
        tid, mid, surface = line.split("\t")
        typ, span = mid.split(" ", 1)
        start, end = span.split(" ")[0], span.split(" ")[-1]
        out.append({"id": tid, "type": typ, "start": int(start), "end": int(end), "text": surface})
    return out


class WLP(Connector):
    source_id = "wlp"
    dataset_id = "wlp"
    dataset_version = "github master"
    dataset_url = "https://github.com/chaitanya2334/WLP-Dataset"

    def fetch(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        z = download(URL, d / "WLP-Dataset-master.zip")
        zipfile.ZipFile(z).extractall(d)
        return d

    def convert(self, raw_dir=None, limit=None):
        root = Path(raw_dir or self.raw_dir()) / "WLP-Dataset-master"
        files = sorted(root.glob("*/protocol_*.txt"), key=lambda p: (p.parent.name, int(p.stem.split("_")[1])))
        for k, txt in enumerate(files):
            if limit is not None and k >= limit:
                break
            yield from self._one(txt)

    def _one(self, txt: Path):
        text = txt.read_text(encoding="utf-8")
        ents = parse_ann(txt.with_suffix(".ann").read_text(encoding="utf-8"))
        native = f"{txt.parent.name}/{txt.stem}"
        lines, pos = [], 0
        for raw in io.StringIO(text).read().split("\n"):
            lines.append((pos, pos + len(raw), raw))
            pos += len(raw) + 1
        lines = [l for l in lines if l[2].strip()]
        title, steps = lines[0][2].strip(), lines[1:]
        prov = Provenance(source_url=f"{self.dataset_url}/blob/master/{native}.txt")
        parent = new_record(self.source_id, self.dataset_id, native,
                            Protocol(title=title, n_steps=len(steps), domain="wet lab biology"),
                            license=self.source.license, origin="real", text=title,
                            tags=[f"split:{txt.parent.name}"], provenance=prov)
        yield parent
        for i, (a, b, line) in enumerate(steps, start=1):
            spans = [{**e, "start": e["start"] - a, "end": e["end"] - a}
                     for e in ents if a <= e["start"] and e["end"] <= b]
            actions = [e["text"] for e in spans if e["type"] == "Action"]
            yield new_record(self.source_id, self.dataset_id, f"{native}#{i}",
                             ProtocolStep(index=i, text=line.strip(), entities=spans,
                                          action=actions[0].lower() if actions else None),
                             license=self.source.license, origin="real", text=line.strip(),
                             parent_id=parent.record_id, provenance=prov)


CONNECTOR = WLP
