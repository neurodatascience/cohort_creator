"""Utilities."""
from __future__ import annotations

from pathlib import Path

from cohort_creator.cohort_creator import main


def root_dir():
    return Path(__file__).parent.parent


def test_main(tmp_path):
    datasets_listing = root_dir() / "inputs" / "datasets.tsv"
    participants_listing = root_dir() / "inputs" / "participants.tsv"
    output_dir = tmp_path
    action = "all"
    datatypes = ["anat"]
    dataset_types = ["raw", "mriqc", "fmriprep"]
    verbosity = 3
    jobs = 3

    main(
        datasets_listing=datasets_listing,
        participants_listing=participants_listing,
        output_dir=output_dir,
        action=action,
        dataset_types=dataset_types,
        datatypes=datatypes,
        space="MNI152NLin2009cAsym",
        verbosity=verbosity,
        jobs=jobs,
    )
