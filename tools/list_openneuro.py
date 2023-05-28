"""List datasets contents on openneuro and write the results in a tsv file."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from warnings import warn

import pandas as pd
from utils import get_nb_subjects
from utils import has_participant_tsv
from utils import init_dataset
from utils import known_derivatives
from utils import list_data_files
from utils import list_modalities
from utils import list_tasks
from utils import new_dataset
from utils import URL_OPENNEURO
from utils import URL_OPENNEURO_DERIVATIVES

DEBUG = False

# adapt to your set up
# LOCAL_DIR = Path(__file__).resolve().parent / "inputs"
LOCAL_DIR = "/home/remi/datalad/datasets.datalad.org"


def main() -> None:
    datalad_superdataset = Path(LOCAL_DIR)

    datasets = init_dataset()
    datasets = list_openneuro(datalad_superdataset, datasets)
    datasets_df = pd.DataFrame.from_dict(datasets)
    datasets_df.to_csv(Path() / "openneuro.tsv", index=False, sep="\t")


def list_openneuro(
    datalad_superdataset: Path, datasets: dict[str, list[Any]], debug: bool = DEBUG
) -> dict[str, list[Any]]:
    """Indexes content of dataset on openneuro.

    Also checks for derivatives folders for mriqc, frmiprep and freesurfer.
    """
    openneuro = datalad_superdataset / "openneuro"
    print(f"Listing derivatives in {openneuro}")

    raw_datasets = sorted(list(openneuro.glob("ds*")))

    derivatives = known_derivatives()

    for i, dataset_pth in enumerate(raw_datasets):
        if debug and i > 10:
            break
        dataset_name = dataset_pth.name
        print(f" {dataset_name}")

        dataset = new_dataset(dataset_name)
        dataset["nb_subjects"] = get_nb_subjects(dataset_pth)
        modalities = list_modalities(dataset_pth)
        if any(
            mod in modalities
            for mod in ["func", "eeg", "ieeg", "meg", "beh", "perf", "pet", "motion"]
        ):
            tasks = list_tasks(dataset_pth)
            check_task(tasks, modalities, dataset_pth)

        dataset["tasks"] = tasks
        dataset["modalities"] = modalities

        tsv_status, json_status, columns = has_participant_tsv(dataset_pth)
        dataset["has_participant_tsv"] = tsv_status
        dataset["has_participant_json"] = json_status
        dataset["participant_columns"] = columns
        dataset["has_phenotype_dir"] = bool((dataset_pth / "phenotype").exists())

        dataset = add_derivatives(dataset, dataset_pth, derivatives)

        for keys in datasets:
            datasets[keys].append(dataset[keys])

    return datasets


def check_task(tasks: list[str], modalities: list[str], dataset_pth: Path) -> None:
    if (
        any(mod in modalities for mod in ["func", "eeg", "ieeg", "meg", "beh", "motion"])
        and not tasks
    ):
        warn(
            f"no tasks found in {dataset_pth} "
            f"with modalities {modalities} "
            f"and files {list_data_files(dataset_pth)}"
        )


def add_derivatives(
    dataset: dict[str, str | list[str] | bool | int], dataset_pth: Path, derivatives: list[str]
) -> dict[str, str | list[str] | bool | int]:
    dataset_name = dataset["name"]
    for der in ["fmriprep", "mriqc"]:
        if f"{dataset_name}-{der}" in derivatives:
            dataset[der] = f"{URL_OPENNEURO_DERIVATIVES}{dataset_name}-{der}"

    for der in [
        "fmriprep",
        "freesurfer",
        "mriqc",
    ]:
        if dataset[der] != "n/a":
            continue
        if der_datasets := dataset_pth.glob(f"derivatives/*{der}*"):
            for i in der_datasets:
                dataset[der] = f"{URL_OPENNEURO}{dataset_name}/tree/main/derivatives/{i.name}"

    return dataset


if __name__ == "__main__":
    main()
