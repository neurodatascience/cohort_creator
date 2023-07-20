"""Update list of datasets on openneuro and overwrite old tsv file.

- this will add new datasets,
- this will update the values the links to the derivatives datasets
- this should fail if a dataset is already in the tsv file
  if they now exist
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from utils import config
from utils import init_dataset
from utils import list_datasets_in_dir
from utils import OPENNEURO

from cohort_creator._utils import openneuro_df

DEBUG = False

# if True, will overwrite the tsv file with the current openneuro datasets
RESET = False


def main() -> None:
    datasets = openneuro_df()
    datasets.replace({pd.NA: "n/a"}, inplace=True)
    datasets = datasets.to_dict(orient="list")

    if RESET:
        datasets = init_dataset()
        input_dir = Path(config()["local_paths"]["datalad"][OPENNEURO])
        datasets = list_datasets_in_dir(datasets, input_dir, debug=DEBUG)

    input_file = Path(__file__).parent / f"{OPENNEURO}.tsv"
    new_openneuro_datasets = pd.read_csv(input_file, sep="\t")
    if len(new_openneuro_datasets) > 0:
        if os.getenv("CI"):
            input_dir = Path(__file__).parent / "tmp"
        else:
            input_dir = Path(config()["local_paths"]["openneuro"][OPENNEURO])
        datasets = list_datasets_in_dir(datasets, input_dir, debug=DEBUG)

    datasets_df = pd.DataFrame.from_dict(datasets)
    datasets_df = datasets_df.sort_values("name")

    root_dir = Path(__file__).parent.parent
    output_file = root_dir / "cohort_creator" / "data" / "openneuro.tsv"
    datasets_df.to_csv(output_file, index=False, sep="\t")


if __name__ == "__main__":
    main()
