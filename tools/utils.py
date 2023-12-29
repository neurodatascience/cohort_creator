"""Utility functions for tools."""
from __future__ import annotations

import functools
import json
import logging
import subprocess
from pathlib import Path
from typing import Any
from typing import Generator
from warnings import warn

import pandas as pd
import requests
import yaml
from datalad.api import Dataset
from datalad.support.exceptions import IncompleteResultsError
from mne.io.brainvision.brainvision import _get_hdr_info
from rich import print

from cohort_creator._utils import list_participants_in_dataset
from cohort_creator.data.utils import KNOWN_DATATYPES

DATASET_TYPE = dict[
    str,
    str
    | int
    | bool
    | list[str]
    | list[int]
    | dict[str, list[float] | dict[str, list[float]]]
    | dict[str, int],
]

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
        "created_on": [],
        "nb_subjects": [],  # usually the number of subjects folder in raw dataset
        "has_participant_tsv": [],
        "has_participant_json": [],
        "participant_columns": [],
        "nb_sessions_tsv": [],
        "nb_scans_tsv": [],
        "nb_physio_files": [],
        "nb_stim_files": [],
        "has_phenotype_dir": [],
        "has_stimuli_dir": [],
        "eeg_file_formats": [],
        "ieeg_file_formats": [],
        "meg_file_formats": [],
        "nb_meeg_channels": [],
        "datatypes": [],
        "sessions": [],  # list of sessions if exist
        "tasks": [],
        "size": [],
        "license": [],
        "authors": [],
        "institutions": [],
        "duration": [],  # duration of recoding of each modality
        "references_and_links": [],
        "raw": [],  # link to raw dataset
        "fmriprep": [],  # link to fmriprep dataset if exists
        "freesurfer": [],  # link to freesurfer dataset if exists
        "mriqc": [],  # link to mriqc dataset if exists
    }


def new_dataset(name: str) -> DATASET_TYPE:
    return {
        "name": name,
        "created_on": "n/a",
        "nb_subjects": "n/a",
        "has_participant_tsv": "n/a",
        "has_participant_json": "n/a",
        "participant_columns": [],
        "nb_sessions_tsv": "n/a",
        "nb_scans_tsv": "n/a",
        "nb_physio_files": "n/a",
        "nb_stim_files": "n/a",
        "has_phenotype_dir": "n/a",
        "has_stimuli_dir": "n/a",
        "eeg_file_formats": "n/a",
        "ieeg_file_formats": "n/a",
        "meg_file_formats": "n/a",
        "nb_meeg_channels": "n/a",
        "datatypes": "n/a",
        "tasks": [],
        "size": "n/a",
        "license": "n/a",
        "authors": [],
        "institutions": [],
        "duration": "n/a",
        "references_and_links": [],
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
    tasks = [f.split("task-")[1].split("_")[0].split(".")[0] for f in files]
    tasks = list(set(tasks))
    return tasks


def _get_scan_duration(dataset_pth: Path, filepath: Path) -> float | None:
    """Get only header of a nifti file and compute its acquisition time."""
    if "nii" in filepath.suffix or "gz" in filepath.suffix:
        script_path = Path(__file__).parent / "read_nb_vols"
        cmd = f"datalad fsspec-head -d {dataset_pth} -c 1024 {filepath.relative_to(dataset_pth)} | python {script_path}"
        print(cmd)
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if not result.stderr:
            return float(result.stdout.replace("\n", ""))
        print(result.stderr)
        return None
    elif "vhdr" in filepath.suffix:
        info, n_samples = _get_meeg_header(dataset_pth, filepath)
        if n_samples and info and info["sfreq"]:
            return n_samples / info["sfreq"]
    return None


def _get_meeg_header(dataset_pth: Path, filepath: Path) -> tuple[None | dict[str, Any], None | int]:
    ds = Dataset(dataset_pth)
    try:
        ds.get(filepath)
        ds.get(filepath.with_suffix(".vmrk"))
        (
            info,
            _,
            _,
            _,
            n_samples,
            _,
            _,
            _,
        ) = _get_hdr_info(
            filepath,
            eog=("HEOGL", "HEOGR", "VEOGb"),
            misc="auto",
            scale=1.0,
        )
        return info, n_samples
    except IncompleteResultsError:
        warn(f"IncompleteResultsError for {filepath}", stacklevel=2)
        return None, None
    except FileNotFoundError:
        warn(f"FileNotFoundError for {filepath}", stacklevel=2)
        return None, None


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


def _created_on(dataset_pth: Path) -> str:
    """Use date of first commit as creation date."""
    result = subprocess.run(
        f'git -C {dataset_pth} log --reverse | sed -n -e "3,3p"',
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.replace("Date:", "").strip()


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

    i = 0
    for dataset_pth in raw_datasets:
        dataset_name = dataset_pth.name
        print(f" {dataset_name}")

        dataset = new_dataset(f"{study_prefix}{dataset_name}")

        if dataset_name.startswith("ds"):
            raw_url = f"{URL_OPENNEURO}{dataset_name}"
        else:
            raw_url = Dataset.siblings(dataset_pth, name="origin")[0]["url"]
        dataset["raw"] = raw_url

        dataset["created_on"] = _created_on(path / dataset_name)

        dataset["nb_subjects"] = get_nb_subjects(dataset_pth)

        sessions = list_sessions(dataset_pth)
        dataset["sessions"] = sessions

        datatypes = list_datatypes(dataset_pth, sessions=sessions)
        dataset["datatypes"] = sorted(datatypes)

        if dataset["nb_subjects"] == 0:
            continue
        i += 1
        if debug and i > 10:
            break

        dataset["size"] = _get_dataset_size(dataset_pth)

        tasks = None
        if any(
            mod in datatypes
            for mod in ["func", "eeg", "ieeg", "meg", "beh", "perf", "pet", "motion", "nirs"]
        ):
            tasks = list_tasks(dataset_pth, sessions=sessions)
            check_task(tasks, datatypes, sessions, dataset_pth)
            dataset["tasks"] = sorted(tasks)

        tsv_status, json_status, columns = has_participant_tsv(dataset_pth)
        dataset["has_participant_tsv"] = tsv_status
        dataset["has_participant_json"] = json_status
        dataset["participant_columns"] = columns

        dataset["nb_sessions_tsv"] = _count_sessions_tsv(dataset_pth)
        dataset["nb_scans_tsv"] = _count_scans_tsv(dataset_pth)
        dataset["nb_physio_files"] = _count_physio_files(dataset_pth)
        dataset["nb_stim_files"] = _count_stim_files(dataset_pth)

        dataset["has_phenotype_dir"] = bool((dataset_pth / "phenotype").exists())
        dataset["has_stimuli_dir"] = bool((dataset_pth / "stimuli").exists())

        dataset["eeg_file_formats"] = _count_eeg_file_formats(dataset_pth)
        dataset["ieeg_file_formats"] = _count_ieeg_file_formats(dataset_pth)
        dataset["meg_file_formats"] = _count_meg_file_formats(dataset_pth)
        dataset["nb_meeg_channels"] = _get_number_meeg_channels(dataset_pth, datatypes)

        dataset["authors"] = _get_authors(dataset_pth)

        dataset["license"] = _get_license(dataset_pth)

        dataset["references_and_links"] = _get_references_and_links(dataset_pth)

        dataset["institutions"] = _get_institutions(dataset_pth)

        dataset["duration"] = _get_duration(dataset_pth, datatypes, tasks)

        dataset = add_derivatives(dataset, dataset_pth, derivatives)

        if dataset["name"] in datasets["name"]:
            # raise ValueError(f"dataset {dataset['name']} already in datasets")
            warn(f"dataset {dataset['name']} already in datasets")

        for keys in datasets:
            datasets[keys].append(dataset[keys])

    return datasets


def _count_sessions_tsv(dataset_pth: Path) -> int:
    return len(list(dataset_pth.glob("sub-*/*sessions.tsv")))


def _count_scans_tsv(dataset_pth: Path) -> int:
    return len(list(dataset_pth.glob("sub-*/**/*scans.tsv")))


def _count_physio_files(dataset_pth: Path) -> int:
    return len(list(dataset_pth.glob("sub-*/**/*physio.tsv.gz")))


def _count_stim_files(dataset_pth: Path) -> int:
    return len(list(dataset_pth.glob("sub-*/**/*stim.tsv.gz")))


def _count_eeg_file_formats(dataset_pth: Path) -> dict[str, int]:
    SUPPORTED_FORMATS = ["bdf", "edf", "eeg", "set"]
    count = {}
    for format in SUPPORTED_FORMATS:
        count[format] = len(list(dataset_pth.glob(f"sub-*/**/eeg/*_eeg.{format}")))
    return count


def _count_ieeg_file_formats(dataset_pth: Path) -> dict[str, int]:
    SUPPORTED_FORMATS = ["nwb", "edf", "eeg", "set", "mefd"]
    count = {}
    for format in SUPPORTED_FORMATS:
        count[format] = len(list(dataset_pth.glob(f"sub-*/**/ieeg/*_ieeg.{format}")))
    return count


def _count_meg_file_formats(dataset_pth: Path) -> dict[str, int]:
    SUPPORTED_FORMATS = [".ds", "", ".fif", ".con", ".kdf", ".raw.mhd"]
    count = {}
    for format in SUPPORTED_FORMATS:
        count[format] = len(list(dataset_pth.glob(f"sub-*/**/meg/*_meg{format}")))
    return count


def _get_number_meeg_channels(dataset_pth: Path, datatypes: list[str]) -> list[int]:
    first_sub = list_participants_in_dataset(dataset_pth)[0]
    nb_channels = []
    for target_datatype in ["ieeg", "eeg"]:
        if target_datatype in datatypes:
            files = dataset_pth.glob(f"{first_sub}/**/{target_datatype}/*_{target_datatype}.vhdr")
            for filepath in files:
                info, _ = _get_meeg_header(dataset_pth, filepath)
                if info:
                    if nchan := info.get("nchan"):
                        nb_channels.append(nchan)
    return sorted(list(set(nb_channels)))


def _get_duration(
    dataset_pth: Path, datatypes: list[str], tasks: list[str] | None
) -> dict[str, list[float] | dict[str, list[float]]]:
    first_sub = list_participants_in_dataset(dataset_pth)[0]

    print(f"  Getting 'scan' duration for {first_sub}")

    duration_all_datatypes: dict[str, list[float] | dict[str, list[float]]] = {}

    for target_datatype in ["func", "pet", "ieeg", "eeg"]:
        if target_datatype in datatypes:
            if target_datatype == "pet":
                files = dataset_pth.glob(f"{first_sub}/**/pet/{first_sub}*_pet.nii*")
                duration_all_datatypes[target_datatype] = _get_duration_for_datatype(
                    dataset_pth, files
                )
            if tasks is None:
                tasks = []
            for task_ in tasks:
                if target_datatype == "func":
                    files = dataset_pth.glob(
                        f"{first_sub}/**/func/{first_sub}*task-{task_}*_bold.nii*"
                    )
                elif target_datatype in ["eeg", "ieeg"]:
                    files = dataset_pth.glob(
                        f"{first_sub}/**/{target_datatype}/*_{target_datatype}.vhdr"
                    )
                duration_all_datatypes[target_datatype] = {
                    task_: _get_duration_for_datatype(dataset_pth, files)
                }
    return duration_all_datatypes


def _get_duration_for_datatype(
    dataset_pth: Path, files: Generator[Path, None, None]
) -> list[float]:
    scan_duration = []
    for filepath in files:
        print(f"   {filepath.relative_to(dataset_pth)}")
        if duration := _get_scan_duration(dataset_pth, filepath):
            scan_duration.append(duration)
    return scan_duration


def _get_authors(dataset_pth: Path) -> list[str]:
    if not (dataset_pth / "dataset_description.json").exists():
        warn("no dataset_description.json")
        return []
    with open(dataset_pth / "dataset_description.json") as f:
        dataset_description = json.load(f)
        return dataset_description.get("Authors", [])


def _get_license(dataset_pth: Path) -> str:
    if not (dataset_pth / "dataset_description.json").exists():
        warn("no dataset_description.json")
        return "n/a"
    with open(dataset_pth / "dataset_description.json") as f:
        dataset_description = json.load(f)
        license = dataset_description.get("License", "n/a")
        license = license.replace("\n", "")
        if "Public Domain Dedication and License v1.0" in license:
            return "PDDL 1.0"
        return license


def _get_references_and_links(dataset_pth: Path) -> list[str]:
    if not (dataset_pth / "dataset_description.json").exists():
        warn("no dataset_description.json")
        return []
    with open(dataset_pth / "dataset_description.json") as f:
        dataset_description = json.load(f)
        return dataset_description.get("ReferencesAndLinks", [])


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
            warn(f"Could not parse: {json_file}", stacklevel=2)
        except UnicodeDecodeError:
            warn(f"Could not parse: {json_file}", stacklevel=2)
        except FileNotFoundError:
            warn(f"Could not find: {json_file}", stacklevel=2)

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
    dataset: DATASET_TYPE, dataset_pth: Path, derivatives: list[str]
) -> DATASET_TYPE:
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
