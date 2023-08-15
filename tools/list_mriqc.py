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
from utils import known_derivatives
from utils import OPENNEURO
from utils import URL_OPENNEURO

from cohort_creator._utils import list_participants_in_dataset
from cohort_creator._utils import list_sessions_in_participant


def init_dataset() -> dict[str, list[str]]:
    return {
        "DatasetID": [],
        "PortalURI": [],  # link to raw dataset
    }


def new_dataset(name: str) -> dict[str, str | list[str]]:
    return {
        "DatasetID": name,
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


def has_mri(session_pth: Path) -> bool:
    """Return True if the session has at least one MRI."""
    return any(
        "anat" in x.name or "func" in x.name for x in session_pth.glob("**/*") if x.is_dir()
    )


def list_participants(datasets: dict[str, Any]) -> dict[str, Any]:
    """List all participants in all mriqc datasets."""
    datasets.pop("PortalURI")
    datasets["SubjectID"] = []
    datasets["SessionID"] = []

    for dataset_name in mriqc_datasets():
        dataset_name = dataset_name.replace("-mriqc", "")

        dataset_pth = get_raw_dataset_path(dataset_name)

        subjects = sorted(list_participants_in_dataset(dataset_pth))

        for subject_ in subjects:
            sessions = list_sessions_in_participant(dataset_pth / subject_)

            for session_ in sessions:
                dataset = new_dataset(dataset_name)

                if session_ is None:
                    session_ = "n/a"
                    dataset["SubjectID"] = subject_
                    dataset["SessionID"] = session_
                    for keys in datasets:
                        datasets[keys].append(dataset[keys])

                elif has_mri(dataset_pth / subject_ / session_):
                    dataset["SubjectID"] = subject_
                    dataset["SessionID"] = session_
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
