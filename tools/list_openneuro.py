"""List datasets contents on openneuro and write the results in a tsv file.

Also checks for derivatives folders for mriqc, frmiprep and freesurfer.

Rerun to update values of "old" datasets.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from cohort_creator.data._update import config
from cohort_creator.data._update import init_dataset
from cohort_creator.data._update import install_missing_datasets
from cohort_creator.data._update import list_datasets_in_dir
from cohort_creator.data._update import list_openneuro_derivatives
from cohort_creator.data._update import OPENNEURO
from cohort_creator.logger import cc_logger

cc_log = cc_logger()

cc_log.setLevel("INFO")

DEBUG = False


def main() -> None:
    install_missing_datasets(use_superdataset=True)

    list_openneuro_derivatives()

    datasets = init_dataset()

    path = Path(config()["local_paths"]["datalad"][OPENNEURO])
    datasets = list_datasets_in_dir(datasets, path, debug=DEBUG)

    path = Path(config()["local_paths"]["openneuro"][OPENNEURO])
    datasets = list_datasets_in_dir(datasets, path, debug=DEBUG)

    datasets_df = pd.DataFrame.from_dict(datasets)
    datasets_df = datasets_df.sort_values("name")

    output_file = Path(__file__).parent.parent / "openneuro.tsv"
    datasets_df.to_csv(output_file, index=False, sep="\t")

    print("data saved to:", output_file)


if __name__ == "__main__":
    main()
