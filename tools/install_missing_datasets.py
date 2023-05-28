"""Install openneuro datasets that are not part of the datalad superdatasets."""
from __future__ import annotations

from pathlib import Path

from datalad import api
from utils import config
from utils import datasets_in_datalad_superdataset
from utils import get_list_of_datasets
from utils import OPENNEURO


def main() -> None:
    known_datasets = datasets_in_datalad_superdataset(OPENNEURO)

    datasets = get_list_of_datasets(OPENNEURO)
    datasets = [repo for repo in datasets if repo.startswith("ds")]
    unknown_datasets = set(datasets) - set(known_datasets)

    print(sorted(unknown_datasets))
    print(len(unknown_datasets))

    if not unknown_datasets:
        print("No new dataset found")
        return

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
