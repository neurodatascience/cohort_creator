"""Utilities."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from cohort_creator._utils import _is_dataset_in_openneuro
from cohort_creator._utils import check_participant_listing
from cohort_creator._utils import check_tsv_content
from cohort_creator._utils import get_dataset_url
from cohort_creator._utils import get_participant_ids
from cohort_creator._utils import get_pipeline_version
from cohort_creator._utils import get_sessions
from cohort_creator._utils import is_subject_in_dataset
from cohort_creator._utils import list_all_files
from cohort_creator._utils import validate_dataset_types


def root_dir():
    return Path(__file__).parent.parent


def path_test_data():
    return Path(__file__).parent / "data"


@pytest.fixture
def bids_examples():
    return path_test_data() / "bids-examples"


def test_get_dataset_url():
    assert get_dataset_url("ds000113", "mriqc") is False
    assert isinstance(get_dataset_url("ds000001", "mriqc"), str)


def test_get_pipeline_version(bids_examples):
    assert get_pipeline_version(bids_examples / "ds000001-fmriprep") == "20.2.0rc0"


def test_is_dataset_in_openneuro():
    assert _is_dataset_in_openneuro("ds000001")
    assert not _is_dataset_in_openneuro("foo")


def test_is_subject_in_dataset(bids_examples):
    assert ~is_subject_in_dataset(subject="foo", dataset_pth=bids_examples / "ds001")
    assert is_subject_in_dataset(subject="sub-01", dataset_pth=bids_examples / "ds001")


def test_list_all_files_raw(bids_examples):
    files = list_all_files(
        data_pth=bids_examples / "ds001",
        dataset_type="raw",
        subject="sub-01",
        sessions=[None],
        datatype="anat",
        space="notused",
    )
    assert len(files) == 1
    assert files == ["sub-01/anat/sub-01_T1w.nii.gz"]


def test_list_all_files_func(bids_examples):
    files = list_all_files(
        data_pth=bids_examples / "ds001",
        dataset_type="raw",
        subject="sub-01",
        sessions=[None],
        datatype="func",
        space="notused",
    )
    assert len(files) == 6
    assert sorted(files) == [
        "sub-01/func/sub-01_task-balloonanalogrisktask_run-01_bold.nii.gz",
        "sub-01/func/sub-01_task-balloonanalogrisktask_run-01_events.tsv",
        "sub-01/func/sub-01_task-balloonanalogrisktask_run-02_bold.nii.gz",
        "sub-01/func/sub-01_task-balloonanalogrisktask_run-02_events.tsv",
        "sub-01/func/sub-01_task-balloonanalogrisktask_run-03_bold.nii.gz",
        "sub-01/func/sub-01_task-balloonanalogrisktask_run-03_events.tsv",
    ]


def test_get_participant_ids():
    inpute_file = root_dir() / "inputs" / "participants.tsv"
    participants = pd.read_csv(inpute_file, sep="\t")
    assert get_participant_ids(participants, "ds000002") == ["sub-12", "sub-13"]


def test_check_tsv_content(tmp_path):
    df = pd.DataFrame({"foo": ["ds000001"]})
    df.to_csv(tmp_path / "tmp.tsv", sep="\t", index=False)
    with pytest.raises(ValueError, match="Column 'DatasetName' not found in"):
        check_tsv_content(tmp_path / "tmp.tsv")


def test_check_participant_listing():
    df = pd.DataFrame({"foo": ["ds000001"]})
    with pytest.raises(ValueError, match="Column 'SessionID' not found in"):
        check_participant_listing(df)


def test_get_sessions():
    inpute_file = root_dir() / "inputs" / "participants.tsv"
    participants = pd.read_csv(inpute_file, sep="\t")

    assert get_sessions(participants, "ds000002", "sub-13") == [None]
    assert get_sessions(participants, "ds001226", "sub-CON03") == ["preop"]


def test_validate_dataset_types():
    with pytest.raises(ValueError, match="Dataset type 'foo' is not supported."):
        validate_dataset_types(["foo"])
