# Notice: samples/uspto_lowe

The files in this folder are a small extract of **USPTO patent chemical reactions (Lowe / USPTO-50K)**,
converted to the assayfold record format. They are **not** covered by the MIT
license of this repository's code. They keep the source license: **CC0-1.0**.

- Source: https://doi.org/10.6084/m9.figshare.5104873.v1
- License: CC0-1.0 (https://creativecommons.org/publicdomain/zero/1.0/)
- License checked at: https://api.figshare.com/v2/articles/5104873 on 2026-11-27
- License statement as found: figshare API metadata for article 5104873 "Chemical reactions from US patents (1976-Sep2016)": license "CC0" (https://creativecommons.org/publicdomain/zero/1.0/)
- Attribution: Lowe, D. M. Extraction of chemical structures and reactions from the literature. PhD thesis, University of Cambridge (2012); Chemical reactions from US patents (1976-Sep2016), figshare (2017), doi:10.6084/m9.figshare.5104873.v1; Schneider, N. et al., J. Chem. Inf. Model. 56, 2336-2346 (2016).

Changes made: a subset of records was selected; fields were mapped to the assayfold
schema; unit strings were normalized (the original string is kept in `raw_unit_str`);
provenance and a record hash were added. See `meta.json` for how the sample was built.

CC0 requires no attribution; please cite the source above anyway.
