"""Open Reaction Database (ORD): structured reactions with amounts, conditions, outcomes.

Data CC-BY-SA-4.0 (derived data must keep the same license). Files are Parquet with one
serialized ord_schema Reaction per row; reading needs `pip install ord-schema`.
"""

from pathlib import Path

import pyarrow.parquet as pq

from ..schema import Provenance, Quantity, Reaction, new_record
from .base import Connector, download

HF = "https://huggingface.co/datasets/open-reaction-database/ord-data/resolve/main/data/{p}/{d}.parquet"
# A small default set: Suzuki-Miyaura coupling optimization (96 reactions each).
DATASETS = ["ord_dataset-2038a3c967db4a32a8fbce288437e929"]
TEMP_UNITS = {"CELSIUS": "Cel", "KELVIN": "K"}
TIME_UNITS = {"SECOND": "s", "MINUTE": "min", "HOUR": "h"}


def _smiles(component):
    for ident in component.identifiers:
        if ident.type == ident.SMILES:
            return ident.value
    return None


def reaction_to_payload(rxn) -> Reaction:
    """Map an ord_schema Reaction to the unified Reaction payload."""
    from ord_schema.proto import reaction_pb2
    role = reaction_pb2.ReactionRole.ReactionRoleType
    reactants, agents = [], []
    for inp in rxn.inputs.values():
        for c in inp.components:
            s = _smiles(c)
            if not s:
                continue
            if c.reaction_role == role.Value("REACTANT"):
                reactants.append(s)
            elif c.reaction_role in (role.Value("REAGENT"), role.Value("SOLVENT"),
                                     role.Value("CATALYST")):
                agents.append(s)
    products, yld = [], None
    for out in rxn.outcomes:
        for p in out.products:
            s = _smiles(p)
            if s:
                products.append(s)
            for m in p.measurements:
                if m.type == m.YIELD and m.HasField("percentage") and yld is None:
                    yld = Quantity(value=m.percentage.value, unit="%", raw_unit_str="percentage")
    cond = {}
    t = rxn.conditions.temperature.setpoint
    if rxn.conditions.temperature.HasField("setpoint"):
        unit = t.DESCRIPTOR.fields_by_name["units"].enum_type.values_by_number[t.units].name
        cond["temperature"] = Quantity(value=t.value, unit=TEMP_UNITS.get(unit, unit), raw_unit_str=unit)
    if rxn.outcomes and rxn.outcomes[0].HasField("reaction_time"):
        rt = rxn.outcomes[0].reaction_time
        unit = rt.DESCRIPTOR.fields_by_name["units"].enum_type.values_by_number[rt.units].name
        cond["reaction_time"] = Quantity(value=rt.value, unit=TIME_UNITS.get(unit, unit), raw_unit_str=unit)
    agents = list(dict.fromkeys(agents))
    rsmi = f"{'.'.join(reactants)}>{'.'.join(agents)}>{'.'.join(products)}"
    return Reaction(reactants=reactants, products=products, agents=agents,
                    reaction_smiles=rsmi, conditions=cond, yield_percent=yld)


class ORD(Connector):
    source_id = "ord"
    dataset_id = "ord"
    dataset_version = "HF open-reaction-database/ord-data main"
    dataset_url = "https://github.com/open-reaction-database/ord-data"
    datasets = DATASETS

    def fetch(self, raw_dir=None, limit=None):
        d = Path(raw_dir or self.raw_dir())
        for ds in self.datasets:
            download(HF.format(p=ds.split("-")[1][:2], d=ds), d / f"{ds}.parquet")
        return d

    def convert(self, raw_dir=None, limit=None):
        from ord_schema.proto import reaction_pb2
        d, n = Path(raw_dir or self.raw_dir()), 0
        for ds in self.datasets:
            table = pq.read_table(d / f"{ds}.parquet")
            name = table.schema.metadata.get(b"ord.name", b"").decode()
            for rid, blob in zip(table.column("reaction_id").to_pylist(), table.column("reaction").to_pylist()):
                if limit is not None and n >= limit:
                    return
                rxn = reaction_pb2.Reaction.FromString(blob)
                notes = rxn.notes.procedure_details.strip() or None
                yield new_record(self.source_id, ds, rid, reaction_to_payload(rxn),
                                 license=self.source.license, origin="real",
                                 text=notes or f"Reaction from ORD dataset '{name}'",
                                 provenance=Provenance(source_url=f"https://open-reaction-database.org/id/{rid}"))
                n += 1


CONNECTOR = ORD
