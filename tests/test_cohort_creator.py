"""Utilities."""
from __future__ import annotations

import pandas as pd

from cohort_creator.cohort_creator import construct_cohort
from cohort_creator.cohort_creator import get_data
from cohort_creator.cohort_creator import install_datasets


def test_install_datasets(tmp_path, caplog):
    sourcedata = tmp_path / "sourcedata"
    install_datasets(
        datasets=["ds000001", "foo"],
        sourcedata=sourcedata,
        dataset_types=["raw", "mriqc", "fmriprep"],
    )
    assert "foo not found in openneuro" in caplog.text
    assert (sourcedata / "ds000001").exists()
    assert (sourcedata / "ds000001-mriqc").exists()
    assert (sourcedata / "ds000001-fmriprep").exists()

    # caplog.clear()
    # install_datasets(datasets=["ds000001"], sourcedata=sourcedata, dataset_types= ["raw"])
    # assert "data already present at" in caplog.text


def test_construct_cohort(tmp_path):
    participants = pd.DataFrame(
        {"DatasetID": ["ds000001"], "SubjectID": ["sub-01"], "SessionID": [""]}
    )
    datasets = pd.DataFrame(
        {
            "DatasetID": ["ds000001"],
            "PortalURI": ["https://github.com/OpenNeuroDatasets-JSONLD/ds000001.git"],
        }
    )
    output_dir = tmp_path / "outputs"
    sourcedata = output_dir / "sourcedata"
    dataset_types = ["raw"]
    datatypes = ["anat"]
    install_datasets(
        datasets=["ds000001", "foo"], sourcedata=sourcedata, dataset_types=dataset_types
    )
    get_data(
        sourcedata=sourcedata,
        datasets=datasets,
        participants=participants,
        dataset_types=dataset_types,
        datatypes=datatypes,
        space="not_used_for_raw",
        jobs=2,
    )
    get_data(
        sourcedata=sourcedata,
        datasets=datasets,
        participants=participants,
        dataset_types=dataset_types,
        datatypes=datatypes,
        space="not_used_for_raw",
        jobs=2,
    )
    construct_cohort(
        output_dir=output_dir,
        sourcedata_dir=sourcedata,
        datasets=datasets,
        participants=participants,
        dataset_types=dataset_types,
        datatypes=datatypes,
        space="not_used_for_raw",
    )
    construct_cohort(
        output_dir=output_dir,
        sourcedata_dir=sourcedata,
        datasets=datasets,
        participants=participants,
        dataset_types=dataset_types,
        datatypes=datatypes,
        space="not_used_for_raw",
    )
