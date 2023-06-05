"""Utilities."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from bids import BIDSLayout

from .conftest import path_test_data
from .conftest import root_dir
from cohort_creator._utils import _is_dataset_in_openneuro
from cohort_creator._utils import check_participant_listing
from cohort_creator._utils import check_tsv_content
from cohort_creator._utils import create_ds_description
from cohort_creator._utils import get_anat_files
from cohort_creator._utils import get_dataset_url
from cohort_creator._utils import get_func_files
from cohort_creator._utils import get_institution
from cohort_creator._utils import get_participant_ids
from cohort_creator._utils import get_pipeline_version
from cohort_creator._utils import get_sessions
from cohort_creator._utils import is_subject_in_dataset
from cohort_creator._utils import list_all_files
from cohort_creator._utils import return_target_pth
from cohort_creator._utils import set_name
from cohort_creator._utils import set_version
from cohort_creator._utils import validate_dataset_types


def test_get_dataset_url():
    assert get_dataset_url("ds000113", "mriqc") is False
    assert isinstance(get_dataset_url("ds000001", "mriqc"), str)


def test_get_pipeline_version(bids_examples):
    assert get_pipeline_version(bids_examples / "ds000001-fmriprep") == "20.2.0rc0"


def test_set_version(bids_examples, tmp_path):
    assert set_version(bids_examples / "ds000001-fmriprep") == "20.2.0rc0"
    assert set_version(Path("foo")) == "UNKNOWN"
    assert set_version(bids_examples) == "UNKNOWN"

    derivative_path = tmp_path / "fmriprep-foobar"
    assert set_version(derivative_path) == "21.0.1"

    derivative_path = tmp_path / "mriqc-foobar"
    assert set_version(derivative_path) == "0.16.1"


def test_set_name(bids_examples, tmp_path):
    assert set_name(bids_examples / "ds000001-fmriprep") == "fMRIPrep"
    assert set_name(Path("foo")) == "foo"
    assert set_name(bids_examples) == "UNKNOWN"

    derivative_path = tmp_path / "fmriprep-foobar"
    assert set_name(derivative_path) == "fMRIPrep"

    derivative_path = tmp_path / "mriqc-foobar"
    assert set_name(derivative_path) == "MRIQC"


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


def test_get_institution(bids_examples):
    institution_name, institution_address = get_institution(bids_examples / "pet005")
    assert institution_name == ["Rigshospitalet"]
    assert institution_address == ["Blegdamsvej_9_Copenhagen_District_DK_2100"]

    institution_name, institution_address = get_institution(bids_examples / "ds001")
    assert institution_name == [None]
    assert institution_address == [None]


def test_create_ds_description(tmp_path):
    create_ds_description(tmp_path)
    assert (tmp_path / "dataset_description.json").exists()


@pytest.mark.parametrize(
    "dataset_type, dataset, src_pth, expected",
    [
        ("raw", "foo", None, ["study-foo"]),
        ("fmriprep", "foo", None, ["study-foo", "derivatives", "fmriprep"]),
        (
            "fmriprep",
            "foo",
            path_test_data() / "bids-examples" / "ds000001-fmriprep",
            ["study-foo", "derivatives", "fmriprep-20.2.0rc0"],
        ),
    ],
)
def test_return_target_pth(dataset_type, dataset, src_pth, expected):
    output_dir = Path().cwd() / "outputs"
    value = return_target_pth(
        output_dir=output_dir, dataset_type=dataset_type, dataset=dataset, src_pth=src_pth
    )
    assert value.relative_to(output_dir) == Path(*expected)


def test_get_anat_files(bids_examples):
    input_dir = bids_examples / "ds006"
    layout = BIDSLayout(input_dir, validate=False, derivatives=False)

    files = get_anat_files(layout, sub="01", ses=None, extension="nii(.gz)?")
    assert len(files) == 2

    files = get_anat_files(layout, sub="01", ses="post", extension="nii(.gz)?")
    assert len(files) == 1

    files = get_anat_files(layout, sub="01")
    assert len(files) == 0


def test_get_func_files(bids_examples):
    input_dir = bids_examples / "ds006"
    layout = BIDSLayout(input_dir, validate=False, derivatives=False)

    files = get_func_files(layout, sub="01", ses=None, extension="nii(.gz)?")
    assert len(files) == 12

    files = get_func_files(layout, sub="01", ses="post", extension="nii(.gz)?")
    assert len(files) == 6

    files = get_func_files(layout, sub="01")
    assert len(files) == 0
