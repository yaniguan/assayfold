# Notice: samples/aqsoldb

The files in this folder are a small extract of **AqSolDB**,
converted to the assayfold record format. They are **not** covered by the MIT
license of this repository's code. They keep the source license: **CC0-1.0**.

- Source: https://doi.org/10.7910/DVN/OVHAW8
- License: CC0-1.0 (https://creativecommons.org/publicdomain/zero/1.0/)
- License checked at: https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/OVHAW8 on 2026-11-18
- License statement as found: Dataverse metadata: license name "CC0 1.0", rightsIdentifier "CC0-1.0"
- Attribution: Sorkun, M. C., Khetan, A., Er, S. AqSolDB, a curated reference set of aqueous solubility and 2D descriptors for a diverse set of compounds. Scientific Data 6, 143 (2019). doi:10.1038/s41597-019-0151-1. Data: doi:10.7910/DVN/OVHAW8

Changes made: a subset of records was selected; fields were mapped to the assayfold
schema; unit strings were normalized (the original string is kept in `raw_unit_str`);
provenance and a record hash were added. See `meta.json` for how the sample was built.

CC0 requires no attribution; please cite the source above anyway.
