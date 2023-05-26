"""Utilities."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from utils import get_sessions

# noinspection PyUnresolvedReferences


def test_get_sessions():
    inpute_file = Path(__file__).parent / "inputs" / "participants.tsv"
    participants = pd.read_csv(inpute_file, sep="\t")

    assert get_sessions(participants, "ds000002", "sub-13") == [None]
    assert get_sessions(participants, "ds001226", "sub-CON03") == ["preop"]
