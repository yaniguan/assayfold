# Adding a source

1. **Check the license first.** Open the official landing page (figshare, Zenodo,
   Dataverse, Hugging Face card, GitHub LICENSE or the paper's data statement). Record the
   SPDX id (or an explicit `LicenseRef-<id>` entry in `assayfold/licenses.py` for custom
   signed research-only agreements), the URL you checked, a short quote and the date. If
   there is no clear license, stop: the source cannot be added.
2. **Write `sources/<id>.yaml`.** Fill in every field of `Source` in `assayfold/schema.py`:
   homepage, license, evidence, attribution (real citation), modalities, kinds, size as
   stated by the source, and status (`planned` until the converter has run on real data).
3. **Write `assayfold/connectors/<id>.py`.** Subclass `Connector`, implement
   `fetch(raw_dir, limit)` (raw files go to `data/raw/<id>/`, never into git) and
   `convert(raw_dir, limit)` (yield records made with `new_record`). Set `CONNECTOR = YourClass`.
   Keep it small. Read units from the source documentation; do not guess them.
4. **Fetch and convert.** `assayfold fetch <id> --limit 50` then
   `assayfold convert <id> --limit 50` and `assayfold check data/unified/<id>.jsonl`.
5. **Commit a sample only if allowed.** `assayfold sample <id> --limit 25` refuses
   non-commercial, unknown-license and non-integrated sources, and keeps committed sample
   files compact (`< 1 MB`) and SHA-256 sealed (`record_hash` + `meta.json` input file
   hashes). Share-alike sources (`CC-BY-SA-3.0`, `CC-BY-SA-4.0`, `ODbL-1.0`) propagate
   their share-alike notice into `NOTICE.md` and export dataset cards. Benchmarks (such as
   `lab_bench`, `chembench`, `bioprobench`, and `ehrsql_mimic_iv_demo`) stay `fetch_only`,
   preserve any upstream `canary` string on `Record.canary` / `QAItem.canary`, and get the
   `eval_only` tag so they never enter training exports, committed samples, or default RAG
   exports.
6. **Test and catalog.** Add offline parser and license-gate tests in `tests/` (for example
   `tests/test_connectors_offline.py` or `tests/test_issue1_and_2026_expansion.py`), then
   run `assayfold catalog`, `assayfold schema`, and `pytest -q`. `tests/test_samples.py`
   and the README-catalog parity test check every committed sample and table row
   automatically.
