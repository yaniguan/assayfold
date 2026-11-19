# Notice: samples/ord

The files in this folder are a small extract of **Open Reaction Database (ORD)**,
converted to the assayfold record format. They are **not** covered by the MIT
license of this repository's code. They keep the source license: **CC-BY-SA-4.0**.

- Source: https://open-reaction-database.org
- License: CC-BY-SA-4.0 (https://creativecommons.org/licenses/by-sa/4.0/)
- License checked at: https://github.com/open-reaction-database/ord-data#license on 2026-11-18
- License statement as found: "The datasets under data/ (and the repository metadata describing them) | CC-BY-SA-4.0"; code under scripts/ is Apache-2.0. HF mirror metadata: "license: cc-by-sa-4.0".
- Attribution: Kearnes, S. M. et al. The Open Reaction Database. J. Am. Chem. Soc. 143, 18820-18826 (2021). doi:10.1021/jacs.1c09820. Data: https://github.com/open-reaction-database/ord-data

Changes made: a subset of records was selected; fields were mapped to the assayfold
schema; unit strings were normalized (the original string is kept in `raw_unit_str`);
provenance and a record hash were added. See `meta.json` for how the sample was built.

Share-alike: this adapted material is licensed under CC-BY-SA-4.0 as well.
