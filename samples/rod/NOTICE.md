# Notice: samples/rod

The files in this folder are a small extract of **Raman Open Database (ROD, COD-linked)**,
converted to the assayfold record format. They are **not** covered by the MIT
license of this repository's code. They keep the source license: **CC0-1.0**.

- Source: https://solsa.crystallography.net/rod/
- License: CC0-1.0 (https://creativecommons.org/publicdomain/zero/1.0/)
- License checked at: https://solsa.crystallography.net/rod/1000001.rod on 2026-11-25
- License statement as found: "All data on this site have been placed in the public domain by the contributors."
- Attribution: El Mendili, Y., Vaitkus, A., Merkys, A., Grazulis, S. et al. Raman Open Database: first interconnected Raman-X-ray diffraction open-access resource for material identification. J. Appl. Crystallogr. 52, 618-625 (2019). doi:10.1107/S1600576719004229. Data: https://solsa.crystallography.net/rod/

Changes made: a subset of records was selected; fields were mapped to the assayfold
schema; unit strings were normalized (the original string is kept in `raw_unit_str`);
provenance and a record hash were added. See `meta.json` for how the sample was built.

CC0 requires no attribution; please cite the source above anyway.
