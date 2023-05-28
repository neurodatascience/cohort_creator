"""List MRIQC datasets contents in openneuro-derivatives \
and write the results in a tsv file.

Also list participants in those datasets.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from utils import get_subjects
from utils import URL_OPENNEURO

# adapt to your set up
# LOCAL_DIR = Path(__file__).resolve().parent / "inputs"
LOCAL_DIR = "/home/remi/datalad/datasets.datalad.org"


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


def list_openneuro_derivatives(
    datalad_superdataset: Path, datasets: dict[str, Any]
) -> dict[str, Any]:
    """Indexes content of dataset on openneuro derivatives.

    List mriqc datasets and eventually matching fmriprep dataset.

    nb_subjects is the number of subjects in the mriqc dataset.
    """
    openneuro_derivatives = datalad_superdataset / "openneuro-derivatives"

    mriqc_datasets = sorted(list(openneuro_derivatives.glob("*mriqc")))

    for dataset_pth in mriqc_datasets:
        dataset_name = dataset_pth.name.replace("-mriqc", "")

        dataset = new_dataset(dataset_name)

        for keys in datasets:
            datasets[keys].append(dataset[keys])

    return datasets


def list_participants(datasets: dict[str, Any]) -> dict[str, Any]:
    """List participants in openneuro datasets."""
    datalad_superdataset = Path(LOCAL_DIR)

    datasets.pop("PortalURI")
    datasets["SubjectID"] = []
    datasets["SessionID"] = []

    openneuro_derivatives = datalad_superdataset / "openneuro-derivatives"

    mriqc_datasets = sorted(list(openneuro_derivatives.glob("*mriqc")))

    for dataset_pth in mriqc_datasets:
        dataset_name = dataset_pth.name.replace("-mriqc", "")

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


def main() -> None:
    output_dir = Path(__file__).parent.parent / "inputs"
    datalad_superdataset = Path(LOCAL_DIR)

    datasets = init_dataset()
    datasets = list_openneuro_derivatives(datalad_superdataset, datasets)
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
