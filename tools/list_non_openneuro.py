"""List datasets contents on openneuro and write the results in a tsv file.

Also checks for derivatives folders for mriqc, frmiprep and freesurfer.

Rerun to update values of "old" datasets.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from cohort_creator.data._update import init_dataset
from cohort_creator.data._update import list_datasets_in_dir
from cohort_creator.logger import cc_logger

DEBUG = False
UPDATE_MERGE = False

cc_log = cc_logger()

cc_log.setLevel("INFO")

logging.getLogger("datalad").setLevel(logging.WARNING)
logging.getLogger("datalad.gitrepo").setLevel(logging.ERROR)


def main() -> None:
    datasets = init_dataset()

    base_path = Path(__file__).parent / "tmp"

    datasets = list_datasets_in_dir(
        datasets,
        base_path / "abide",
        debug=DEBUG,
        dataset_name_prefix="",
        study_prefix="ABIDE_",
        update_merge=UPDATE_MERGE,
    )

    datasets = list_datasets_in_dir(
        datasets,
        base_path / "abide2",
        debug=DEBUG,
        dataset_name_prefix="",
        study_prefix="ABIDE2_",
        update_merge=UPDATE_MERGE,
    )

    datasets = list_datasets_in_dir(
        datasets,
        base_path / "adhd200",
        debug=DEBUG,
        dataset_name_prefix="",
        study_prefix="ADHD200_",
        update_merge=UPDATE_MERGE,
    )

    datasets = list_datasets_in_dir(
        datasets,
        base_path / "corr",
        debug=DEBUG,
        dataset_name_prefix="",
        study_prefix="CORR_",
        update_merge=UPDATE_MERGE,
    )

    datasets = list_datasets_in_dir(
        datasets,
        base_path / "cneuromod",
        debug=DEBUG,
        dataset_name_prefix="",
        study_prefix="CNEUROMOD_",
        include=[
            "anat",
            "friends",
            "harrypotter",
            "hcptrt",
            "movie10",
            "shinobi",
            "shinobi_training",
        ],
        update_merge=UPDATE_MERGE,
    )

    datasets_df = pd.DataFrame.from_dict(datasets)
    datasets_df = datasets_df.sort_values("name")

    output_file = Path(__file__).parent.parent / "non_openneuro.tsv"
    datasets_df.to_csv(output_file, index=False, sep="\t")

    print("data saved to:", output_file)


if __name__ == "__main__":
    main()
