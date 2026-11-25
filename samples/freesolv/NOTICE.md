# Notice: samples/freesolv

The files in this folder are a small extract of **FreeSolv hydration free energies**,
converted to the assayfold record format. They are **not** covered by the MIT
license of this repository's code. They keep the source license: **CC-BY-4.0**.

- Source: https://github.com/MobleyLab/FreeSolv
- License: CC-BY-4.0 (https://creativecommons.org/licenses/by/4.0/)
- License checked at: https://github.com/MobleyLab/FreeSolv/blob/master/README.md#license on 2026-11-18
- License statement as found: "the data here is covered by the enclosed LICENSE file, specifying CC-BY 4.0, and the code covered by LICENSE_code, an MIT license." The README adds that data derived from other sources may carry original licensing restrictions.
- Attribution: Mobley, D. L. (2013). Experimental and Calculated Small Molecule Hydration Free Energies. UC Irvine. http://www.escholarship.org/uc/item/6sd403pz ; Duarte Ramos Matos, G. et al., J. Chem. Eng. Data 62, 1559-1569 (2017), doi:10.1021/acs.jced.7b00104

Changes made: a subset of records was selected; fields were mapped to the assayfold
schema; unit strings were normalized (the original string is kept in `raw_unit_str`);
provenance and a record hash were added. See `meta.json` for how the sample was built.
