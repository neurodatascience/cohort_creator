"""Utilities."""
from __future__ import annotations

import pandas as pd
import pytest

from cohort_creator._cli import create_yoda
from cohort_creator._utils import sourcedata
from cohort_creator.cohort_creator import construct_cohort
from cohort_creator.cohort_creator import get_data
from cohort_creator.cohort_creator import install_datasets


@pytest.fixture
def output_dir(tmp_path):
    create_yoda(output_dir=tmp_path)
    return tmp_path


def test_install_datasets(output_dir, caplog):
    install_datasets(
        datasets=["ds000001", "foo"],
        output_dir=output_dir,
        dataset_types=["raw", "mriqc", "fmriprep"],
    )
    assert "foo not found in openneuro" in caplog.text
    assert (sourcedata(output_dir) / "ds000001").exists()
    assert (sourcedata(output_dir) / "ds000001-mriqc").exists()
    assert (sourcedata(output_dir) / "ds000001-fmriprep").exists()

    # caplog.clear()
    # install_datasets(datasets=["ds000001"], sourcedata=sourcedata, dataset_types= ["raw"])
    # assert "data already present at" in caplog.text


def test_install_datasets_create_participant_listing(output_dir):
    install_datasets(
        datasets=["ds000002"],
        output_dir=output_dir,
        dataset_types=["raw"],
        generate_participant_listing=True,
    )
    (output_dir / "code" / "participants.tsv").exists()


def test_construct_cohort(output_dir):
    participants = pd.DataFrame(
        {"DatasetID": ["ds000001"], "SubjectID": ["sub-01"], "SessionID": [""]}
    )
    datasets = pd.DataFrame(
        {
            "DatasetID": ["ds000001"],
            "PortalURI": ["https://github.com/OpenNeuroDatasets-JSONLD/ds000001.git"],
        }
    )
    dataset_types = ["raw"]
    datatypes = ["anat"]
    install_datasets(
        datasets=["ds000001", "foo"], output_dir=output_dir, dataset_types=dataset_types
    )
    get_data(
        output_dir=output_dir,
        datasets=datasets,
        participants=participants,
        dataset_types=dataset_types,
        datatypes=datatypes,
        space="not_used_for_raw",
        jobs=2,
    )
    get_data(
        output_dir=output_dir,
        datasets=datasets,
        participants=participants,
        dataset_types=dataset_types,
        datatypes=datatypes,
        space="not_used_for_raw",
        jobs=2,
    )
    construct_cohort(
        output_dir=output_dir,
        datasets=datasets,
        participants=participants,
        dataset_types=dataset_types,
        datatypes=datatypes,
        space="not_used_for_raw",
    )
    construct_cohort(
        output_dir=output_dir,
        datasets=datasets,
        participants=participants,
        dataset_types=dataset_types,
        datatypes=datatypes,
        space="not_used_for_raw",
    )
