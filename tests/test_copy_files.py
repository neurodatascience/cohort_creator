"""Utilities."""

from __future__ import annotations

import pandas as pd

from cohort_creator.main import install_datasets
from cohort_creator.copy_files import copy_top_files, copy_files


def test_copy_top_files(output_dir):
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
    copy_top_files(src_pth=src_pth, target_pth=target_pth, datatypes=datatypes)


def test_copy_files(output_dir):
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
    copy_files(
        output_dir=output_dir,
        datasets=datasets,
        participants=participants,
        dataset_types=dataset_types,
        datatypes=datatypes,
        space="not_used_for_raw",
        task="*",
    )

    assert (output_dir / "study-ds000001" / "bids" / 'sub-01' / "anat" / "sub-03_T1w.nii.gzz").exists()


