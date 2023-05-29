"""List MRIQC datasets contents in openneuro-derivatives \
and write the results in a tsv file.

Also list participants in those datasets.
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import pandas as pd
from utils import config
from utils import get_subjects
from utils import known_derivatives
from utils import OPENNEURO
from utils import URL_OPENNEURO


def init_dataset() -> dict[str, list[str]]:
    return {
        "DatasetName": [],
        "PortalURI": [],  # link to raw dataset
    }


def new_dataset(name: str) -> dict[str, str | list[str]]:
    return {
        "DatasetName": name,
        "PortalURI": f"{URL_OPENNEURO}{name}",
    }


@functools.lru_cache(maxsize=1)
def mriqc_datasets() -> list[str]:
    derivatives = known_derivatives()
    return sorted([x for x in derivatives if "mriqc" in x])


def list_mriqc_in_derivatives(datasets: dict[str, Any]) -> dict[str, Any]:
    for dataset_pth in mriqc_datasets():
        dataset_name = dataset_pth.replace("-mriqc", "")
        dataset = new_dataset(dataset_name)
        for keys in datasets:
            datasets[keys].append(dataset[keys])

    return datasets


def list_participants(datasets: dict[str, Any]) -> dict[str, Any]:
    """List all participants in all mriqc datasets."""
    datasets.pop("PortalURI")
    datasets["SubjectID"] = []
    datasets["SessionID"] = []

    for dataset_name in mriqc_datasets():
        dataset_name = dataset_name.replace("-mriqc", "")

        dataset_pth = get_raw_dataset_path(dataset_name)

        subjects = get_subjects(dataset_pth)

        sessions = [
            x.name.replace("ses-", "") for x in dataset_pth.glob("sub-*/ses-*") if x.is_dir()
        ]
        sessions = list(set(sessions))

        for subject_ in subjects:
            dataset = new_dataset(dataset_name)
            dataset["SubjectID"] = subject_
            dataset["SessionID"] = sessions

            for keys in datasets:
                datasets[keys].append(dataset[keys])

    return datasets


def get_raw_dataset_path(dataset_name: str) -> Path:
    """Return the path to the raw dataset.

    Look first in the datalad superdataset, then in locally installed openneuro datasets.
    """
    path = Path(config()["local_paths"]["datalad"][OPENNEURO]) / dataset_name
    if path.exists():
        return path
    path = Path(config()["local_paths"]["openneuro"][OPENNEURO]) / dataset_name
    if path.exists():
        return path
    raise FileNotFoundError(f"Dataset {dataset_name} not found")


def main() -> None:
    output_dir = Path(__file__).parent.parent / "inputs"

    datasets = init_dataset()
    datasets = list_mriqc_in_derivatives(datasets)
    df = pd.DataFrame.from_dict(datasets)
    df.to_csv(
        output_dir / "datasets_with_mriqc.tsv",
        index=False,
        sep="\t",
    )

    datasets = init_dataset()
    datasets = list_participants(datasets)
    df = pd.DataFrame.from_dict(datasets)
    df.to_csv(
        output_dir / "participants_with_mriqc.tsv",
        index=False,
        sep="\t",
    )


if __name__ == "__main__":
    main()
