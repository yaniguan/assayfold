"""USPTO reactions text-mined from US patents, 1976-Sep 2016 (D. Lowe). CC0-1.0.

Reads the grants SMILES file (7z, ~75 MB) from figshare. Needs `pip install py7zr`.
The file is tab-separated with a header line; the columns are read by name.
"""

import csv
import io
from pathlib import Path

from ..schema import Provenance, Quantity, Reaction, new_record
from .base import Connector, download

URL = "https://ndownloader.figshare.com/files/8664379"   # 1976_Sep2016_USPTOgrants_smiles.7z


def parse_yield(text):
    try:
        return Quantity(value=float(str(text).strip().rstrip("%")), unit="%")
    except (TypeError, ValueError):
        return None


class USPTO(Connector):
    source_id = "uspto"
    dataset_id = "uspto-grants-1976-2016"
    dataset_version = "figshare doi:10.6084/m9.figshare.5104873.v1"
    dataset_url = "https://doi.org/10.6084/m9.figshare.5104873.v1"

    def fetch(self, raw_dir=None, limit=None):
        import py7zr
        d = Path(raw_dir or self.raw_dir())
        arc = download(URL, d / "1976_Sep2016_USPTOgrants_smiles.7z")
        if not list(d.glob("*.rsmi")):
            with py7zr.SevenZipFile(arc) as z:
                z.extractall(d)
        return d

    def convert(self, raw_dir=None, limit=None):
        path = sorted(Path(raw_dir or self.raw_dir()).glob("*.rsmi"))[0]
        with open(path, newline="", encoding="utf-8") as f:
            for i, row in enumerate(csv.DictReader(f, delimiter="\t")):
                if limit is not None and i >= limit:
                    break
                rsmi = row["ReactionSmiles"].split(" ")[0]
                reac, agents, prod = (rsmi.split(">") + ["", ""])[:3]
                yield new_record(
                    self.source_id, self.dataset_id, f"{row.get('PatentNumber')}#{row.get('ParagraphNum')}#{i}",
                    Reaction(reactants=[s for s in reac.split(".") if s], agents=[s for s in agents.split(".") if s],
                             products=[s for s in prod.split(".") if s], reaction_smiles=rsmi,
                             yield_percent=parse_yield(row.get("TextMinedYield"))),
                    license=self.source.license, origin="real",
                    text=f"Reaction from US patent {row.get('PatentNumber')} ({row.get('Year')})",
                    provenance=Provenance(source_url=self.dataset_url))


CONNECTOR = USPTO
