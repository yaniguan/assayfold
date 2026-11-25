"""FineBio: hierarchical biological wet-lab experiment protocols and atomic operations."""

import json
from pathlib import Path

from ..schema import Protocol, ProtocolStep, Provenance, Quantity, new_record
from .base import Connector, download

ANN_URL = (
    "https://raw.githubusercontent.com/aistairc/FineBio/main/"
    "atomic_operation_detection/actionformer2/data/annotations/annotation_all.json"
)
MAP_URL = "https://raw.githubusercontent.com/aistairc/FineBio/main/step_segmentation/data/mapping.txt"


def trial_to_records(source_id: str, dataset_id: str, license_id: str,
                     trial_id: str, entry: dict, source_url: str, max_steps: int | None = None):
    """Yield one Protocol record and its timestamped atomic ProtocolStep children."""
    parts = trial_id.split("_")
    proto_code = parts[1] if len(parts) > 1 else "00"
    subset = str(entry.get("subset") or "train")
    anns = list(entry.get("annotations") or [])
    if max_steps is not None:
        anns = anns[:max_steps]
    props = {}
    if entry.get("duration") is not None:
        props["duration"] = Quantity(
            value=round(float(entry["duration"]), 4), unit="s", raw_unit_str="s"
        )
    if entry.get("fps") is not None:
        props["frame_rate"] = Quantity(
            value=round(float(entry["fps"]), 4), unit="Hz", raw_unit_str="fps"
        )
    base_tags = ["non_commercial", f"split:{subset}", f"protocol:{proto_code}"]
    if subset == "test":
        base_tags.append("eval_only")
    proto_rec = new_record(
        source_id,
        dataset_id,
        trial_id,
        Protocol(
            title=f"FineBio biological experiment {trial_id} (protocol {proto_code})",
            n_steps=len(entry.get("annotations") or []),
            url="https://github.com/aistairc/FineBio",
            domain="molecular_biology",
        ),
        license=license_id,
        origin="real",
        text=f"FineBio wet-lab protocol execution {trial_id} ({subset})",
        properties=props,
        tags=base_tags,
        provenance=Provenance(source_url=source_url),
    )
    yield proto_rec
    for idx, ann in enumerate(anns):
        seg = ann.get("segment") or [0.0, 0.0]
        t0, t1 = round(float(seg[0]), 4), round(float(seg[1]), 4)
        dur = round(max(0.0, t1 - t0), 4)
        verb = str(ann.get("verb_label") or "")
        op_label = str(ann.get("atomic_operation_label") or verb or f"step_{idx}")
        manip = str(ann.get("manipulated_label") or "none")
        aff = str(ann.get("affected_label") or "none")
        hand = str(ann.get("hand_label") or "unknown")
        entities = [{"role": "manipulated", "label": manip}]
        if aff != "none":
            entities.append({"role": "affected", "label": aff})
        yield new_record(
            source_id,
            dataset_id,
            f"{trial_id}#op{idx}",
            ProtocolStep(
                index=idx,
                text=op_label.replace("-", " ").replace("_", " "),
                action=verb or None,
                params={
                    "start_time": Quantity(value=t0, unit="s", raw_unit_str="s"),
                    "end_time": Quantity(value=t1, unit="s", raw_unit_str="s"),
                    "duration": Quantity(value=dur, unit="s", raw_unit_str="s"),
                    "hand": hand,
                },
                entities=entities,
            ),
            license=license_id,
            origin="real",
            parent_id=proto_rec.record_id,
            text=f"{op_label} ({t0}-{t1} s, {hand} hand)",
            tags=list(base_tags),
            provenance=Provenance(source_url=source_url),
        )


class FineBio(Connector):
    source_id = "finebio"
    dataset_id = "finebio-atomic"
    dataset_version = "GitHub aistairc/FineBio main (annotation_all.json)"
    dataset_url = "https://github.com/aistairc/FineBio"

    def fetch(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        download(ANN_URL, d / "annotation_all.json")
        download(MAP_URL, d / "mapping.txt")
        return d

    def convert(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        db = json.loads((d / "annotation_all.json").read_text(encoding="utf-8"))["database"]
        n = 0
        for trial_id in sorted(db):
            for rec in trial_to_records(
                self.source_id, self.dataset_id, self.source.license,
                trial_id, db[trial_id], ANN_URL,
            ):
                if limit is not None and n >= limit:
                    return
                yield rec
                n += 1


CONNECTOR = FineBio
