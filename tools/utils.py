"""Utility functions for tools."""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any
from warnings import warn

import pandas as pd
import requests
import yaml
from rich import print

from cohort_creator._utils import list_participants_in_dataset


OPENNEURO = "OpenNeuroDatasets"
URL_OPENNEURO = f"https://github.com/{OPENNEURO}/"
OPENNEURO_DERIVATIVES = "OpenNeuroDerivatives"
URL_OPENNEURO_DERIVATIVES = f"https://github.com/{OPENNEURO_DERIVATIVES}/"


@functools.lru_cache(maxsize=1)
def config() -> dict[str, Any]:
    """Return the configuration."""
    with open(Path(__file__).parent / "config.yml") as f:
        return yaml.safe_load(f)


def gh_api_base_url() -> str:
    return "https://api.github.com/orgs/"


def known_derivatives() -> list[str]:
    tsv = Path(__file__).resolve().parent / f"{OPENNEURO_DERIVATIVES}.tsv"
    if not tsv.exists():
        raise FileNotFoundError(
            f"{tsv} not found.\n" f"Run 'list_derivatives.py' script to create it."
        )
    return pd.read_csv(tsv, sep="\t")["name"].values.tolist()


def init_dataset() -> dict[str, list[Any]]:
    return {
        "name": [],
        "nb_subjects": [],  # usually the number of subjects folder in raw dataset
        "has_participant_tsv": [],
        "has_participant_json": [],
        "participant_columns": [],
        "has_phenotype_dir": [],
        "modalities": [],
        "sessions": [],  # list of sessions if exist
        "tasks": [],
        "raw": [],  # link to raw dataset
        "fmriprep": [],  # link to fmriprep dataset if exists
        "freesurfer": [],  # link to freesurfer dataset if exists
        "mriqc": [],  # link to mriqc dataset if exists
    }


def new_dataset(name: str) -> dict[str, str | int | bool | list[str]]:
    return {
        "name": name,
        "nb_subjects": "n/a",
        "has_participant_tsv": "n/a",
        "has_participant_json": "n/a",
        "participant_columns": "n/a",
        "has_phenotype_dir": "n/a",
        "modalities": "n/a",
        "tasks": "n/a",
        "raw": f"{URL_OPENNEURO}{name}",
        "fmriprep": "n/a",
        "freesurfer": "n/a",
        "mriqc": "n/a",
    }


def get_nb_subjects(pth: Path) -> int:
    return len(list_participants_in_dataset(pth))


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


def is_known_bids_modality(modality: str) -> bool:
    KNOWN_MODALITIES = [
        "anat",
        "dwi",
        "func",
        "perf",
        "fmap",
        "beh",
        "meg",
        "eeg",
        "ieeg",
        "pet",
        "micr",
        "nirs",
        "motion",
    ]
    return modality in KNOWN_MODALITIES


def list_modalities(bids_pth: Path, sessions: list[str]) -> list[str]:
    pattern = "sub-*/ses-*/*" if sessions else "sub-*/*"
    sub_dirs = [v.name for v in bids_pth.glob(pattern) if v.is_dir()]
    modalities = [v for v in set(sub_dirs) if is_known_bids_modality(v)]
    return list(set(modalities))


def list_data_files(bids_pth: Path, sessions: list[str]) -> list[str]:
    """Return the list of files in BIDS raw."""
    pattern = "sub-*/ses-*/*/*" if sessions else "sub-*/*/*"
    files = [v.name for v in bids_pth.glob(pattern) if "task-" in v.name]
    return files


def list_tasks(bids_pth: Path, sessions: list[str]) -> list[str]:
    files = list_data_files(bids_pth, sessions)
    tasks = [f.split("task-")[1].split("_")[0] for f in files]
    tasks = list(set(tasks))
    return tasks


def get_list_of_datasets(gh_orga: str) -> list[str]:
    auth = get_auth()
    datasets: list[str] = []
    resp: dict[str, str] | bool | None = True
    page = 1
    while resp:
        resp = request_list_of_repos(gh_orga, page=page, auth=auth)
        if resp is None:
            break
        datasets.extend(repo["name"] for repo in resp)  # type: ignore
        page += 1
    datasets = [x for x in datasets if x.startswith("ds")]
    return datasets


def request_list_of_repos(
    gh_orga: str, page: int, auth: tuple[str, str] | None = None
) -> dict[str, str] | None:
    url = f"{gh_api_base_url()}{gh_orga}/repos?per_page=100&page={page}"
    print(url)
    response = requests.get(url, auth=auth)
    if response.status_code != 200:
        warn(f"Error {response.status_code}: {response.text}")
        return None
    return response.json()


@functools.lru_cache(maxsize=1)
def get_auth() -> tuple[str, str] | None:
    import os

    if os.getenv("CI"):
        return None

    username = config()["auth"]["username"]
    token_file = Path(config()["auth"]["token_file"])

    token = None
    if token_file.exists():
        with open(token_file) as f:
            token = f.read().strip()
    auth = None if username is None or token is None else (username, token)
    return auth


def list_datasets_in_dir(
    datasets: dict[str, list[Any]], path: Path, debug: bool
) -> dict[str, list[Any]]:
    print(f"Listing datasets in {path}")

    raw_datasets = sorted(list(path.glob("ds*")))

    derivatives = known_derivatives()

    for i, dataset_pth in enumerate(raw_datasets):
        if debug and i > 10:
            break

        dataset_name = dataset_pth.name
        print(f" {dataset_name}")

        dataset = new_dataset(dataset_name)
        dataset["nb_subjects"] = get_nb_subjects(dataset_pth)

        if dataset["nb_subjects"] == 0:
            continue

        sessions = list_sessions(dataset_pth)
        dataset["sessions"] = sessions

        modalities = list_modalities(dataset_pth, sessions=sessions)
        if any(
            mod in modalities
            for mod in ["func", "eeg", "ieeg", "meg", "beh", "perf", "pet", "motion"]
        ):
            tasks = list_tasks(dataset_pth, sessions=sessions)
            check_task(tasks, modalities, sessions, dataset_pth)
            dataset["tasks"] = sorted(tasks)
        dataset["modalities"] = sorted(modalities)

        tsv_status, json_status, columns = has_participant_tsv(dataset_pth)
        dataset["has_participant_tsv"] = tsv_status
        dataset["has_participant_json"] = json_status
        dataset["participant_columns"] = columns
        dataset["has_phenotype_dir"] = bool((dataset_pth / "phenotype").exists())

        dataset = add_derivatives(dataset, dataset_pth, derivatives)

        if dataset["name"] in datasets["name"]:
            raise ValueError(f"dataset {dataset['name']} already in datasets")

        for keys in datasets:
            datasets[keys].append(dataset[keys])

    return datasets


def list_sessions(dataset_pth: Path) -> list[str]:
    sessions = [v.name.replace("ses-", "") for v in dataset_pth.glob("sub-*/ses-*") if v.is_dir()]
    return sorted(list(set(sessions)))


def check_task(
    tasks: list[str], modalities: list[str], sessions: list[str], dataset_pth: Path
) -> None:
    """Check if tasks are present in dataset with modalities that can have tasks."""
    if (
        any(mod in modalities for mod in ["func", "eeg", "ieeg", "meg", "beh", "motion"])
        and not tasks
    ):
        warn(
            f"no tasks found in {dataset_pth} "
            f"with modalities {modalities} "
            f"and files {list_data_files(dataset_pth, sessions)}"
        )


def add_derivatives(
    dataset: dict[str, str | list[str] | bool | int], dataset_pth: Path, derivatives: list[str]
) -> dict[str, str | list[str] | bool | int]:
    """Update dict with links to derivatives if they exist."""
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
