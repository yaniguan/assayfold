# Notice: samples/rgd1

The files in this folder are a small extract of **RGD1 reaction database (CHNO)**,
converted to the assayfold record format. They are **not** covered by the MIT
license of this repository's code. They keep the source license: **CC-BY-4.0**.

- Source: https://doi.org/10.6084/m9.figshare.21066901
- License: CC-BY-4.0 (https://creativecommons.org/licenses/by/4.0/)
- License checked at: https://api.figshare.com/v2/articles/21066901 on 2026-11-18
- License statement as found: figshare metadata: license "CC BY 4.0". The code repo github.com/zhaoqy1996/RGD1 is GPL-3.0 (code only).
- Attribution: Zhao, Q., Vaddadi, S. M., Woulfe, M., Ogunfowora, L. A., Garimella, S. S., Isayev, O., Savoie, B. M. Comprehensive exploration of graphically defined reaction spaces. Scientific Data 10, 145 (2023). doi:10.1038/s41597-023-02043-z

Changes made: a subset of records was selected; fields were mapped to the assayfold
schema; unit strings were normalized (the original string is kept in `raw_unit_str`);
provenance and a record hash were added. See `meta.json` for how the sample was built.
