# assayfold

**Every open lab dataset, one schema: licensed, traced, ready for training and RAG.**

Open science data is spread over figshare, Zenodo, Dataverse, Hugging Face and GitHub,
each with its own format, units and license. The skill that matters most now is to collect
that open data, turn it into one format, and use what the open community has already
built. assayfold does this for lab science: protocols, reactions, quantum chemistry,
molecules, lab images and reaction-path structures go in, and one hierarchical, checked,
license-aware record format comes out.

```
Source  (who published it, license + evidence URL, citation)
  └── Dataset  (version, URL, file sha256)
        └── Record  (experiment | protocol | protocol_step | observation | molecule |
                     structure | reaction | spectrum | image | trajectory | qa_item)
              ├── payload     kind-specific fields (SMILES, xyz in Angstrom, steps, masks, ...)
              ├── properties  name -> Quantity(value, unit, uncertainty)
              ├── blobs       sha256-addressed raw files (images, archives)
              ├── license     SPDX id, checked by the license gate
              ├── provenance  source URL, file sha256, converter, time (UTC)
              └── record_hash sha256 of the canonical JSON
```

The field names (`Quantity`, `Uncertainty`, `BlobRef`, `Provenance`, `origin`,
`schema_version`, `record_hash`) follow the hierarchical lab ledger design used in
[YLM](https://github.com/yaniguan/YLM), so open data and our own lab records share one
format. See [docs/ledger_mapping.md](docs/ledger_mapping.md).

## Quickstart

```bash
pip install -e ".[dev,all]"          # rdkit, h5py, ord-schema, py7zr are optional extras
assayfold list                      # sources, licenses and status
assayfold fetch freesolv            # raw files go to data/raw/ (never committed)
assayfold convert freesolv          # -> data/unified/freesolv.jsonl
assayfold check data/unified/freesolv.jsonl
assayfold export data/unified/*.jsonl --format parquet --purpose train_commercial --out out/train.parquet
assayfold export data/unified/*.jsonl --format rag --out out/rag.jsonl
```

Each export writes a dataset card (`<file>.card.json`) with record counts per source and
license, what the license gate blocked, and the sha256 of the output.

## Catalog

Generated from `sources/*.yaml` by `assayfold catalog` (also in [catalog.csv](catalog.csv)).
"Sample records" are the small, license-checked samples committed under `samples/`.

<!-- catalog:start -->
| Source | Modalities | License | Commercial use | Full size | Sample records | Status |
|---|---|---|---|---|---|---|
| [AqSolDB](https://doi.org/10.7910/DVN/OVHAW8) | molecule, property | [CC0-1.0](https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/OVHAW8) | yes | 3.8 MB (curated-solubility-dataset.tab, 3,844,092 bytes per Dataverse) | 25 | integrated |
| [BioProBench](https://huggingface.co/datasets/BioProBench/BioProBench) | text, protocol, qa | [CC-BY-NC-4.0 (non-commercial)](https://github.com/YuyangSunshine/bioprobench) | no | test files: PQA 1,200, ORD 1,161, ERR 1,200, GEN 772 items; all JSON files ~783 MB (HF file list) | 0 | fetch_only |
| [FreeSolv hydration free energies](https://github.com/MobleyLab/FreeSolv) | molecule, property | [CC-BY-4.0](https://github.com/MobleyLab/FreeSolv/blob/master/README.md#license) | yes | 642 molecules (database.json) | 25 | integrated |
| [LAB-Bench (ProtocolQA and other subsets)](https://huggingface.co/datasets/futurehouse/lab-bench) | text, protocol, qa | [CC-BY-SA-4.0](https://huggingface.co/datasets/futurehouse/lab-bench) | yes | 1,967 rows in 8 subsets, 268 MB parquet (HF datasets-server); ProtocolQA: 108 rows | 0 | fetch_only |
| [LabPics (Medical) vessel and material segmentation](https://doi.org/10.5281/zenodo.4736111) | image, segmentation | [MIT](https://zenodo.org/api/records/4736111) | yes | LabPicsMedical.zip 280,823,957 bytes; LabPicsChemistry.zip 3,917,445,796 bytes (Zenodo) | 12 | integrated |
| [Open Reaction Database (ORD)](https://open-reaction-database.org) | reaction, conditions, outcome | [CC-BY-SA-4.0](https://github.com/open-reaction-database/ord-data#license) | yes | one Parquet file per dataset (Git LFS, mirrored on Hugging Face); default sample file 19,867 bytes, 96 reactions | 10 | integrated |
| [protocols.io public protocols](https://www.protocols.io) | text, protocol | [CC-BY-4.0](https://www.protocols.io/terms) | yes | public protocol collection via API; no total stated in the API docs | 0 | planned |
| [QM9 (134k molecules, DFT properties and 3D structures)](https://doi.org/10.1038/sdata.2014.22) | structure, property | [CC0-1.0](https://jla-gardner.github.io/load-atoms/datasets/QM9.html) | yes | 133,885 molecules; mirror gdb9.tar.gz is 44,852,087 bytes | 20 | integrated |
| [RGD1 reaction database (CHNO)](https://doi.org/10.6084/m9.figshare.21066901) | reaction, energy, transition_state, geometry | [CC-BY-4.0](https://api.figshare.com/v2/articles/21066901) | yes | DFT_reaction_info.csv 33.4 MB; RGD1_CHNO.h5 1.34 GB; RGD1_RPs.h5 468 MB (figshare file sizes) | 20 | integrated |
| [Transition1x reaction-pathway DFT data](https://doi.org/10.1038/s41597-022-01870-w) | structure, energy, forces, reaction_path | [MIT](https://huggingface.co/datasets/colabfit/Transition1x-test) | yes | 9.6 million DFT calculations (card); test split 190,261 configurations, co_0.parquet 146 MB | 20 | integrated |
| [USPTO reactions (Lowe, 1976-Sep 2016)](https://doi.org/10.6084/m9.figshare.5104873.v1) | reaction | [CC0-1.0](https://api.figshare.com/v2/articles/5104873) | yes | grants SMILES 7z 75,191,394 bytes; applications SMILES 7z 87,597,379 bytes (figshare) | 0 | planned |
| [Wet Lab Protocols corpus (WLP)](https://github.com/chaitanya2334/WLP-Dataset) | text, protocol, annotation | [MIT](https://github.com/chaitanya2334/WLP-Dataset/blob/master/LICENSE) | yes | 622 annotated protocols (README) | 58 | integrated |
<!-- catalog:end -->

Status: **integrated** = converter run on real data and a sample is committed;
**fetch_only** = converter works but no sample is committed (benchmark or non-commercial
data); **planned** = converter written and unit-tested, not yet run on the live source.

## Quality checks

`assayfold check` and every `sample`/`export` run the same checks, and report each failure
with a record id and reason. Nothing is dropped silently.

- **Schema validation**: pydantic models with `extra="forbid"`; the JSON Schema is in [schema/](schema).
- **Unit normalization**: raw unit strings map to UCUM-style codes (`uL`, `Cel`, `kcal/mol`,
  `Ao`, `[Eh]` for Hartree); the original string is kept in `raw_unit_str`; unknown units fail.
- **Chemistry sanity**: SMILES parse (RDKit when installed), finite coordinates, atom/coordinate counts.
- **Dedup**: by content hash, and by canonical SMILES for molecules within a source.
- **Integrity**: `record_hash` must match the content.
- **License gate**: unknown or missing licenses are blocked; non-commercial data is blocked
  for `train_commercial` and never committed; benchmark items (`eval_only` tag) never enter
  a training export.

## License policy

- Code: MIT ([LICENSE](LICENSE)).
- Data keeps its own license, recorded per source with the URL where it was checked and a
  quote. Share-alike sources (ORD, LAB-Bench) require the same license on derived data.
- Only small samples of redistributable, commercial-use-allowed data are committed.
  Full data is always fetched by script from the official location.
- This is an engineering guard, not legal advice. Re-check a license before you rely on it.

## Adding a source

See [docs/adding_a_source.md](docs/adding_a_source.md). A new connector is one file in
`assayfold/connectors/` plus one YAML file in `sources/`; tests pick it up automatically.

## Related repos

<!-- related:start -->
The lab co-scientist parts that use this data:

| Repo | Role |
|---|---|
| [YLM](https://github.com/yaniguan/YLM) | Brain: 3D chemistry + language model; home of the lab data ledger |
| [lab-ears](https://github.com/yaniguan/lab-ears) | Ears: spoken and written lab protocols |
| [lab-hands](https://github.com/yaniguan/lab-hands) | Hands and touch: bench manipulation and tactile sensing |
| [lab-rehearsal](https://github.com/yaniguan/lab-rehearsal) | Rehearse a run in a digital twin before the bench |
| [lab-verify](https://github.com/yaniguan/lab-verify) | Strict default-deny checkers (Lean, SQL, protocol) |
| [lab-decide](https://github.com/yaniguan/lab-decide) | Decision API that answers only where it is calibrated |
| [lab-ask-why](https://github.com/yaniguan/lab-ask-why) | Co-scientist that asks why |
| [lab-feet](https://github.com/yaniguan/lab-feet) | Run lab models on small edge boards |
| [stepbot](https://github.com/yaniguan/stepbot) | Compile simple step files to liquid-handler protocols |
| [twinstep](https://github.com/yaniguan/twinstep) | Seeded-error twins for protocol steps |
| [lab-automation-atlas](https://github.com/yaniguan/lab-automation-atlas) | Map of lab automation platforms and open protocol data |
| [WignerFlow](https://github.com/yaniguan/WignerFlow) | Generative molecular dynamics |
| [ouroboros-ocsr](https://github.com/yaniguan/ouroboros-ocsr) | Eyes: chemical structure images to 3D |
<!-- related:end -->

## Citing the data

Cite the original datasets. The `attribution` field in each `sources/<id>.yaml` has the
reference to use.
