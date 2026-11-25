"""RGD1: ~176k computed organic reactions (C, H, N, O) with DFT barriers. CC-BY-4.0.

Uses DFT_reaction_info.csv (B3LYP-D3/TZVP energies). Geometries live in RGD1_CHNO.h5
(1.3 GB), which is not fetched by default.
"""

import csv
import sys
from pathlib import Path

from ..schema import Provenance, Quantity, Reaction, new_record
from .base import Connector, download, partial_path

URL = "https://ndownloader.figshare.com/files/40273231"   # DFT_reaction_info.csv
FILE = "DFT_reaction_info.csv"
HEAD_BYTES = 2_000_000     # with a limit, read only the head of the 33 MB CSV
UNIT = "kcal/mol"  # CSV headers carry no unit; the paper reports these energies in kcal/mol
FIELDS = {"DE_F": "barrier_electronic_forward", "DE_B": "barrier_electronic_backward",
          "DG_F": "barrier_gibbs_forward", "DG_B": "barrier_gibbs_backward",
          "DH": "reaction_enthalpy"}


class RGD1(Connector):
    source_id = "rgd1"
    dataset_id = "rgd1-chno"
    dataset_version = "figshare doi:10.6084/m9.figshare.21066901.v9"
    dataset_url = "https://doi.org/10.6084/m9.figshare.21066901"

    def fetch(self, raw_dir=None, limit=None):
        # With a limit, keep only the head of the CSV, stored as DFT_reaction_info.head2000000.csv
        # so that a later fetch without a limit still downloads the full file.
        full = Path(raw_dir or self.raw_dir()) / FILE
        if limit is None or full.exists():
            return download(URL, full)
        return download(URL, full, max_bytes=HEAD_BYTES)

    def csv_path(self, raw_dir=None) -> Path:
        """The full CSV when present, otherwise the head-only read."""
        full = Path(raw_dir or self.raw_dir()) / FILE
        return full if full.exists() else partial_path(full, HEAD_BYTES)

    def raw_files(self, raw_dir=None):
        return [self.csv_path(raw_dir)]

    def is_partial(self, raw_dir=None):
        return self.csv_path(raw_dir).name != FILE

    def _record(self, row):
        props = {name: Quantity(value=float(row[k]), unit=UNIT) for k, name in FIELDS.items()}
        payload = Reaction(reactants=row["reactant"].split("."), products=row["product"].split("."),
                           reaction_smiles=f"{row['reactant']}>>{row['product']}")
        return new_record(self.source_id, self.dataset_id, row["channel"], payload,
                          license=self.source.license, origin="simulated",
                          text=f"Computed reaction {row['channel']} ({row['type']}), B3LYP-D3/TZVP",
                          properties=props, tags=[f"type:{row['type']}"],
                          provenance=Provenance(source_url=self.dataset_url))

    def convert(self, raw_dir=None, limit=None):
        """Yield one record per CSV row. Only the last row may be skipped: when it is
        malformed, or when the file is a head-only read and the row may be cut off.
        A malformed row anywhere else raises. Skipped rows are counted in self.skipped_rows."""
        path, partial = self.csv_path(raw_dir), self.is_partial(raw_dir)
        self.skipped_rows, n = 0, 0
        with open(path, "rb") as fb:
            fb.seek(0, 2)
            ends_with_newline = fb.tell() == 0 or (fb.seek(-1, 2) or fb.read(1) == b"\n")
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
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
                        raise ValueError(f"{path.name} line {line}: malformed row ({e!r}); "
                                         "only the last row of a file may be skipped") from e
                    rec = None
                if rec is None or (last and partial and not ends_with_newline):
                    self.skipped_rows += 1
                    print(f"rgd1: skipped the last row of {path.name} (line {line}): "
                          f"{'malformed' if rec is None else 'cut off by the head-only read'}",
                          file=sys.stderr)
                else:
                    yield rec
                    n += 1
                row = nxt


CONNECTOR = RGD1
