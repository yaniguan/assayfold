"""Small unit table: raw unit strings -> UCUM-style codes, plus a few safe conversions.

No external unit library. Units we do not know raise in strict mode.
Codes in square brackets ([Eh], [logS]) are local codes, not official UCUM.
"""

import re

# raw string (lower-cased, spaces removed) -> canonical code
_ALIASES = {
    "ul": "uL", "µl": "uL", "μl": "uL", "microliter": "uL", "microliters": "uL",
    "ml": "mL", "milliliter": "mL", "milliliters": "mL", "l": "L", "liter": "L",
    "nl": "nL", "nanoliter": "nL",
    "g": "g", "mg": "mg", "ug": "ug", "µg": "ug", "kg": "kg", "gram": "g", "milligram": "mg",
    "g/mol": "g/mol", "da": "g/mol",
    "mol/l": "mol/L", "molar": "mol/L", "mmol/l": "mmol/L",
    "umol/l": "umol/L", "mol": "mol", "mmol": "mmol",
    "c": "Cel", "°c": "Cel", "degc": "Cel", "celsius": "Cel", "cel": "Cel",
    "k": "K", "kelvin": "K",
    "s": "s", "sec": "s", "second": "s", "seconds": "s", "min": "min", "minute": "min",
    "minutes": "min", "h": "h", "hr": "h", "hour": "h", "hours": "h",
    "hartree": "[Eh]", "ha": "[Eh]", "eh": "[Eh]", "[eh]": "[Eh]",
    "ev": "eV", "kcal/mol": "kcal/mol", "kj/mol": "kJ/mol",
    "angstrom": "Ao", "å": "Ao", "ao": "Ao", "ang": "Ao", "bohr": "[a0]",
    "ev/angstrom": "eV/Ao", "ev/å": "eV/Ao", "ev/ao": "eV/Ao",
    "hartree/bohr": "[Eh]/[a0]",
    "debye": "[D]", "d": "[D]", "[d]": "[D]",
    "bohr^3": "[a0]3", "a0^3": "[a0]3", "bohr3": "[a0]3", "bohr^2": "[a0]2", "a0^2": "[a0]2",
    "cal/molk": "cal/(mol.K)", "cal/(mol·k)": "cal/(mol.K)", "cal/(mol.k)": "cal/(mol.K)",
    "ghz": "GHz", "mhz": "MHz",
    "nm": "nm", "cm-1": "/cm", "cm^-1": "/cm", "1/cm": "/cm", "/cm": "/cm",
    "ppm": "[ppm]", "%": "%", "percent": "%", "rpm": "{rpm}", "xg": "{g-force}", "g-force": "{g-force}",
    "log(mol/l)": "[logS]", "logs": "[logS]", "log10(mol/l)": "[logS]", "[logs]": "[logS]",
    "1": "1", "": "1", "unitless": "1", "dimensionless": "1",
}
# case-sensitive aliases (checked first): M is molar, m would be metre
_CASED = {"M": "mol/L", "mM": "mmol/L", "uM": "umol/L", "µM": "umol/L", "nM": "nmol/L", "D": "[D]"}
KNOWN = set(_ALIASES.values()) | set(_CASED.values())

# (from, to) -> factor or function for safe conversions
_FACTORS = {
    ("[Eh]", "eV"): 27.211386245988,
    ("eV", "[Eh]"): 1 / 27.211386245988,
    ("kcal/mol", "kJ/mol"): 4.184,
    ("kJ/mol", "kcal/mol"): 1 / 4.184,
    ("[Eh]", "kcal/mol"): 627.509474,
    ("mL", "uL"): 1000.0, ("uL", "mL"): 0.001, ("L", "mL"): 1000.0, ("mL", "L"): 0.001,
    ("[a0]", "Ao"): 0.529177210903, ("Ao", "[a0]"): 1 / 0.529177210903,
    ("[Eh]/[a0]", "eV/Ao"): 27.211386245988 / 0.529177210903,
}


class UnitError(ValueError):
    pass


def to_code(raw: str, strict: bool = True) -> str:
    """Map a raw unit string to its canonical code. Unknown -> UnitError (strict) or raw."""
    if raw in KNOWN:
        return raw
    if str(raw).strip() in _CASED:
        return _CASED[str(raw).strip()]
    key = re.sub(r"\s+", "", str(raw)).lower()
    if key in _ALIASES:
        return _ALIASES[key]
    if strict:
        raise UnitError(f"unknown unit: {raw!r}")
    return raw


def is_known(code: str) -> bool:
    return code in KNOWN


def parse_quantity(text: str, strict: bool = True):
    """Parse '25:microliter' (Autoprotocol) or '25 uL' into (value, code, raw_unit)."""
    text = str(text).strip()
    m = re.match(r"^([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*[: ]?\s*(.*)$", text)
    if not m:
        raise UnitError(f"cannot parse quantity: {text!r}")
    value, raw_unit = float(m.group(1)), m.group(2).strip()
    return value, to_code(raw_unit, strict=strict), raw_unit


def convert(value: float, src: str, dst: str) -> float:
    """Convert between a few unit pairs. Raises UnitError for unsupported pairs."""
    if src == dst:
        return value
    if (src, dst) == ("Cel", "K"):
        return value + 273.15
    if (src, dst) == ("K", "Cel"):
        return value - 273.15
    if (src, dst) in _FACTORS:
        return value * _FACTORS[(src, dst)]
    raise UnitError(f"no conversion {src} -> {dst}")
