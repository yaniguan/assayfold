"""License and attribution notice for a committed sample, built from sources/<id>.yaml.

Takes any object with the Source fields (no pydantic needed), so it also works on plain
YAML data. `assayfold sample` writes the result to samples/<id>/NOTICE.md.
"""

MIT_PERMISSION = """\
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
"""


def _get(src, name):
    return src.get(name) if isinstance(src, dict) else getattr(src, name, None)


def notice_text(src) -> str:
    sid, lic = _get(src, "id"), _get(src, "license")
    lines = [
        f"# Notice: samples/{sid}",
        "",
        f"The files in this folder are a small extract of **{_get(src, 'name')}**,",
        "converted to the assayfold record format. They are **not** covered by the MIT",
        f"license of this repository's code. They keep the source license: **{lic}**.",
        "",
        f"- Source: {_get(src, 'homepage')}",
        f"- License: {lic}" + (f" ({_get(src, 'license_url')})" if _get(src, "license_url") else ""),
        f"- License checked at: {_get(src, 'license_evidence')} on {_get(src, 'license_checked')}",
    ]
    if _get(src, "license_quote"):
        lines.append(f"- License statement as found: {_get(src, 'license_quote')}")
    lines += [
        f"- Attribution: {_get(src, 'attribution')}",
        "",
        "Changes made: a subset of records was selected; fields were mapped to the assayfold",
        "schema; unit strings were normalized (the original string is kept in `raw_unit_str`);",
        "provenance and a record hash were added. See `meta.json` for how the sample was built.",
    ]
    if lic.startswith("CC-BY-SA"):
        lines += ["", f"Share-alike: this adapted material is licensed under {lic} as well."]
    if lic.startswith("CC0"):
        lines += ["", "CC0 requires no attribution; please cite the source above anyway."]
    if lic == "MIT":
        quote = _get(src, "license_quote") or ""
        i = quote.find("Copyright")
        copyright_line = quote[i:].strip().rstrip('"') if i >= 0 else None
        lines += ["", "## MIT license of the source data", "",
                  copyright_line or f"Copyright line: not recorded here; see {_get(src, 'license_evidence')}.",
                  "", MIT_PERMISSION.rstrip()]
    return "\n".join(lines) + "\n"
