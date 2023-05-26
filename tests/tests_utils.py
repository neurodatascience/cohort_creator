"""Utilities."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.utils import get_sessions
from src.utils import validate_dataset_types

# noinspection PyUnresolvedReferences


def test_get_sessions():
    inpute_file = Path(__file__).parent / "inputs" / "participants.tsv"
    participants = pd.read_csv(inpute_file, sep="\t")

    assert get_sessions(participants, "ds000002", "sub-13") == [None]
    assert get_sessions(participants, "ds001226", "sub-CON03") == ["preop"]


def test_validate_dataset_types():
    with pytest.raises(ValueError, match="Dataset type 'foo' is not supported."):
        validate_dataset_types(["foo"])
