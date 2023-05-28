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

USERNAME = "Remi-Gau"

TOKEN_FILE = Path("/home/remi/Documents/tokens/gh_read_repo_for_orga.txt")

OPENNEURO = "OpenNeuroDatasets"
URL_OPENNEURO = f"https://github.com/{OPENNEURO}/"
OPENNEURO_DERIVATIVES = "OpenNeuroDerivatives"
URL_OPENNEURO_DERIVATIVES = f"https://github.com/{OPENNEURO_DERIVATIVES}/"


@functools.lru_cache(maxsize=1)
def config() -> dict[str, Any]:
    """Return the configuration."""
    with open(Path(__file__).parent / "config.yml") as f:
        return yaml.safe_load(f)


def root_dir() -> Path:
    return Path(__file__).parent.parent


def gh_api_base_url() -> str:
    return "https://api.github.com/orgs/"


def known_derivatives() -> list[str]:
    tsv = Path(__file__).parent / f"{OPENNEURO_DERIVATIVES}.tsv"
    return pd.read_csv(tsv, sep="\t")["name"].values.tolist()


def datasets_in_datalad_superdataset(subds: str) -> list[str]:
    assert subds in [OPENNEURO, OPENNEURO_DERIVATIVES]
    path = Path(config()["local_paths"]["datalad"][subds])
    return [x.name for x in path.glob("*") if x.is_dir()]


@functools.lru_cache(maxsize=1)
def known_datasets_tsv(gh_orga: str) -> Path:
    if gh_orga == OPENNEURO_DERIVATIVES:
        return root_dir() / "cohort_creator" / "data" / "openneuro_derivatives.tsv"
    return root_dir() / "cohort_creator" / "data" / "openneuro.tsv"


def init_dataset() -> dict[str, list[Any]]:
    return {
        "name": [],
        "nb_subjects": [],  # usually the number of subjects folder in raw dataset
        "has_participant_tsv": [],
        "has_participant_json": [],
        "participant_columns": [],
        "has_phenotype_dir": [],
        "modalities": [],
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


def get_subjects(pth: Path) -> list[str]:
    return [v.name for v in pth.glob("sub-*") if v.is_dir()]


def get_nb_subjects(pth: Path) -> int:
    return len(get_subjects(pth))


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


def list_modalities(bids_pth: Path) -> list[str]:
    sub_dirs = [v.name for v in bids_pth.glob("sub-*/*") if v.is_dir()]
    for v in bids_pth.glob("sub-*/ses-*/*"):
        if v.is_dir():
            sub_dirs.append(v.name)
    modalities = [v for v in set(sub_dirs) if is_known_bids_modality(v)]
    return list(set(modalities))


def list_data_files(bids_pth: Path) -> list[str]:
    """Return the list of files in BIDS raw."""
    files = [v.name for v in bids_pth.glob("sub-*/*/*") if v.is_file() and "task-" in v.name]
    for v in bids_pth.glob("sub-*/ses-*/*/*"):
        if v.is_file() and "task-" in v.name:
            files.append(v.name)
    return files


def list_tasks(bids_pth: Path) -> list[str]:
    files = list_data_files(bids_pth)
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


def get_auth() -> tuple[str, str] | None:
    TOKEN = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE) as f:
            TOKEN = f.read().strip()
    auth = None if USERNAME is None or TOKEN is None else (USERNAME, TOKEN)
    return auth
