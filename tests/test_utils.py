"""Utilities."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from bids import BIDSLayout

from .conftest import path_test_data
from .conftest import root_dir
from cohort_creator._utils import _is_dataset_in_openneuro
from cohort_creator._utils import check_participant_listing
from cohort_creator._utils import check_tsv_content
from cohort_creator._utils import create_ds_description
from cohort_creator._utils import create_tsv_participant_session_in_datasets
from cohort_creator._utils import get_anat_files
from cohort_creator._utils import get_bids_filter
from cohort_creator._utils import get_dataset_url
from cohort_creator._utils import get_filters
from cohort_creator._utils import get_func_files
from cohort_creator._utils import get_institution
from cohort_creator._utils import get_list_datasets_to_install
from cohort_creator._utils import get_participant_ids
from cohort_creator._utils import get_pipeline_version
from cohort_creator._utils import get_sessions
from cohort_creator._utils import is_subject_in_dataset
from cohort_creator._utils import list_all_files_with_filter
from cohort_creator._utils import list_participants_in_dataset
from cohort_creator._utils import load_dataset_listing
from cohort_creator._utils import load_participant_listing
from cohort_creator._utils import return_target_pth
from cohort_creator._utils import set_name
from cohort_creator._utils import set_version
from cohort_creator._utils import validate_dataset_types


def test_create_tsv_participant_session_in_datasets(bids_examples, tmp_path):
    tsv_file = create_tsv_participant_session_in_datasets(
        dataset_paths=[bids_examples / "ds001", bids_examples / "ds006"], output_dir=tmp_path
    )
    assert tsv_file.exists()
    df = pd.read_csv(tsv_file, sep="\t")

    assert df.columns.tolist() == ["DatasetID", "SubjectID", "SessionID", "SessionPath"]

    assert df["DatasetID"].unique().tolist() == ["ds001", "ds006"]

    nb_sub_ds001 = len(list_participants_in_dataset(bids_examples / "ds001"))
    nb_sub_ds006 = len(list_participants_in_dataset(bids_examples / "ds006"))
    nb_ses_ds006 = 2
    assert len(df) == nb_sub_ds001 + nb_sub_ds006 * nb_ses_ds006

    assert df["SessionID"].unique().tolist() == [np.nan, "ses-post", "ses-pre"]


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


def test_check_tsv_content(tmp_path):
    df = pd.DataFrame({"foo": ["ds000001"]})
    df.to_csv(tmp_path / "tmp.tsv", sep="\t", index=False)
    with pytest.raises(ValueError, match="Column 'DatasetID' not found in"):
        check_tsv_content(tmp_path / "tmp.tsv")


def test_check_participant_listing():
    df = pd.DataFrame({"foo": ["ds000001"]})
    with pytest.raises(ValueError, match="Column 'SubjectID' not found in"):
        check_participant_listing(df)


def test_get_sessions():
    input_file = root_dir() / "tests" / "data" / "participants.tsv"
    participants = load_participant_listing(input_file)

    assert get_sessions(participants, "ds000002", "sub-13") == [None]
    assert get_sessions(participants, "ds001226", "sub-CON03") == ["ses-postop", "ses-preop"]


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


def test_get_bids_filter(tmp_path):
    bids_filter = get_bids_filter()
    assert all(key in ["raw", "mriqc", "fmriprep"] for key in bids_filter.keys())

    tmp_filter = tmp_path / "filter.json"
    content = {"raw": {"eeg": {"datatype": "eeg", "suffix": "eeg", "ext": "set"}}}
    with open(tmp_filter, "w") as f:
        json.dump(content, f)
    bids_filter = get_bids_filter(tmp_filter)
    assert bids_filter == content


def test_get_bids_filter_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        get_bids_filter(Path().cwd() / "foo")

    tmp_filter = tmp_path / "filter.json"
    content = {"foo": {"bar": "baz"}}
    with open(tmp_filter, "w") as f:
        json.dump(content, f)
    with pytest.raises(TypeError, match="must be JSON object"):
        get_bids_filter(tmp_filter)

    tmp_filter = tmp_path / "filter.json"
    content = {"foo": {"bar": {"baz": "qux"}}}
    with open(tmp_filter, "w") as f:
        json.dump(content, f)
    with pytest.raises(ValueError, match="not found in"):
        get_bids_filter(tmp_filter)


def test_get_filters():
    filters = get_filters(dataset_type="raw", datatype="anat")
    assert sorted(filters.keys()) == ["t1w", "t2w"]

    filters = get_filters(dataset_type="raw", datatype="func")
    assert sorted(filters.keys()) == ["bold", "events"]


def test_list_all_files_with_filter_raw(bids_examples):
    dataset_type = "raw"
    datatype = "anat"
    filters = get_filters(dataset_type=dataset_type, datatype=datatype)
    files = list_all_files_with_filter(
        data_pth=bids_examples / "ds001",
        dataset_type=dataset_type,
        filters=filters,
        subject="sub-01",
        sessions=[None],
        datatype=datatype,
    )
    assert len(files) == 1
    assert files == ["sub-01/anat/sub-01_T1w.nii.gz"]


@pytest.mark.parametrize(
    "sessions, expected",
    (
        ([None], []),
        (["ses-pre"], ["sub-01/ses-pre/anat/sub-01_ses-pre_T1w.nii.gz"]),
        (
            ["ses-pre", "ses-post"],
            [
                "sub-01/ses-post/anat/sub-01_ses-post_T1w.nii.gz",
                "sub-01/ses-pre/anat/sub-01_ses-pre_T1w.nii.gz",
            ],
        ),
        (["foo"], []),
    ),
)
def test_list_all_files_with_filter_raw_with_sessions(bids_examples, sessions, expected):
    dataset_type = "raw"
    datatype = "anat"
    filters = get_filters(dataset_type=dataset_type, datatype=datatype)
    files = list_all_files_with_filter(
        data_pth=bids_examples / "ds006",
        dataset_type=dataset_type,
        filters=filters,
        subject="sub-01",
        sessions=sessions,
        datatype=datatype,
    )
    assert files == expected


def test_list_all_files_with_filter_func(bids_examples):
    dataset_type = "raw"
    datatype = "func"
    filters = get_filters(dataset_type=dataset_type, datatype=datatype)
    files = list_all_files_with_filter(
        data_pth=bids_examples / "ds001",
        dataset_type=dataset_type,
        filters=filters,
        subject="sub-01",
        sessions=[None],
        datatype=datatype,
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


def test_list_all_files_with_filter_anat_fmriprep(bids_examples):
    dataset_type = "fmriprep"
    datatype = "anat"
    filters = get_filters(dataset_type=dataset_type, datatype=datatype)
    files = list_all_files_with_filter(
        data_pth=bids_examples / "ds000001-fmriprep",
        dataset_type=dataset_type,
        filters=filters,
        subject="sub-10",
        sessions=[None],
        datatype=datatype,
        space=None,
    )
    assert len(files) == 4
    assert files == [
        "sub-10/anat/sub-10_desc-preproc_T1w.json",
        "sub-10/anat/sub-10_desc-preproc_T1w.nii.gz",
        "sub-10/anat/sub-10_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.json",
        "sub-10/anat/sub-10_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.nii.gz",
    ]


def test_list_all_files_with_filter_func_fmriprep(bids_examples):
    dataset_type = "fmriprep"
    datatype = "func"
    filters = get_filters(dataset_type=dataset_type, datatype=datatype)
    files = list_all_files_with_filter(
        data_pth=bids_examples / "ds000001-fmriprep",
        dataset_type=dataset_type,
        filters=filters,
        subject="sub-10",
        sessions=[None],
        datatype=datatype,
        space=None,
    )
    assert len(files) == 12
    assert files == [
        "sub-10/func/sub-10_task-balloonanalogrisktask_run-1_desc-confounds_timeseries.json",
        "sub-10/func/sub-10_task-balloonanalogrisktask_run-1_desc-confounds_timeseries.tsv",
        "sub-10/func/sub-10_task-balloonanalogrisktask_run-1_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.json",
        "sub-10/func/sub-10_task-balloonanalogrisktask_run-1_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.nii.gz",
        "sub-10/func/sub-10_task-balloonanalogrisktask_run-2_desc-confounds_timeseries.json",
        "sub-10/func/sub-10_task-balloonanalogrisktask_run-2_desc-confounds_timeseries.tsv",
        "sub-10/func/sub-10_task-balloonanalogrisktask_run-2_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.json",
        "sub-10/func/sub-10_task-balloonanalogrisktask_run-2_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.nii.gz",
        "sub-10/func/sub-10_task-balloonanalogrisktask_run-3_desc-confounds_timeseries.json",
        "sub-10/func/sub-10_task-balloonanalogrisktask_run-3_desc-confounds_timeseries.tsv",
        "sub-10/func/sub-10_task-balloonanalogrisktask_run-3_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.json",
        "sub-10/func/sub-10_task-balloonanalogrisktask_run-3_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.nii.gz",
    ]


def test_load_dataset_listing():
    datasets_listing_file = root_dir() / "inputs" / "dataset-results.tsv"
    load_dataset_listing([str(datasets_listing_file)])
    load_dataset_listing(["ds000001", "ds000002"])


def test_get_list_datasets_to_install():
    participants_listing_file = root_dir() / "inputs" / "participant-results.tsv"
    participant_listing = load_participant_listing(participants_listing_file)
    datasets_listing_file = root_dir() / "inputs" / "dataset-results.tsv"
    dataset_listing = load_dataset_listing([str(datasets_listing_file)])

    datasets_to_install = get_list_datasets_to_install(dataset_listing, participant_listing)

    expected = [
        "ds001454",
        "ds001408",
        "ds001868",
        "ds003416",
        "ds003425",
        "ds000244",
        "ds003192",
        "ds002419",
        "ds000220",
        "ds002799",
        "ds001705",
        "ds002685",
        "ds003453",
        "ds003465",
        "ds000006",
        "ds003452",
    ]
    assert len(datasets_to_install) == len(expected)
    assert all(x in expected for x in datasets_to_install)


def test_get_list_datasets_to_install_with_no_participants_tsv():
    dataset_listing = pd.DataFrame({"DatasetID": ["foo", "bar"]})

    datasets_to_install = get_list_datasets_to_install(dataset_listing)

    expected = [
        "foo",
        "bar",
    ]
    assert len(datasets_to_install) == len(expected)
    assert all(x in expected for x in datasets_to_install)


def test_get_participant_ids():
    participants_listing_file = root_dir() / "inputs" / "participant-results.tsv"
    participants = load_participant_listing(participants_listing_file)
    datasets_listing_file = root_dir() / "inputs" / "dataset-results.tsv"
    datasets = load_dataset_listing([str(datasets_listing_file)])

    participant_ids = get_participant_ids(
        datasets=datasets, participants=participants, dataset_name="ds000244"
    )

    expected = ["sub-08", "sub-11"]

    assert len(participant_ids) == len(expected)
    assert all(x in expected for x in participant_ids)


def test_list_participants_in_dataset(bids_examples):
    participants_ids = list_participants_in_dataset(bids_examples / "ieeg_visual")

    assert all(x in ["sub-01", "sub-02"] for x in participants_ids)
