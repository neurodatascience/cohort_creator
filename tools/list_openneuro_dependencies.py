"""List datasets contents either on openneuro proper or in openneuro-derivatives \
and write the results in a tsv file.

Each tsv has the columns defined in the dict `datasets` defined in main().
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from warnings import warn

import datalad.api as dlapi
import pandas as pd
from rich import print


VERBOSE = False

# adapt to your set up
# LOCAL_DIR = Path(__file__).resolve().parent / "inputs"
LOCAL_DIR = "/home/remi/datalad/datasets.datalad.org"

URL_OPENNEURO = "https://github.com/OpenNeuroDatasets/"
URL_OPENNEURO_DERIVATIVES = "https://github.com/OpenNeuroDerivatives/"


def init_dataset() -> dict[str, list[Any]]:
    return {
        "name": [],
        "has_participant_tsv": [],
        "has_participant_json": [],
        "participant_columns": [],
        "has_phenotype_dir": [],
        "has_mri": [],
        "nb_subjects": [],  # usually the number of subjects folder in raw dataset
        "raw": [],  # link to raw dataset
        "fmriprep": [],  # link to fmriprep dataset if exists
        "freesurfer": [],  # link to freesurfer dataset if exists
        "mriqc": [],  # link to mriqc dataset if exists
    }


def main() -> None:
    datalad_superdataset = Path(LOCAL_DIR)

    datasets = init_dataset()
    datasets = list_openneuro(datalad_superdataset, datasets)
    datasets_df = pd.DataFrame.from_dict(datasets)
    datasets_df.to_csv(Path() / "openneuro.tsv", index=False, sep="\t")

    datasets = init_dataset()
    datasets = list_openneuro_derivatives(datalad_superdataset, datasets)
    datasets_df = pd.DataFrame.from_dict(datasets)
    datasets_df.to_csv(
        Path() / "openneuro_derivatives.tsv",
        index=False,
        sep="\t",
    )


def has_mri(bids_pth: Path) -> bool:
    """Return True if at least one subject has at least one MRI modality folder."""
    return bool(
        list(bids_pth.glob("sub*/func"))
        or list(bids_pth.glob("sub*/ses*/func"))
        or list(bids_pth.glob("sub*/anat"))
        or list(bids_pth.glob("sub*/ses*/anat"))
        or list(bids_pth.glob("sub*/dwi"))
        or list(bids_pth.glob("sub*/ses*/dwi"))
        or list(bids_pth.glob("sub*/perf"))
        or list(bids_pth.glob("sub*/ses*/perf"))
    )


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


def list_participants_tsv_columns(participant_tsv: Path) -> list[str]:
    """Return the list of columns in participants.tsv."""
    try:
        df = pd.read_csv(participant_tsv, sep="\t")
        return df.columns.tolist()
    except pd.errors.ParserError:
        warn(f"Could not parse: {participant_tsv}")
        return ["cannot be parsed"]


def list_openneuro(
    datalad_superdataset: Path, datasets: dict[str, list[Any]]
) -> dict[str, list[Any]]:
    """Indexes content of dataset on openneuro.

    Also checks for derivatives folders for mriqc, frmiprep and freesurfer.
    """
    openneuro = datalad_superdataset / "openneuro"
    install_dataset(openneuro, verbose=VERBOSE)

    raw_datasets = sorted(list(openneuro.glob("ds*")))

    for dataset_pth in raw_datasets:
        dataset_name = dataset_pth.name

        dataset = new_dataset(dataset_name)
        dataset["nb_subjects"] = get_nb_subjects(dataset_pth)
        dataset["has_mri"] = has_mri(dataset_pth)

        tsv_status, json_status, columns = has_participant_tsv(dataset_pth)
        dataset["has_participant_tsv"] = tsv_status
        dataset["has_participant_json"] = json_status
        dataset["participant_columns"] = columns
        dataset["has_phenotype_dir"] = bool((dataset_pth / "phenotype").exists())

        for der in [
            "fmriprep",
            "freesurfer",
            "mriqc",
        ]:
            if der_datasets := dataset_pth.glob(f"derivatives/*{der}*"):
                for i in der_datasets:
                    dataset[der] = f"{URL_OPENNEURO}{dataset_name}/tree/main/derivatives/{i.name}"

        for keys in datasets:
            datasets[keys].append(dataset[keys])

    return datasets


def has_participant_tsv(pth: Path) -> tuple[bool, bool, str | list[str]]:
    tsv_status = bool((pth / "participants.tsv").exists())
    json_status = bool((pth / "participants.json").exists())
    if tsv_status:
        return tsv_status, json_status, list_participants_tsv_columns(pth / "participants.tsv")
    else:
        return tsv_status, json_status, "n/a"


def list_openneuro_derivatives(
    datalad_superdataset: Path, datasets: dict[str, list[Any]]
) -> dict[str, list[Any]]:
    """Indexes content of dataset on openneuro derivatives.

    List mriqc datasets and eventually matching fmriprep dataset.

    nb_subjects is the number of subjects in the mriqc dataset.
    """
    openneuro_derivatives = datalad_superdataset / "openneuro-derivatives"

    install_dataset(openneuro_derivatives, verbose=VERBOSE)

    mriqc_datasets = sorted(list(openneuro_derivatives.glob("*mriqc")))

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
    fmriprep_datasets = sorted(list(openneuro_derivatives.glob("*fmriprep")))
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


def install_dataset(dataset_pth: Path, verbose: bool) -> None:
    dl_dataset = dlapi.Dataset(dataset_pth)
    if not dl_dataset.is_installed():
        if verbose:
            print(f"installing: {dataset_pth}")
        dl_dataset.install()
    elif verbose:
        print(f"{dataset_pth} already installed")


def get_nb_subjects(pth: Path) -> int:
    tmp = [v for v in pth.glob("sub-*") if v.is_dir()]
    return len(tmp)


if __name__ == "__main__":
    main()
