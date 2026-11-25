# Notice: samples/massspecgym

The files in this folder are a small extract of **MassSpecGym tandem MS/MS spectra**,
converted to the assayfold record format. They are **not** covered by the MIT
license of this repository's code. They keep the source license: **MIT**.

- Source: https://huggingface.co/datasets/roman-bushuiev/MassSpecGym
- License: MIT (https://opensource.org/licenses/MIT)
- License checked at: https://huggingface.co/api/datasets/roman-bushuiev/MassSpecGym on 2026-11-25
- License statement as found: Hugging Face dataset cardData: "license": "mit"; Copyright (c) MassSpecGym contributors
- Attribution: Bushuiev, R. et al. MassSpecGym: A benchmark for the discovery and identification of molecules. NeurIPS Datasets and Benchmarks (2024). arXiv:2410.23326. Data: https://huggingface.co/datasets/roman-bushuiev/MassSpecGym

Changes made: a subset of records was selected; fields were mapped to the assayfold
schema; unit strings were normalized (the original string is kept in `raw_unit_str`);
provenance and a record hash were added. See `meta.json` for how the sample was built.

## MIT license of the source data

Copyright (c) MassSpecGym contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
