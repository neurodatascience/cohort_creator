"""Install openneuro datasets that are not part of the datalad superdatasets."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from datalad import api
from utils import config
from utils import get_list_of_datasets
from utils import OPENNEURO

from cohort_creator._utils import openneuro_df


def main() -> None:
    known_datasets = openneuro_df()["name"].values.tolist()

    datasets = get_list_of_datasets(OPENNEURO)
    unknown_datasets = set(datasets) - set(known_datasets)

    print(sorted(unknown_datasets))
    print(len(unknown_datasets))

    df = pd.DataFrame({"name": datasets})
    df.to_csv(Path(__file__).parent / f"{OPENNEURO}.tsv", sep="\t", index=False)

    if not unknown_datasets:
        print("No new dataset found")
        return

    if os.getenv("CI"):
        output_dir = Path(__file__).parent / "tmp"
    else:
        output_dir = Path(config()["local_paths"]["openneuro"][OPENNEURO])
    output_dir.mkdir(exist_ok=True)

    for dataset in unknown_datasets:
        data_pth = output_dir / dataset
        if data_pth.exists():
            print(f"  data already present at {data_pth}")
            continue
        else:
            print(f"    installing : {data_pth}")
            api.install(
                path=data_pth,
                source=f"https://github.com/{OPENNEURO}/{dataset}",
                recursive=False,
            )


if __name__ == "__main__":
    main()
