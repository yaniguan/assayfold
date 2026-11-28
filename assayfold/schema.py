"""Unified schema: Source -> Dataset -> Record.

Field names follow the lab ledger design (Quantity, Uncertainty, BlobRef, Provenance,
origin, schema_version, record_hash) so hub records can be appended to a ledger later.
See docs/ledger_mapping.md.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import SCHEMA_VERSION
from .canonical import canonical_json, sha256_hex


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- shared value types (same names as the ledger) ----------

class Uncertainty(_Model):
    kind: Literal["std", "interval", "none"] = "none"
    std: Optional[float] = None
    low: Optional[float] = None
    high: Optional[float] = None
    n: Optional[int] = None
    method: Optional[str] = None


class Quantity(_Model):
    value: Optional[float] = None
    unit: str = "1"                       # canonical code, see units.py
    raw_unit_str: Optional[str] = None    # the unit exactly as the source wrote it
    uncertainty: Optional[Uncertainty] = None


class BlobRef(_Model):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_type: str
    size_bytes: int
    filename_orig: Optional[str] = None
    url: Optional[str] = None             # where the bytes can be fetched again
    role: Literal["raw", "derived", "thumbnail"] = "raw"


class AgentRef(_Model):
    type: Literal["human", "robot", "model", "software", "instrument"] = "software"
    id: str
    name: Optional[str] = None
    version: Optional[str] = None


class SoftwareRef(_Model):
    name: str
    version: Optional[str] = None


class Provenance(_Model):
    agent: AgentRef = AgentRef(id="assayfold-converter", name="assayfold")
    recorded_utc: str = Field(default_factory=utc_now)
    source_url: Optional[str] = None      # page or file the record came from
    source_file_sha256: Optional[str] = None
    software: list[SoftwareRef] = []
    used: list[str] = []                  # ids or sha256 of inputs
    derived_from: list[str] = []


# ---------- hierarchy: Source and Dataset ----------

class Source(_Model):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    homepage: str
    license: str                          # SPDX id
    license_url: Optional[str] = None
    license_evidence: str                 # URL where the license was checked
    license_quote: Optional[str] = None
    license_checked: str                  # YYYY-MM-DD
    commercial_use_ok: bool
    redistribution_ok: bool
    attribution: str
    modalities: list[str]
    kinds: list[str]
    access: Literal["api", "download", "huggingface", "github"]
    size_full: Optional[str] = None       # as stated by the source, e.g. "3.8 MB"
    status: Literal["integrated", "fetch_only", "planned"] = "integrated"
    notes: Optional[str] = None


class Dataset(_Model):
    id: str
    source_id: str
    name: str
    version: str
    url: str
    license: str
    n_records_total: Optional[int] = None
    size_bytes_total: Optional[int] = None
    fetched_utc: str = Field(default_factory=utc_now)
    files: dict[str, str] = {}            # filename -> sha256


# ---------- record payloads (one per kind) ----------

class Molecule(_Model):
    kind: Literal["molecule"] = "molecule"
    smiles: str
    name: Optional[str] = None
    inchikey: Optional[str] = None
    formula: Optional[str] = None


ELEMENTS: tuple[str, ...] = (
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
    "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
    "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
)
ELEMENT_SET: frozenset[str] = frozenset(ELEMENTS)


class Structure(_Model):
    kind: Literal["structure"] = "structure"
    elements: list[str]
    coords_angstrom: list[list[float]]
    charge: int = 0
    multiplicity: Optional[int] = None
    smiles: Optional[str] = None
    role: Optional[str] = None            # e.g. reactant, product, transition_state
    forces: Optional[list[list[float]]] = None   # per atom, unit in forces_unit
    forces_unit: Optional[str] = None            # e.g. "eV/Ao"

    @model_validator(mode="after")
    def _shape(self):
        if len(self.elements) != len(self.coords_angstrom):
            raise ValueError("elements and coords_angstrom differ in length")
        if any(len(c) != 3 for c in self.coords_angstrom):
            raise ValueError("each coordinate needs 3 values")
        if self.forces is not None:
            if len(self.forces) != len(self.elements):
                raise ValueError("elements and forces differ in length")
            if any(len(f) != 3 for f in self.forces):
                raise ValueError("each force vector needs 3 values")
            if not self.forces_unit:
                raise ValueError("forces_unit is required when forces is set")
        return self


class Reaction(_Model):
    kind: Literal["reaction"] = "reaction"
    reactants: list[str]                  # SMILES
    products: list[str]
    agents: list[str] = []                # reagents, solvents, catalysts
    reaction_smiles: Optional[str] = None
    conditions: dict[str, Quantity] = {}
    yield_percent: Optional[Quantity] = None


class Protocol(_Model):
    kind: Literal["protocol"] = "protocol"
    title: str
    n_steps: Optional[int] = None
    url: Optional[str] = None
    domain: Optional[str] = None


class ProtocolStep(_Model):
    kind: Literal["protocol_step"] = "protocol_step"
    index: int
    text: str
    action: Optional[str] = None          # verb, e.g. "centrifuge"
    params: dict[str, Union[Quantity, str]] = {}
    entities: list[dict] = []             # e.g. annotated spans {type, text, start, end}


class Experiment(_Model):
    kind: Literal["experiment"] = "experiment"
    title: str
    description: Optional[str] = None


class Observation(_Model):
    kind: Literal["observation"] = "observation"
    property: str
    value: Quantity
    method: Optional[str] = None          # e.g. "experimental", "DFT B3LYP/6-31G(2df,p)"


class Spectrum(_Model):
    kind: Literal["spectrum"] = "spectrum"
    technique: str                        # e.g. IR, UV-Vis, NMR-1H
    x_unit: str
    y_unit: str
    x: list[float] = []
    y: list[float] = []
    peaks: list[dict] = []


class Image(_Model):
    kind: Literal["image"] = "image"
    blob: BlobRef
    width: Optional[int] = None
    height: Optional[int] = None
    annotations: list[dict] = []          # e.g. {label, mask_blob_sha256 | polygon}


class Trajectory(_Model):
    kind: Literal["trajectory"] = "trajectory"
    n_frames: int
    method: Optional[str] = None
    frames_blob: Optional[BlobRef] = None


class QAItem(_Model):
    kind: Literal["qa_item"] = "qa_item"
    task: str
    question: str
    choices: list[str] = []
    answer: Optional[str] = None
    context: Optional[str] = None
    canary: Optional[str] = None


Payload = Annotated[
    Union[Molecule, Structure, Reaction, Protocol, ProtocolStep, Experiment,
          Observation, Spectrum, Image, Trajectory, QAItem],
    Field(discriminator="kind"),
]
KINDS = ["experiment", "protocol", "protocol_step", "observation", "molecule", "structure",
         "reaction", "spectrum", "image", "trajectory", "qa_item"]
ORIGINS = ("real", "simulated", "model_generated", "synthetic_demo")


# ---------- the record ----------

def make_record_id(source_id: str, dataset_id: str, native_id: str) -> str:
    return "af:" + sha256_hex(f"{source_id}|{dataset_id}|{native_id}".encode())[:24]


class Record(_Model):
    record_id: str
    source_id: str
    dataset_id: str
    native_id: str
    kind: str
    parent_id: Optional[str] = None
    text: Optional[str] = None
    payload: Payload
    properties: dict[str, Quantity] = {}
    blobs: list[BlobRef] = []
    license: str
    origin: Literal["real", "simulated", "model_generated", "synthetic_demo"]
    provenance: Provenance = Field(default_factory=Provenance)
    tags: list[str] = []
    canary: Optional[str] = None
    schema_version: str = SCHEMA_VERSION
    record_hash: Optional[str] = None

    @model_validator(mode="after")
    def _kind_matches(self):
        if self.kind != self.payload.kind:
            raise ValueError(f"kind {self.kind!r} != payload kind {self.payload.kind!r}")
        if isinstance(self.payload, QAItem):
            if self.canary and not self.payload.canary:
                self.payload.canary = self.canary
            elif self.payload.canary and not self.canary:
                self.canary = self.payload.canary
        return self

    def content_hash(self) -> str:
        """sha256 over the canonical content. Excludes record_hash, recorded_utc, and unset canary."""
        d = self.model_dump(mode="json", exclude={"record_hash"})
        d["provenance"].pop("recorded_utc", None)
        if d.get("canary") is None:
            d.pop("canary", None)
        if isinstance(d.get("payload"), dict) and d["payload"].get("canary") is None:
            d["payload"].pop("canary", None)
        return sha256_hex(canonical_json(d))

    def sealed(self) -> "Record":
        """Return a copy with record_hash filled in."""
        return self.model_copy(update={"record_hash": self.content_hash()})


def new_record(source_id: str, dataset_id: str, native_id, payload, license: str,
               origin: str, **kw) -> Record:
    """Build and hash a record. Use this from connectors."""
    native_id = str(native_id)
    rec = Record(record_id=make_record_id(source_id, dataset_id, native_id),
                 source_id=source_id, dataset_id=dataset_id, native_id=native_id,
                 kind=payload.kind, payload=payload, license=license, origin=origin, **kw)
    return rec.sealed()


def export_json_schema(out_dir="schema") -> list[Path]:
    """Write JSON Schema files for Source, Dataset and Record."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, model in (("source", Source), ("dataset", Dataset), ("record", Record)):
        p = out / f"{name}.schema.json"
        p.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n")
        paths.append(p)
    return paths
