# Notice: samples/tdc_lipophilicity

The files in this folder are a small extract of **AstraZeneca ChEMBL3301361 octanol/water lipophilicity (logD7.4)**,
converted to the assayfold record format. They are **not** covered by the MIT
license of this repository's code. They keep the source license: **CC-BY-SA-3.0**.

- Source: https://doi.org/10.6019/CHEMBL3301361
- License: CC-BY-SA-3.0 (https://creativecommons.org/licenses/by-sa/3.0/)
- License checked at: https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/LICENSE on 2026-11-27
- License statement as found: ChEMBL LICENSE file: "Creative Commons Attribution-ShareAlike 3.0 Unported" covering AstraZeneca experimental DMPK deposition CHEMBL3301361 (doi:10.6019/CHEMBL3301361).
- Attribution: Wenlock, M., Tomkinson, N. Experimental in vitro DMPK and physicochemical data on a set of publicly disclosed compounds. EMBL-EBI ChEMBL (2015), doi:10.6019/CHEMBL3301361; Wu, Z. et al. MoleculeNet: a benchmark for molecular machine learning. Chemical Science 9, 513-530 (2018), doi:10.1039/C7SC02664A.

Changes made: a subset of records was selected; fields were mapped to the assayfold
schema; unit strings were normalized (the original string is kept in `raw_unit_str`);
provenance and a record hash were added. See `meta.json` for how the sample was built.

Share-alike: this adapted material is licensed under CC-BY-SA-3.0 as well.
