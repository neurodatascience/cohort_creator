"""List datasets contents on openneuro and write the results in a tsv file.

Also checks for derivatives folders for mriqc, frmiprep and freesurfer.

Rerun to update values of "old" datasets.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from utils import config
from utils import init_dataset
from utils import list_datasets_in_dir
from utils import OPENNEURO

DEBUG = False


def main() -> None:
    datasets = init_dataset()

    path = Path(config()["local_paths"]["openneuro"][OPENNEURO])
    datasets = list_datasets_in_dir(datasets, path, debug=DEBUG)

    path = Path(config()["local_paths"]["datalad"][OPENNEURO])
    datasets = list_datasets_in_dir(datasets, path, debug=DEBUG)

    datasets_df = pd.DataFrame.from_dict(datasets)
    datasets_df = datasets_df.sort_values("name")
    datasets_df.to_csv(Path() / "openneuro.tsv", index=False, sep="\t")


if __name__ == "__main__":
    main()
