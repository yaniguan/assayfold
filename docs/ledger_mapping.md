# Mapping to the lab data ledger

The YLM lab data ledger (design draft, being built separately) records our own experiments
as an append-only, hash-chained log: Project -> Campaign -> Experiment -> ProtocolStep ->
Action -> Observation. assayfold records open data in a shape that can be appended to that
ledger without loss. This table follows the ledger's current design draft; if the ledger
changes, this file and `assayfold/schema.py` change with it.

| assayfold | Ledger | Notes |
|---|---|---|
| `Source` | `Project` (external) | One external project per open source; license and citation live here |
| `Dataset` | `Campaign` (external) | Version, URL and file sha256 values |
| `Record` | `RecordEnvelope` | Same idea: id, kind, payload, provenance, blobs, hash |
| `Record.record_id` | `record_id` | Ours is deterministic (`af:` + sha256 of source, dataset, native id); the ledger uses UUIDv7 |
| `Record.record_hash` | `record_hash` | sha256 of canonical JSON (sorted keys, no spaces); the ledger also chains `prev_hash` |
| `Record.parent_id` | `parent_id` | Protocol step -> protocol, frame -> trajectory |
| `Record.origin` | `origin` | Same enum: `real`, `simulated`, `model_generated`, `synthetic_demo` |
| `Record.schema_version` | `schema_version` | semver |
| `Record.license` | `Project.license` | Per record here, because hub records mix sources |
| `Record.tags` | `tags` | e.g. `eval_only`, `split:test`, `reaction:rxn9083` |
| `Provenance` | `Provenance` | `agent`, `recorded_utc`, `software`, `used`, `derived_from` as in the ledger; plus `source_url`, `source_file_sha256` |
| `Quantity` / `Uncertainty` | `Quantity` / `Uncertainty` | Same fields: `value`, `unit` (UCUM-style), `raw_unit_str`, `uncertainty{kind,std,low,high,n,method}` |
| `BlobRef` | `BlobRef` | Same fields (`sha256`, `media_type`, `size_bytes`, `filename_orig`, `role`), plus `url` to refetch |
| kind `experiment` | `Experiment` | |
| kind `protocol` | `Experiment.protocol_ref` | A published protocol, before it is run |
| kind `protocol_step` | `ProtocolStep` | `index`, `text`, `action`, `params` |
| kind `observation` | `Observation` | A single measured property |
| kinds `molecule`, `structure`, `reaction`, `spectrum`, `image`, `trajectory` | `Observation` (modality) or a blob | The ledger stores these as an Observation modality or a raw blob |
| kind `qa_item` | (none) | Evaluation data only; tagged `eval_only` so it never becomes training data |

Not mapped: the ledger's `Action`, `GateDecision`, `CheckerResult`, `SimComparison`,
`Anomaly` and `SignOff` record our own runs. Open datasets rarely publish them; when they
do (for example failed reactions in ORD), they can be added as new kinds.
