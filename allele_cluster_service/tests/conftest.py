from pathlib import Path

import pandas as pd
import pytest

DATA_DIR = Path(__file__).parent.joinpath("data").resolve()


@pytest.fixture()
def mlst_profiles_all_same():
    """Samples with the same MLST profile."""
    path = DATA_DIR / "mlst_same_profile.csv"
    return pd.read_csv(path).to_csv(sep="\t", index=False)


@pytest.fixture()
def mlst_profiles_different():
    """Samples with the same MLST profile."""
    path = DATA_DIR / "mlst_different_profile.csv"
    return pd.read_csv(path).to_csv(sep="\t", index=False)
