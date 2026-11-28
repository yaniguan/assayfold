"""Small unit table: raw unit strings -> UCUM-style codes, plus a few safe conversions.

No external unit library. Units we do not know raise in strict mode.
Codes in square brackets ([Eh], [logS], [m/z], [U]) are local codes, not official UCUM.
Case-sensitive SI/UCUM symbols (U vs u, mS vs ms, mHz vs MHz, d vs D, Da vs da) live in
`_CASED` so lowercasing never turns one valid unit into a different one.
"""

import math
import re

# Unambiguous case-insensitive aliases (full words and case-invariant symbols, spaces removed)
_ALIASES = {
    "ul": "uL", "µl": "uL", "μl": "uL", "microliter": "uL", "microliters": "uL",
    "ml": "mL", "milliliter": "mL", "milliliters": "mL",
    "l": "L", "liter": "L", "liters": "L",
    "nl": "nL", "nanoliter": "nL", "nanoliters": "nL",
    "g": "g", "mg": "mg", "ug": "ug", "µg": "ug", "μg": "ug", "kg": "kg",
    "gram": "g", "grams": "g", "milligram": "mg", "milligrams": "mg",
    "microgram": "ug", "micrograms": "ug", "kilogram": "kg", "kilograms": "kg",
    "g/mol": "g/mol", "dalton": "g/mol", "daltons": "g/mol", "amu": "g/mol",
    "kg/mol": "kg/mol", "kilodalton": "kg/mol", "kilodaltons": "kg/mol",
    "mol/l": "mol/L", "molar": "mol/L",
    "mmol/l": "mmol/L", "millimolar": "mmol/L",
    "umol/l": "umol/L", "µmol/l": "umol/L", "μmol/l": "umol/L", "micromolar": "umol/L",
    "nmol/l": "nmol/L", "nanomolar": "nmol/L",
    "mol": "mol", "mmol": "mmol",
    "mol/kg": "mol/kg", "mmol/kg": "mmol/kg", "molal": "mol/kg",
    "g/l": "g/L", "gl-1": "g/L", "g/liter": "g/L", "mg/ml": "g/L", "mg/l": "mg/L",
    "°c": "Cel", "degc": "Cel", "celsius": "Cel", "cel": "Cel",
    "kelvin": "K",
    "millisecond": "ms", "milliseconds": "ms",
    "microsecond": "us", "microseconds": "us",
    "nanosecond": "ns", "nanoseconds": "ns",
    "sec": "s", "second": "s", "seconds": "s",
    "min": "min", "minute": "min", "minutes": "min",
    "h": "h", "hr": "h", "hrs": "h", "hour": "h", "hours": "h",
    "day": "d", "days": "d",
    "enzymeunit": "[U]", "enzymeunits": "[U]",
    "siemens": "S", "millisiemens": "mS", "microsiemens": "uS", "megasiemens": "MS",
    "hartree": "[Eh]", "ha": "[Eh]", "eh": "[Eh]", "[eh]": "[Eh]",
    "ev": "eV", "electronvolt": "eV", "electronvolts": "eV",
    "kcal/mol": "kcal/mol", "kj/mol": "kJ/mol",
    "angstrom": "Ao", "angstroms": "Ao", "å": "Ao", "ao": "Ao", "ang": "Ao", "bohr": "[a0]",
    "ev/angstrom": "eV/Ao", "ev/å": "eV/Ao", "ev/ao": "eV/Ao",
    "hartree/bohr": "[Eh]/[a0]",
    "debye": "[D]", "debyes": "[D]", "[d]": "[D]",
    "bohr^3": "[a0]3", "a0^3": "[a0]3", "bohr3": "[a0]3", "bohr^2": "[a0]2", "a0^2": "[a0]2",
    "cal/molk": "cal/(mol.K)", "cal/(mol·k)": "cal/(mol.K)", "cal/(mol.k)": "cal/(mol.K)",
    "hertz": "Hz", "millihertz": "mHz", "kilohertz": "kHz", "megahertz": "MHz", "gigahertz": "GHz",
    "fps": "Hz",
    "nm": "nm", "nanometer": "nm", "nanometers": "nm",
    "cm-1": "/cm", "cm^-1": "/cm", "cm⁻¹": "/cm", "1/cm": "/cm", "/cm": "/cm",
    "wavenumber": "/cm", "ramanshift": "/cm", "ramanshift(cm^-1)": "/cm",
    "deg": "deg", "°": "deg", "degree": "deg", "degrees": "deg",
    "2theta": "deg", "2-theta": "deg", "deg2theta": "deg", "deg(2theta)": "deg",
    "rad": "rad", "radian": "rad", "radians": "rad",
    "m/z": "[m/z]", "mz": "[m/z]", "[m/z]": "[m/z]", "th": "[m/z]",
    "thomson": "[m/z]", "da/e": "[m/z]",
    "watt": "W", "watts": "W", "milliwatt": "mW", "milliwatts": "mW",
    "kilowatt": "kW", "megawatt": "MW",
    "db": "dB", "decibel": "dB", "decibels": "dB",
    "pascal": "Pa", "pascals": "Pa", "kilopascal": "kPa", "megapascal": "MPa",
    "bar": "bar", "atm": "atm",
    "{counts}": "{counts}", "counts": "{counts}", "cnt": "{counts}",
    "{arb}": "{arb}", "a.u.": "{arb}", "au": "{arb}", "arb.units": "{arb}",
    "ppm": "[ppm]", "%": "%", "percent": "%", "percentage": "%",
    "rpm": "{rpm}", "xg": "{g-force}", "g-force": "{g-force}", "rcf": "{g-force}",
    "log(mol/l)": "[logS]", "logs": "[logS]", "log10(mol/l)": "[logS]", "[logs]": "[logS]",
    "logd": "[logD]", "logd7.4": "[logD]", "logd(ph7.4)": "[logD]", "[logd]": "[logD]",
    "ph": "[pH]", "[ph]": "[pH]",
    "absorbance": "1", "abs": "1",
    "1": "1", "": "1", "unitless": "1", "dimensionless": "1",
}

# Case-sensitive symbols (whitespace stripped, case preserved): checked before lowercasing.
_CASED = {
    "M": "mol/L", "mM": "mmol/L", "uM": "umol/L", "µM": "umol/L", "μM": "umol/L",
    "nM": "nmol/L", "pM": "pmol/L",
    "U": "[U]", "[U]": "[U]", "mU": "m[U]", "U/mL": "[U]/mL", "U/L": "[U]/L",
    "u": "g/mol", "Da": "g/mol", "kDa": "kg/mol",
    "d": "d", "D": "[D]",
    "s": "s", "S": "S",
    "ms": "ms", "mS": "mS", "MS": "MS",
    "us": "us", "µs": "us", "μs": "us",
    "uS": "uS", "µS": "uS", "μS": "uS",
    "ns": "ns",
    "Hz": "Hz", "mHz": "mHz", "kHz": "kHz", "MHz": "MHz", "GHz": "GHz",
    "W": "W", "mW": "mW", "kW": "kW", "MW": "MW",
    "Pa": "Pa", "mPa": "mPa", "kPa": "kPa", "MPa": "MPa",
    "C": "Cel", "K": "K",
    "mS/cm": "mS/cm", "mScm-1": "mS/cm", "mScm^-1": "mS/cm", "mS·cm-1": "mS/cm",
    "S/cm": "S/cm", "Scm-1": "S/cm", "Scm^-1": "S/cm",
    "S/m": "S/m", "Sm-1": "S/m", "Sm^-1": "S/m",
    "uS/cm": "uS/cm", "µS/cm": "uS/cm", "μS/cm": "uS/cm",
}
KNOWN = set(_ALIASES.values()) | set(_CASED.values())

# (from, to) -> multiplicative factor for safe conversions
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
    ("S", "mS"): 1000.0, ("mS", "S"): 0.001,
    ("mS", "uS"): 1000.0, ("uS", "mS"): 0.001,
    ("MS", "S"): 1_000_000.0, ("S", "MS"): 1e-6,
    ("deg", "rad"): math.pi / 180.0, ("rad", "deg"): 180.0 / math.pi,
    ("Hz", "mHz"): 1000.0, ("mHz", "Hz"): 0.001,
    ("kHz", "Hz"): 1000.0, ("Hz", "kHz"): 0.001,
    ("MHz", "Hz"): 1_000_000.0, ("Hz", "MHz"): 1e-6,
    ("GHz", "Hz"): 1_000_000_000.0, ("Hz", "GHz"): 1e-9,
    ("s", "ms"): 1000.0, ("ms", "s"): 0.001,
    ("s", "us"): 1_000_000.0, ("us", "s"): 1e-6,
    ("ms", "us"): 1000.0, ("us", "ms"): 0.001,
    ("min", "s"): 60.0, ("s", "min"): 1 / 60.0,
    ("h", "s"): 3600.0, ("s", "h"): 1 / 3600.0,
    ("h", "min"): 60.0, ("min", "h"): 1 / 60.0,
    ("d", "s"): 86400.0, ("s", "d"): 1 / 86400.0,
    ("d", "h"): 24.0, ("h", "d"): 1 / 24.0,
    ("d", "min"): 1440.0, ("min", "d"): 1 / 1440.0,
    ("W", "mW"): 1000.0, ("mW", "W"): 0.001,
    ("kW", "W"): 1000.0, ("W", "kW"): 0.001,
    ("MW", "W"): 1_000_000.0, ("W", "MW"): 1e-6,
    ("g/L", "mg/L"): 1000.0, ("mg/L", "g/L"): 0.001,
}


class UnitError(ValueError):
    pass


def to_code(raw: str, strict: bool = True) -> str:
    """Map a raw unit string to its canonical code. Unknown -> UnitError (strict) or raw."""
    if raw in KNOWN:
        return raw
    s = str(raw).strip()
    if s in KNOWN:
        return s
    no_ws = re.sub(r"\s+", "", s)
    if no_ws in _CASED:
        return _CASED[no_ws]
    if no_ws in KNOWN:
        return no_ws
    key = no_ws.lower()
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
    is_temp = (src_code, dst_code) in (("Cel", "K"), ("K", "Cel"))
    if not is_temp and (src_code, dst_code) not in _FACTORS:
        raise UnitError(f"no conversion {q.unit} -> {dst}")
    val = convert(q.value, src_code, dst_code) if q.value is not None else None
    unc = q.uncertainty.model_copy(deep=True) if q.uncertainty is not None else None
    if unc is not None:
        if is_temp:
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
