"""Utilities."""

from __future__ import annotations

from cohort_creator._utils import sourcedata
from cohort_creator.copy_files import copy_this_subject, copy_top_files
from cohort_creator.main import install_datasets


def test_copy_top_files(output_dir):
    dataset_types = ["raw"]
    install_datasets(
        datasets=["ds000001", "foo"], output_dir=output_dir, dataset_types=dataset_types
    )
    copy_top_files(
        src_pth=sourcedata(output_dir) / "ds000001",
        target_pth=output_dir / "study-ds000001" / "bids",
        datatypes=["anat", "func"],
    )

    assert (
        output_dir / "study-ds000001" / "bids" / "task-balloonanalogrisktask_bold.json"
    ).exists()
    assert (output_dir / "study-ds000001" / "bids" / "README").exists()
    assert (output_dir / "study-ds000001" / "bids" / "dataset_description.json").exists()


def test_copy_this_subject(output_dir):
    dataset_types = ["raw"]
    datatypes = ["anat"]
    install_datasets(datasets=["ds000001"], output_dir=output_dir, dataset_types=dataset_types)
    copy_this_subject(
        subject="sub-01",
        datatypes=datatypes,
        dataset_type=dataset_types[0],
        src_pth=sourcedata(output_dir) / "ds000001",
        target_pth=output_dir / "study-ds000001" / "bids",
    )

    assert (
        output_dir / "study-ds000001" / "bids" / "sub-01" / "anat" / "sub-03_T1w.nii.gz"
    ).exists()
