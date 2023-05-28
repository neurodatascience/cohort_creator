"""Update datasets list."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from datalad import api
from rich import print
from utils import get_list_of_datasets
from utils import known_datasets_tsv
from utils import OPENNEURO_DERIVATIVES

# from utils import init_dataset


def create_listing_new_datasets(gh_orga: str) -> None:
    known_datasets = pd.read_csv(known_datasets_tsv(gh_orga), sep="\t")
    print(known_datasets["name"].values)
    print(len(known_datasets))

    datasets = get_list_of_datasets(gh_orga)

    unknown_datasets = [
        repo
        for repo in datasets
        if repo.split("-")[0] not in known_datasets["name"].values and repo.startswith("ds")
    ]
    unknown_datasets = sorted(unknown_datasets)
    print(sorted(unknown_datasets))
    print(len(unknown_datasets))

    if not unknown_datasets:
        print("No new dataset found")
        return

    output_dir = Path(__file__).parent / "tmp" / gh_orga
    output_dir.mkdir(exist_ok=True)

    for dataset in unknown_datasets:
        print(f"Downloading {dataset}")
        data_pth = output_dir / dataset
        if data_pth.exists():
            print(f"  data already present at {data_pth}")
        else:
            print(f"    installing : {data_pth}")
            api.install(
                path=data_pth,
                source=f"https://github.com/{gh_orga}/{dataset}",
                recursive=False,
            )
            # TODO
            # if (data_pth / "sourcedata" / "raw").exists():
            #     cwd = os.getcwd()
            #     os.chdir(data_pth)
            #     result = run("git submodule update --init sourcedata/raw")
            #     os.chdir(cwd)

    # datasets = init_dataset()
    # datasets = list_derivatives(output_dir, datasets)
    # datasets_df = pd.DataFrame.from_dict(datasets)
    # datasets_df.to_csv(
    #     output_dir / f"{gh_orga}.tsv",
    #     index=False,
    #     sep="\t",
    # )


def main() -> None:
    create_listing_new_datasets(OPENNEURO_DERIVATIVES)


if __name__ == "__main__":
    main()
