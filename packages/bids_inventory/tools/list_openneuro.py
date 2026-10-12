"""List datasets contents on openneuro and write the results in a JSON lines file.

Also checks for derivatives folders for mriqc, frmiprep and freesurfer.

Rerun to update values of "old" datasets.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from bids_inventory._update import (
    OPENNEURO,
    config,
    init_dataset,
    install_missing_datasets,
    list_datasets_in_dir,
    list_openneuro_derivatives,
)
from bids_inventory.listing import save_known_datasets
from bids_inventory.logger import bi_logger

cc_log = bi_logger()

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

    output_file = Path(__file__).parent.parent / "openneuro.jsonl"
    save_known_datasets(datasets_df, output_file)

    print("data saved to:", output_file)


if __name__ == "__main__":
    main()
