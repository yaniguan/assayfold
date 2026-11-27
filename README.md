# assayfold

**Every open lab dataset, one schema: licensed, traced, ready for training and RAG.**

Open science data is spread over figshare, Zenodo, Dataverse, Hugging Face and GitHub,
each with its own format, units and license. The skill that matters most now is to collect
that open data, turn it into one format, and use what the open community has already
built. assayfold does this across 27 open laboratory sources: protocols, atomic wet-lab
operations, reactions, quantum chemistry, molecules, hydration free energies, octanol/water
lipophilicity, multi-solvent solubilities, electrolyte conductivities, MS/MS, FT-IR, Raman
and powder XRD spectra, lab vessel/phase images, machine audio, clinical lab SQL queries and
reaction-path structures go in, and one hierarchical, checked, license-aware record format
comes out.

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

Generated from the 27 `sources/*.yaml` definitions by `assayfold catalog` (also in
[catalog.csv](catalog.csv)). "Sample records" are the small, license-checked samples committed
under `samples/`.

<!-- catalog:start -->
| Source | Modalities | License | Commercial use | Full size | Sample records | Status |
|---|---|---|---|---|---|---|
| [AqSolDB](https://doi.org/10.7910/DVN/OVHAW8) | molecule, property | [CC0-1.0](https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/OVHAW8) | yes | 3.8 MB (curated-solubility-dataset.tab, 3,844,092 bytes per Dataverse) | 25 | integrated |
| [BigSolDB 2.0 multi-solvent solubility](https://doi.org/10.5281/zenodo.15094979) | molecule, solubility, property | [CC-BY-4.0](https://zenodo.org/api/records/15094979) | yes | BigSolDBv2.0.csv 18,280,116 bytes; BigSolDBv2.0_densities.csv 120,029 bytes (Zenodo) | 25 | integrated |
| [BioProBench](https://huggingface.co/datasets/BioProBench/BioProBench) | text, protocol, qa | [CC-BY-NC-4.0 (non-commercial)](https://github.com/YuyangSunshine/bioprobench) | no | test files: PQA 1,200, ORD 1,161, ERR 1,200, GEN 772 items; all JSON files ~783 MB (HF file list) | 0 | fetch_only |
| [CALiSol-23 electrolyte conductivity atlas](https://doi.org/10.11583/DTU.24559960.v1) | electrolyte, conductivity, property | [CC-BY-4.0](https://api.figshare.com/v2/articles/24559960) | yes | 13,825 rows across 14 Li salts and 38 solvents (calisol23_DOI_10.11583DTU.c.6929599.csv, 2,868,746 bytes) | 25 | integrated |
| [ChemBench chemistry knowledge and safety benchmark](https://huggingface.co/datasets/jablonkagroup/ChemBench) | text, chemistry, safety, qa | [MIT](https://huggingface.co/api/datasets/jablonkagroup/ChemBench) | yes | 9 chemistry and lab-safety Parquet subsets (~2,700 curated questions on Hugging Face) | 0 | fetch_only |
| [DCASE 2025 Task 2 machine anomalous sound detection](https://doi.org/10.5281/zenodo.15097779) | audio, acoustic, anomaly_detection | [CC-BY-NC-SA-4.0 (non-commercial)](https://zenodo.org/api/records/15097779) | no | 7 machine ZIP archives (valve, slider, fan, gearbox, bearing, ToyCar, ToyTrain; ~2.36 GB total on Zenodo) | 0 | fetch_only |
| [EHRSQL-2024 clinical lab & EHR SQL benchmark (MIMIC-IV Demo v2.2)](https://github.com/glee4810/ehrsql-2024) | text, clinical_lab, sql, qa | [ODbL-1.0](https://physionet.org/content/mimic-iv-demo/2.2/) | yes | EHRSQL-2024 train/valid/test splits (~10 MB JSON) + MIMIC-IV Demo v2.2 SQLite database (37 MB, 100 patients) | 0 | fetch_only |
| [FineBio biological experiment protocol and atomic action dataset](https://github.com/aistairc/FineBio) | video, protocol, action | [LicenseRef-FineBio-NC (non-commercial)](https://github.com/aistairc/FineBio#download) | no | 226 multi-view wet-lab experiment trials across 32 participants and 7 protocols (14.5 h video; hierarchical JSON/TXT annotations on GitHub) | 0 | fetch_only |
| [FreeSolv hydration free energies](https://github.com/MobleyLab/FreeSolv) | molecule, property | [CC-BY-4.0](https://github.com/MobleyLab/FreeSolv/blob/master/README.md#license) | yes | 642 molecules (database.json) | 25 | integrated |
| [LAB-Bench (ProtocolQA and other subsets)](https://huggingface.co/datasets/futurehouse/lab-bench) | text, protocol, qa | [CC-BY-SA-4.0](https://huggingface.co/datasets/futurehouse/lab-bench) | yes | 1,967 rows in 8 subsets, 268 MB parquet (HF datasets-server); ProtocolQA: 108 rows | 0 | fetch_only |
| [LabPics (Medical) vessel and material segmentation](https://doi.org/10.5281/zenodo.4736111) | image, segmentation | [MIT](https://zenodo.org/api/records/4736111) | yes | LabPicsMedical.zip 280,823,957 bytes; LabPicsChemistry.zip 3,917,445,796 bytes (Zenodo) | 12 | integrated |
| [LabPics (Chemistry) reaction vessel and phase segmentation](https://doi.org/10.5281/zenodo.4736111) | image, segmentation, chemistry_vessels | [MIT](https://zenodo.org/api/records/4736111) | yes | LabPicsChemistry.zip 3,917,445,796 bytes (~5,007 annotated chemistry vessel scenes on Zenodo) | 10 | integrated |
| [MassSpecGym tandem MS/MS spectra](https://huggingface.co/datasets/roman-bushuiev/MassSpecGym) | spectrum, molecule, msms | [MIT](https://huggingface.co/api/datasets/roman-bushuiev/MassSpecGym) | yes | 231k MS/MS spectra (MassSpecGym.tsv 262,334,768 bytes on Hugging Face) | 20 | integrated |
| [opXRD experimental powder X-ray diffraction](https://doi.org/10.5281/zenodo.15298026) | spectrum, xrd, crystal | [CC-BY-4.0](https://zenodo.org/api/records/15298026) | yes | 92,565 experimental PXRD JSON patterns across 7 institutions (opxrd.zip, 1,400,997,733 bytes on Zenodo) | 10 | integrated |
| [Open Reaction Database (ORD)](https://open-reaction-database.org) | reaction, conditions, outcome | [CC-BY-SA-4.0](https://github.com/open-reaction-database/ord-data#license) | yes | one Parquet file per dataset (Git LFS, mirrored on Hugging Face); default sample file 19,867 bytes, 96 reactions | 10 | integrated |
| [protocols.io public protocols](https://www.protocols.io) | text, protocol | [CC-BY-4.0](https://www.protocols.io/terms) | yes | public protocol collection via API; no total stated in the API docs | 0 | planned |
| [protocols.io open-access protocols & BioProt](https://github.com/protocolsio/protocols) | text, protocol, wet_lab | [CC-BY-4.0](https://www.protocols.io/terms) | yes | 573 public protocol JSONs in protocolsio/protocols plus 100 BioProt protocols (~267 KB); full live catalog via PROTOCOLS_IO_ACCESS_TOKEN | 15 | integrated |
| [QM9 (134k molecules, DFT properties and 3D structures)](https://doi.org/10.1038/sdata.2014.22) | structure, property | [CC0-1.0](https://api.figshare.com/v2/articles/1057645) | yes | 133,885 molecules; mirror gdb9.tar.gz is 44,852,087 bytes | 20 | integrated |
| [Bioprocess Analytes Benchtop Raman (Kaiser RXN1)](https://huggingface.co/datasets/chlange/RamanSpectraBioprocessAnalystesKaiser) | spectrum, raman, bioprocess | [CC-BY-4.0](https://huggingface.co/api/datasets/chlange/RamanSpectraBioprocessAnalystesKaiser) | yes | 134 Raman spectra (300.0-1941.3 cm^-1) across train/val/test Parquet splits | 5 | integrated |
| [RGD1 reaction database (CHNO)](https://doi.org/10.6084/m9.figshare.21066901) | reaction, energy, transition_state, geometry | [CC-BY-4.0](https://api.figshare.com/v2/articles/21066901) | yes | DFT_reaction_info.csv 33.4 MB; RGD1_CHNO.h5 1.34 GB; RGD1_RPs.h5 468 MB (figshare file sizes) | 20 | integrated |
| [Raman Open Database (ROD, COD-linked)](https://solsa.crystallography.net/rod/) | spectrum, raman, crystal | [CC0-1.0](https://solsa.crystallography.net/rod/1000001.rod) | yes | Open CIF 2.0 mineral and crystal Raman spectra via REST API (solsa.crystallography.net/rod) | 10 | integrated |
| [AstraZeneca ChEMBL3301361 octanol/water lipophilicity (logD7.4)](https://doi.org/10.6019/CHEMBL3301361) | molecule, lipophilicity, property | [CC-BY-SA-3.0](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/LICENSE) | yes | 4,200 compounds with experimental shake-flask octanol/buffer logD7.4 (Lipophilicity.csv, 282,606 bytes) | 25 | integrated |
| [Transition1x reaction-pathway DFT data](https://doi.org/10.1038/s41597-022-01870-w) | structure, energy, forces, reaction_path | [MIT](https://api.figshare.com/v2/articles/19614657) | yes | 9.6 million DFT calculations (card); test split 190,261 configurations, co_0.parquet 146 MB | 20 | integrated |
| [Open FT-IR chemometrics spectra (olive oil, coffee, fresh meat)](https://github.com/QIBChemometrics/FTIR-food-library) | spectrum, ir, ftir, chemometrics | [CC0-1.0](https://raw.githubusercontent.com/QIBChemometrics/FTIR-food-library/main/LICENSE) | yes | 120 olive oil ATR-FTIR spectra (820 KB), 120 fresh meat ATR-FTIR spectra (648 KB), and 46 food/coffee library spectra (4.9 MB) | 10 | integrated |
| [USPTO reactions (Lowe, 1976-Sep 2016)](https://doi.org/10.6084/m9.figshare.5104873.v1) | reaction | [CC0-1.0](https://api.figshare.com/v2/articles/5104873) | yes | grants SMILES 7z 75,191,394 bytes; applications SMILES 7z 87,597,379 bytes (figshare) | 25 | integrated |
| [USPTO patent chemical reactions (Lowe / USPTO-50K)](https://doi.org/10.6084/m9.figshare.5104873.v1) | reaction, conditions, yield | [CC0-1.0](https://api.figshare.com/v2/articles/5104873) | yes | 1.8M text-mined US patent reactions (1976-Sep 2016); 1976 grants shard 11.1 MB (17,855 reactions); USPTO-50K validation shard 182 KB | 25 | integrated |
| [Wet Lab Protocols corpus (WLP)](https://github.com/chaitanya2334/WLP-Dataset) | text, protocol, annotation | [MIT](https://github.com/chaitanya2334/WLP-Dataset/blob/master/LICENSE) | yes | 622 annotated protocols (README) | 58 | integrated |
<!-- catalog:end -->

Status: **integrated** = converter run on real data and a sample is committed;
**fetch_only** = converter works but no sample is committed (benchmark or non-commercial
data); **planned** = converter written and unit-tested, not yet run on the live source.

## Quality checks

`assayfold check` and every `sample`/`export` run the same checks, and report each failure
with a record id and reason. RGD1 reports how many malformed rows it skipped; a truncated
last line at EOF is allowed, other dropped rows are counted.

- **Schema validation**: pydantic models with `extra="forbid"`; the JSON Schema is in [schema/](schema).
- **Unit normalization**: raw unit strings map to UCUM-style codes (`uL`, `Cel`, `K`,
  `kcal/mol`, `kJ/mol`, `Ao`, `[Eh]` for Hartree, `[logS]`, `[logD]`, `[pH]`, `mS/cm` for
  electrolyte conductivity, `deg` for 2-theta diffraction angles, `/cm` for `cm^-1` IR/Raman
  wavenumber, `[m/z]` and `g/mol` for `Da` in mass spectrometry, `mol/kg`, `g/L`, `Hz`, `s`);
  the original string is kept in `raw_unit_str`; unknown units fail (including
  `Spectrum.x_unit` and `Spectrum.y_unit`).
- **Chemistry and spectral sanity**: SMILES parse (RDKit when installed), finite coordinates,
  atom/coordinate counts, finite matched-length `Spectrum` arrays.
- **Dedup**: by content hash, and by canonical SMILES for molecules within a source.
- **Integrity**: `record_hash` is checked on the record as loaded, before unit normalization
  reseals it.
- **License gate**: each record's `source_id` must exist in `sources/<id>.yaml`, and its
  license must match that source file. The per-record license string alone is not trusted.
  Non-commercial data (`CC-BY-NC-4.0`, `CC-BY-NC-SA-4.0`, `LicenseRef-FineBio-NC`) is blocked
  for `train_commercial`, `rag` (an index that may serve a commercial product), and committed
  samples. It is allowed for `train_research` and `rag_research`, with research-use-only (and
  share-alike, where applicable) notes. Benchmark items (`eval_only` tag, e.g. LAB-Bench,
  ChemBench, BioProBench, EHRSQL-2024 / MIMIC-IV Demo, and held-out test folds) never enter a
  training export or sample.

## License policy

- Code: MIT ([LICENSE](LICENSE)).
- Data keeps its own license, recorded per source with the URL where it was checked and a
  quote. Share-alike sources (`CC-BY-SA-3.0`, `CC-BY-SA-4.0`, `ODbL-1.0`, e.g. ORD, LAB-Bench,
  ChEMBL3301361 Lipophilicity, MIMIC-IV Demo) require the same license on derived data.
- Committed files under `samples/` are not under the MIT license of the code. Each folder
  has a `NOTICE.md` with the source name, license, evidence URL and attribution.
- Only small samples of redistributable, commercial-use-allowed data are committed.
  Full data is fetched by script from the official location or a named mirror listed in
  the source YAML.
- A limited or interrupted download is stored under a distinct name (not the published
  filename) and is not reused as the full file. `files` hashes in `meta.json` are of the
  files the converter actually read.
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
