import pytest

from assayfold.schema import Molecule, QAItem, Quantity, Reaction, new_record


@pytest.fixture
def mol():
    return new_record("aqsoldb", "t", "1", Molecule(smiles="CCO", name="ethanol"),
                      license="CC0-1.0", origin="real",
                      properties={"log_solubility": Quantity(value=1.1, unit="[logS]")})


@pytest.fixture
def nc_item():
    return new_record("bioprobench", "t", "q1", QAItem(task="x", question="Which step?"),
                      license="CC-BY-NC-4.0", origin="real", tags=["eval_only"])


@pytest.fixture
def rxn():
    return new_record("ord", "t", "r1", Reaction(reactants=["CCO", "CC(=O)O"], products=["CCOC(C)=O"],
                                                  conditions={"temperature": Quantity(value=60, unit="degC")}),
                      license="CC-BY-SA-4.0", origin="real")
