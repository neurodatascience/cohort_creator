"""Utility functions for tools."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from warnings import warn

import pandas as pd

URL_OPENNEURO = "https://github.com/OpenNeuroDatasets/"
URL_OPENNEURO_DERIVATIVES = "https://github.com/OpenNeuroDerivatives/"


def new_dataset(name: str) -> dict[str, str | int | bool | list[str]]:
    return {
        "name": name,
        "has_participant_tsv": "n/a",
        "has_participant_json": "n/a",
        "participant_columns": "n/a",
        "has_phenotype_dir": "n/a",
        "has_mri": "n/a",
        "nb_subjects": "n/a",
        "raw": f"{URL_OPENNEURO}{name}",
        "fmriprep": "n/a",
        "freesurfer": "n/a",
        "mriqc": "n/a",
    }


def get_nb_subjects(pth: Path) -> int:
    tmp = [v for v in pth.glob("sub-*") if v.is_dir()]
    return len(tmp)


def has_participant_tsv(pth: Path) -> tuple[bool, bool, str | list[str]]:
    tsv_status = bool((pth / "participants.tsv").exists())
    json_status = bool((pth / "participants.json").exists())
    if tsv_status:
        return tsv_status, json_status, list_participants_tsv_columns(pth / "participants.tsv")
    else:
        return tsv_status, json_status, "n/a"


def list_participants_tsv_columns(participant_tsv: Path) -> list[str]:
    """Return the list of columns in participants.tsv."""
    try:
        df = pd.read_csv(participant_tsv, sep="\t")
        return df.columns.tolist()
    except pd.errors.ParserError:
        warn(f"Could not parse: {participant_tsv}")
        return ["cannot be parsed"]


def list_derivatives(pth: Path, datasets: dict[str, list[Any]]) -> dict[str, list[Any]]:
    mriqc_datasets = sorted(list(pth.glob("*mriqc")))

    for dataset_pth in mriqc_datasets:
        dataset_name = dataset_pth.name.replace("-mriqc", "")

        dataset = new_dataset(dataset_name)

        dataset["nb_subjects"] = get_nb_subjects(dataset_pth)
        dataset["has_mri"] = True
        dataset["mriqc"] = f"{URL_OPENNEURO_DERIVATIVES}{dataset_pth.name}"

        tsv_status, json_status, columns = has_participant_tsv(dataset_pth / "sourcedata" / "raw")
        dataset["has_participant_tsv"] = tsv_status
        dataset["has_participant_json"] = json_status
        dataset["participant_columns"] = columns

        dataset["has_phenotype_dir"] = (dataset_pth / "sourcedata" / "raw" / "phenotype").exists()

        fmriprep_dataset = Path(str(dataset_pth).replace("mriqc", "fmriprep"))
        if fmriprep_dataset.exists():
            dataset["fmriprep"] = f"{URL_OPENNEURO_DERIVATIVES}{fmriprep_dataset.name}"

        freesurfer_dataset = fmriprep_dataset / "sourcedata" / "freesurfer"
        if freesurfer_dataset.exists():
            dataset["freesurfer"] = f"{dataset['fmriprep']}/tree/main/sourcedata/freesurfer"

        for keys in datasets:
            datasets[keys].append(dataset[keys])

    # adds fmriprep derivatives that have no mriqc counterparts
    fmriprep_datasets = sorted(list(pth.glob("*fmriprep")))
    for dataset_pth in fmriprep_datasets:
        dataset_name = dataset_pth.name.replace("-fmriprep", "")

        if dataset_name not in datasets["name"]:
            dataset = new_dataset(dataset_name)

            dataset["nb_subjects"] = get_nb_subjects(dataset_pth)
            dataset["has_mri"] = True
            dataset["fmriprep"] = f"{URL_OPENNEURO_DERIVATIVES}{dataset_pth.name}"

            tsv_status, json_status, columns = has_participant_tsv(
                dataset_pth / "sourcedata" / "raw"
            )
            dataset["has_participant_tsv"] = tsv_status
            dataset["has_participant_json"] = json_status
            dataset["participant_columns"] = columns

            dataset["has_phenotype_dir"] = (
                dataset_pth / "sourcedata" / "raw" / "phenotype"
            ).exists()

            freesurfer_dataset = dataset_pth / "sourcedata" / "freesurfer"
            if freesurfer_dataset.exists():
                dataset["freesurfer"] = f"{dataset['fmriprep']}/tree/main/sourcedata/freesurfer"

    return datasets
