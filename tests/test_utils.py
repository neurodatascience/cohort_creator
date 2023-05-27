"""Utilities."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from cohort_creator.utils import check_tsv_content
from cohort_creator.utils import get_participant_ids
from cohort_creator.utils import get_sessions
from cohort_creator.utils import validate_dataset_types


def root_dir():
    return Path(__file__).parent.parent


def test_get_participant_ids():
    inpute_file = root_dir() / "inputs" / "participants.tsv"
    participants = pd.read_csv(inpute_file, sep="\t")
    assert get_participant_ids(participants, "ds000002") == ["sub-03", "sub-12", "sub-13"]


def test_check_tsv_content(tmp_path):
    df = pd.DataFrame({"foo": ["ds000001"]})
    df.to_csv(tmp_path / "tmp.tsv", sep="\t", index=False)
    with pytest.raises(ValueError, match="Column 'DatasetName' not found in"):
        check_tsv_content(tmp_path / "tmp.tsv")


def test_get_sessions():
    inpute_file = root_dir() / "inputs" / "participants.tsv"
    participants = pd.read_csv(inpute_file, sep="\t")

    assert get_sessions(participants, "ds000002", "sub-13") == [None]
    assert get_sessions(participants, "ds001226", "sub-CON03") == ["preop"]


def test_validate_dataset_types():
    with pytest.raises(ValueError, match="Dataset type 'foo' is not supported."):
        validate_dataset_types(["foo"])
