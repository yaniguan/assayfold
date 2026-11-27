# Notice: samples/ucr_ftir_chemometrics

The files in this folder are a small extract of **Open FT-IR chemometrics spectra (olive oil, coffee, fresh meat)**,
converted to the assayfold record format. They are **not** covered by the MIT
license of this repository's code. They keep the source license: **CC0-1.0**.

- Source: https://github.com/QIBChemometrics/FTIR-food-library
- License: CC0-1.0 (https://creativecommons.org/publicdomain/zero/1.0/)
- License checked at: https://raw.githubusercontent.com/QIBChemometrics/FTIR-food-library/main/LICENSE on 2026-11-27
- License statement as found: Quadram Institute Bioscience LICENSE across FTIR-food-library, FTIR-Spectra-Olive-Oils, and fresh-meat-ftir: "Creative Commons Legal Code CC0 1.0 Universal"
- Attribution: Kemsley, E. K., Tapp, H. S., Defernez, M., Al-Jowder, O., Downey, G., Wilson, R. H. Quadram Institute Bioscience (formerly Institute of Food Research, Norwich) Open FT-IR Chemometrics Datasets: Tapp et al., J. Agric. Food Chem. 51, 6110-6115 (2003); Downey et al., J. Agric. Food Chem. 45, 4357-4361 (1997); Al-Jowder et al., Food Chem. 59, 195-201 (1997).

Changes made: a subset of records was selected; fields were mapped to the assayfold
schema; unit strings were normalized (the original string is kept in `raw_unit_str`);
provenance and a record hash were added. See `meta.json` for how the sample was built.

CC0 requires no attribution; please cite the source above anyway.
