"""Utility functions for tools."""
from __future__ import annotations

import functools
import json
import logging
import subprocess
from pathlib import Path
from typing import Any
from warnings import warn

import pandas as pd
import requests
import yaml
from datalad.api import Dataset
from rich import print

from cohort_creator._utils import KNOWN_DATATYPES
from cohort_creator._utils import list_participants_in_dataset

logging.getLogger("datalad").setLevel(logging.WARNING)
logging.getLogger("datalad.gitrepo").setLevel(logging.ERROR)


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
    """Focus on openneuro derivatives repositories."""
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
        "datatypes": [],
        "sessions": [],  # list of sessions if exist
        "tasks": [],
        "size": [],
        "authors": [],
        "institutions": [],
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
        "participant_columns": [],
        "has_phenotype_dir": "n/a",
        "datatypes": "n/a",
        "tasks": [],
        "size": "n/a",
        "authors": [],
        "institutions": [],
        "raw": "n/a",
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
        return tsv_status, json_status, []


def list_participants_tsv_columns(participant_tsv: Path) -> list[str]:
    """Return the list of columns in participants.tsv."""
    try:
        df = pd.read_csv(participant_tsv, sep="\t")
        return df.columns.tolist()
    except pd.errors.ParserError:
        warn(f"Could not parse: {participant_tsv}")
        return ["cannot be parsed"]
    except UnicodeDecodeError:
        warn(f"Could not parse: {participant_tsv}")
        return ["cannot be parsed"]


def is_known_bids_datatype(datatype: str) -> bool:
    return datatype in KNOWN_DATATYPES


def list_datatypes(bids_pth: Path, sessions: list[str]) -> list[str]:
    pattern = "sub-*/ses-*/*" if sessions else "sub-*/*"
    sub_dirs = [v.name for v in bids_pth.glob(pattern) if v.is_dir()]
    datatypes = [v for v in set(sub_dirs) if is_known_bids_datatype(v)]
    return list(set(datatypes))


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
        datasets.extend(repo["name"] for repo in resp)  # type: ignore[index]
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
    datasets: dict[str, list[Any]],
    path: Path,
    debug: bool,
    dataset_name_prefix: str = "ds",
    study_prefix: str = "",
    include: None | list[str] = None,
) -> dict[str, list[Any]]:
    print(f"Listing datasets in {path}")

    EXCLUDED = [
        ".git",
        ".github",
        ".datalad",
        ".gitattributes",
        ".gitmodules",
        ".DS_Store",
        "code",
        "docs",
    ]
    raw_datasets = sorted(list(path.glob(f"{dataset_name_prefix}*")))
    raw_datasets = [x for x in raw_datasets if path.is_dir() and x.name not in EXCLUDED]
    if include:
        raw_datasets = [x for x in raw_datasets if x.name in include]

    derivatives = known_derivatives()

    for i, dataset_pth in enumerate(raw_datasets):
        if debug and i > 50:
            break

        dataset_name = dataset_pth.name
        print(f" {dataset_name}")

        dataset = new_dataset(f"{study_prefix}{dataset_name}")

        if dataset_name.startswith("ds"):
            raw_url = f"{URL_OPENNEURO}{dataset_name}"
        else:
            raw_url = Dataset.siblings(dataset_pth, name="origin")[0]["url"]
        dataset["raw"] = raw_url

        dataset["nb_subjects"] = get_nb_subjects(dataset_pth)
        if dataset["nb_subjects"] == 0:
            continue

        dataset["size"] = _get_dataset_size(dataset_pth)

        sessions = list_sessions(dataset_pth)
        dataset["sessions"] = sessions

        datatypes = list_datatypes(dataset_pth, sessions=sessions)
        dataset["datatypes"] = sorted(datatypes)

        if any(
            mod in datatypes
            for mod in ["func", "eeg", "ieeg", "meg", "beh", "perf", "pet", "motion"]
        ):
            tasks = list_tasks(dataset_pth, sessions=sessions)
            check_task(tasks, datatypes, sessions, dataset_pth)
            dataset["tasks"] = sorted(tasks)

        tsv_status, json_status, columns = has_participant_tsv(dataset_pth)
        dataset["has_participant_tsv"] = tsv_status
        dataset["has_participant_json"] = json_status
        dataset["participant_columns"] = columns

        dataset["has_phenotype_dir"] = bool((dataset_pth / "phenotype").exists())

        dataset["authors"] = _get_authors(dataset_pth)

        # TODO only do in first subject ?
        dataset["institutions"] = _get_institutions(dataset_pth)

        # TODO imaging time for first subject

        dataset = add_derivatives(dataset, dataset_pth, derivatives)

        if dataset["name"] in datasets["name"]:
            # raise ValueError(f"dataset {dataset['name']} already in datasets")
            warn(f"dataset {dataset['name']} already in datasets")

        for keys in datasets:
            datasets[keys].append(dataset[keys])

    return datasets


def _get_authors(dataset_pth: Path) -> list[str]:
    if not (dataset_pth / "dataset_description.json").exists():
        warn("no dataset_description.json")
        return []
    with open(dataset_pth / "dataset_description.json") as f:
        dataset_description = json.load(f)
        return dataset_description.get("Authors", [])


def _get_institutions(dataset_pth: Path) -> list[str]:
    """List institutions in JSON files in root folder and first subject.

    Assumes that first subject is representative of the dataset.
    """
    json_files = list(dataset_pth.glob("*.json"))
    first_subject = list_participants_in_dataset(dataset_pth)[0]
    json_files.extend(list(dataset_pth.glob(f"{first_subject}/**/*.json")))

    institutions = []
    for json_file in json_files:
        if Path(json_file).name.startswith("."):
            continue

        try:
            with open(json_file) as f:
                json_dict = json.load(f)
                if tmp := _construct_institution_string(json_dict).strip(", "):
                    institutions.append(tmp)

        except json.decoder.JSONDecodeError:
            warn(f"Could not parse: {json_file}")
        except UnicodeDecodeError:
            warn(f"Could not parse: {json_file}")
        except FileNotFoundError:
            warn(f"Could not find: {json_file}")

    return sorted(list({x for x in institutions if x}))


def _construct_institution_string(json_dict: Any) -> str:
    if not isinstance(json_dict, dict):
        return ""
    institution_name = json_dict.get("InstitutionName", "")
    if not isinstance(institution_name, str):
        institution_name = ""
    institution_address = json_dict.get("InstitutionAddress", "")
    if not isinstance(institution_address, str):
        institution_address = ""
    return ", ".join([institution_name.strip(), institution_address.strip()])


def _get_dataset_size(dataset_pth: Path) -> str:
    result = subprocess.run(
        f"datalad status -d {dataset_pth} --annex all", shell=True, capture_output=True, text=True
    )
    size = result.stdout.split("/")
    if len(size) > 1:
        size = result.stdout.split("/")[1].split(" ")[:2]
        return " ".join(size)
    else:
        return "n/a"
    # TODO
    # possible to get for each folder by doing
    # datalad -f '{bytesize}' status --annex -- <paths> | paste -sd+ | bc


def list_sessions(dataset_pth: Path) -> list[str]:
    sessions = [v.name.replace("ses-", "") for v in dataset_pth.glob("sub-*/ses-*") if v.is_dir()]
    return sorted(list(set(sessions)))


def check_task(
    tasks: list[str], datatypes: list[str], sessions: list[str], dataset_pth: Path
) -> None:
    """Check if tasks are present in dataset with datatypes that can have tasks."""
    if (
        any(mod in datatypes for mod in ["func", "eeg", "ieeg", "meg", "beh", "motion"])
        and not tasks
    ):
        warn(
            f"no tasks found in {dataset_pth} "
            f"with datatypes {datatypes} "
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
