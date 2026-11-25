# Notice: samples/raman_bioprocess

The files in this folder are a small extract of **Bioprocess Analytes Benchtop Raman (Kaiser RXN1)**,
converted to the assayfold record format. They are **not** covered by the MIT
license of this repository's code. They keep the source license: **CC-BY-4.0**.

- Source: https://huggingface.co/datasets/chlange/RamanSpectraBioprocessAnalystesKaiser
- License: CC-BY-4.0 (https://creativecommons.org/licenses/by/4.0/)
- License checked at: https://huggingface.co/api/datasets/chlange/RamanSpectraBioprocessAnalystesKaiser on 2026-11-25
- License statement as found: Hugging Face dataset cardData: "license": "cc-by-4.0"
- Attribution: Lange, C., Borisyak, M., Koegler, M., Born, S., Ziehe, A., Neubauer, P., Cruz Bournazou, M. N. Comparing machine learning methods on Raman spectra from eight different spectrometers. Spectrochimica Acta Part A 334, 125861 (2025). doi:10.1016/j.saa.2025.125861

Changes made: a subset of records was selected; fields were mapped to the assayfold
schema; unit strings were normalized (the original string is kept in `raw_unit_str`);
provenance and a record hash were added. See `meta.json` for how the sample was built.
