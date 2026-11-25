# Notice: samples/qm9

The files in this folder are a small extract of **QM9 (134k molecules, DFT properties and 3D structures)**,
converted to the assayfold record format. They are **not** covered by the MIT
license of this repository's code. They keep the source license: **CC0-1.0**.

- Source: https://doi.org/10.1038/sdata.2014.22
- License: CC0-1.0 (https://creativecommons.org/publicdomain/zero/1.0/)
- License checked at: https://jla-gardner.github.io/load-atoms/datasets/QM9.html on 2026-11-18
- License statement as found: load-atoms dataset entry for QM9 (files from figshare collection 978904): "This dataset is licensed under the CC0 license." The figshare collection page itself returned HTTP 403 to our network on 2026-11-18, so re-check it at https://figshare.com/collections/_/978904.
- Attribution: Ramakrishnan, R., Dral, P. O., Rupp, M., von Lilienfeld, O. A. Quantum chemistry structures and properties of 134 kilo molecules. Scientific Data 1, 140022 (2014). doi:10.1038/sdata.2014.22

Changes made: a subset of records was selected; fields were mapped to the assayfold
schema; unit strings were normalized (the original string is kept in `raw_unit_str`);
provenance and a record hash were added. See `meta.json` for how the sample was built.

CC0 requires no attribution; please cite the source above anyway.
