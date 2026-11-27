"""Small unit table: raw unit strings -> UCUM-style codes, plus a few safe conversions.

No external unit library. Units we do not know raise in strict mode.
Codes in square brackets ([Eh], [logS], [m/z]) are local codes, not official UCUM.
"""

import math
import re

# raw string (lower-cased, spaces removed) -> canonical code
_ALIASES = {
    "ul": "uL", "µl": "uL", "μl": "uL", "microliter": "uL", "microliters": "uL",
    "ml": "mL", "milliliter": "mL", "milliliters": "mL", "l": "L", "liter": "L",
    "nl": "nL", "nanoliter": "nL",
    "g": "g", "mg": "mg", "ug": "ug", "µg": "ug", "kg": "kg", "gram": "g", "milligram": "mg",
    "g/mol": "g/mol", "da": "g/mol", "dalton": "g/mol", "daltons": "g/mol",
    "amu": "g/mol", "u": "g/mol", "kg/mol": "kg/mol", "kda": "kg/mol",
    "mol/l": "mol/L", "molar": "mol/L", "mmol/l": "mmol/L",
    "umol/l": "umol/L", "mol": "mol", "mmol": "mmol",
    "mol/kg": "mol/kg", "mmol/kg": "mmol/kg", "molal": "mol/kg",
    "g/l": "g/L", "gl-1": "g/L", "g/liter": "g/L", "mg/ml": "g/L", "mg/l": "mg/L",
    "c": "Cel", "°c": "Cel", "degc": "Cel", "celsius": "Cel", "cel": "Cel",
    "k": "K", "kelvin": "K",
    "ms": "ms", "millisecond": "ms", "milliseconds": "ms",
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
    "hz": "Hz", "hertz": "Hz", "fps": "Hz", "khz": "kHz", "ghz": "GHz", "mhz": "MHz",
    "nm": "nm", "cm-1": "/cm", "cm^-1": "/cm", "cm⁻¹": "/cm", "1/cm": "/cm", "/cm": "/cm",
    "wavenumber": "/cm", "ramanshift": "/cm", "ramanshift(cm^-1)": "/cm",
    "deg": "deg", "°": "deg", "degree": "deg", "degrees": "deg",
    "2theta": "deg", "2-theta": "deg", "deg2theta": "deg", "deg(2theta)": "deg",
    "rad": "rad", "radian": "rad", "radians": "rad",
    "ms/cm": "mS/cm", "mscm-1": "mS/cm", "mscm^-1": "mS/cm", "ms·cm-1": "mS/cm",
    "s/cm": "S/cm", "scm-1": "S/cm", "scm^-1": "S/cm",
    "s/m": "S/m", "sm-1": "S/m", "sm^-1": "S/m",
    "us/cm": "uS/cm", "µs/cm": "uS/cm", "μs/cm": "uS/cm",
    "m/z": "[m/z]", "mz": "[m/z]", "[m/z]": "[m/z]", "th": "[m/z]",
    "thomson": "[m/z]", "da/e": "[m/z]",
    "mw": "mW", "milliwatt": "mW", "w": "W", "watt": "W",
    "db": "dB", "decibel": "dB",
    "pa": "Pa", "kpa": "kPa", "bar": "bar", "atm": "atm",
    "{counts}": "{counts}", "counts": "{counts}", "cnt": "{counts}",
    "{arb}": "{arb}", "a.u.": "{arb}", "au": "{arb}", "arb.units": "{arb}",
    "ppm": "[ppm]", "%": "%", "percent": "%", "rpm": "{rpm}", "xg": "{g-force}", "g-force": "{g-force}",
    "rcf": "{g-force}",
    "log(mol/l)": "[logS]", "logs": "[logS]", "log10(mol/l)": "[logS]", "[logs]": "[logS]",
    "logd": "[logD]", "logd7.4": "[logD]", "logd(ph7.4)": "[logD]", "[logd]": "[logD]",
    "ph": "[pH]", "[ph]": "[pH]",
    "absorbance": "1", "abs": "1",
    "1": "1", "": "1", "unitless": "1", "dimensionless": "1",
}
# case-sensitive aliases (checked first): M is molar, m would be metre
_CASED = {
    "M": "mol/L", "mM": "mmol/L", "uM": "umol/L", "µM": "umol/L", "nM": "nmol/L",
    "D": "[D]", "Da": "g/mol", "kDa": "kg/mol",
}
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
    ("mS/cm", "S/m"): 0.1, ("S/m", "mS/cm"): 10.0,
    ("S/cm", "mS/cm"): 1000.0, ("mS/cm", "S/cm"): 0.001,
    ("mS/cm", "uS/cm"): 1000.0, ("uS/cm", "mS/cm"): 0.001,
    ("deg", "rad"): math.pi / 180.0, ("rad", "deg"): 180.0 / math.pi,
    ("kHz", "Hz"): 1000.0, ("Hz", "kHz"): 0.001,
    ("s", "ms"): 1000.0, ("ms", "s"): 0.001,
    ("min", "s"): 60.0, ("s", "min"): 1 / 60.0,
    ("h", "s"): 3600.0, ("s", "h"): 1 / 3600.0,
    ("h", "min"): 60.0, ("min", "h"): 1 / 60.0,
    ("W", "mW"): 1000.0, ("mW", "W"): 0.001,
    ("g/L", "mg/L"): 1000.0, ("mg/L", "g/L"): 0.001,
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
    src_code, dst_code = to_code(src), to_code(dst)
    if src_code == dst_code:
        return value
    if (src_code, dst_code) == ("Cel", "K"):
        return value + 273.15
    if (src_code, dst_code) == ("K", "Cel"):
        return value - 273.15
    if (src_code, dst_code) in _FACTORS:
        return value * _FACTORS[(src_code, dst_code)]
    raise UnitError(f"no conversion {src} -> {dst}")


def convert_quantity(q, dst: str):
    """Return a copy of Quantity `q` converted to canonical unit `dst`, propagating uncertainty."""
    src_code, dst_code = to_code(q.unit), to_code(dst)
    if src_code == dst_code:
        return q.model_copy(deep=True, update={"unit": dst_code, "raw_unit_str": q.raw_unit_str or q.unit})
    val = convert(q.value, src_code, dst_code) if q.value is not None else None
    unc = q.uncertainty.model_copy(deep=True) if q.uncertainty is not None else None
    if unc is not None:
        if (src_code, dst_code) in (("Cel", "K"), ("K", "Cel")):
            # Temperature interval width (std) is invariant between Celsius and Kelvin; bounds shift.
            if unc.low is not None:
                unc.low = convert(unc.low, src_code, dst_code)
            if unc.high is not None:
                unc.high = convert(unc.high, src_code, dst_code)
        else:
            factor = _FACTORS[(src_code, dst_code)]
            if unc.std is not None:
                unc.std = unc.std * abs(factor)
            if unc.low is not None:
                unc.low = unc.low * factor
            if unc.high is not None:
                unc.high = unc.high * factor
    return q.model_copy(
        deep=True,
        update={
            "value": val,
            "unit": dst_code,
            "raw_unit_str": q.raw_unit_str or q.unit,
            "uncertainty": unc,
        },
    )
