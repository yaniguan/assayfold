import pytest

from assayfold import units


@pytest.mark.parametrize("raw,code", [("microliter", "uL"), ("µL", "uL"), ("°C", "Cel"),
                                      ("Hartree", "[Eh]"), ("Å", "Ao"), ("M", "mol/L"),
                                      ("mM", "mmol/L"), ("kcal/mol", "kcal/mol"), ("cm-1", "/cm")])
def test_aliases(raw, code):
    assert units.to_code(raw) == code


def test_autoprotocol_string():
    assert units.parse_quantity("25:microliter")[:2] == (25.0, "uL")
    assert units.parse_quantity("1.5 mL")[:2] == (1.5, "mL")


def test_unknown_unit_strict_and_lenient():
    with pytest.raises(units.UnitError):
        units.to_code("furlong")
    assert units.to_code("furlong", strict=False) == "furlong"


def test_conversions():
    assert units.convert(1.0, "[Eh]", "eV") == pytest.approx(27.211386, rel=1e-6)
    assert units.convert(1.0, "kcal/mol", "kJ/mol") == pytest.approx(4.184)
    assert units.convert(25.0, "Cel", "K") == pytest.approx(298.15)
    with pytest.raises(units.UnitError):
        units.convert(1.0, "eV", "uL")
