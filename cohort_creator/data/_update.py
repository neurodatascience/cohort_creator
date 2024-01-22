from __future__ import annotations

import functools
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any
from typing import Generator
from typing import Iterable
from warnings import warn

import numpy as np
import pandas as pd
import requests
import yaml
from datalad import api
from datalad.support.exceptions import IncompleteResultsError
from mne.io.brainvision.brainvision import _get_hdr_info
from rich.progress import Progress

from cohort_creator._utils import list_participants_in_dataset
from cohort_creator._utils import progress_bar
from cohort_creator.data.utils import _data_dir
from cohort_creator.data.utils import _load_known_datasets
from cohort_creator.data.utils import _openneuro_listing_tsv
from cohort_creator.data.utils import known_datasets_df
from cohort_creator.data.utils import KNOWN_DATATYPES
from cohort_creator.logger import cc_logger

DATASET_TYPE = dict[
    str,
    str
    | int
    | bool
    | list[str]
    | list[int]
    | dict[str, Iterable[tuple[int, float]] | dict[str, Iterable[tuple[int, float]]]]
    | dict[str, int],
]

OPENNEURO = "OpenNeuroDatasets"
OPENNEURO_DERIVATIVES = "OpenNeuroDerivatives"
URL_OPENNEURO = f"https://github.com/{OPENNEURO}/"
URL_OPENNEURO_DERIVATIVES = f"https://github.com/{OPENNEURO_DERIVATIVES}/"

cc_log = cc_logger()

logging.getLogger("datalad").setLevel(logging.WARNING)
logging.getLogger("datalad.gitrepo").setLevel(logging.ERROR)


@functools.lru_cache(maxsize=1)
def config() -> dict[str, Any]:
    """Return the configuration."""
    with open(Path(__file__).parent / "config.yml") as f:
        return yaml.safe_load(f)


def install_missing_datasets(use_superdataset: bool = False) -> None:
    """Install unknown openneuro datasets.

    This script installs all the datasets from openneuro:
    - that are not in the openneuro.tsv file
    - OR that are not part of the datalad superdatasets.

    Parameters
    ----------
    use_superdataset : bool
       Set to ``True`` to only use datasets from the datalad superdatasets as known.
    """
    unknown_datasets = list_openneuro_raw(use_superdataset)

    if not unknown_datasets:
        cc_log.info("No new dataset found")
        return

    if os.getenv("CI"):
        output_dir = Path(__file__).parent / "tmp"
    else:
        output_dir = Path(config()["local_paths"]["openneuro"][OPENNEURO])
    output_dir.mkdir(exist_ok=True)

    with Progress() as progress:
        task = progress.add_task("[green]Installing...", total=len(unknown_datasets))

        for dataset in unknown_datasets:
            data_pth = output_dir / dataset

            if data_pth.exists():
                cc_log.info(f"  data already present at {data_pth}")
                progress.update(task, advance=1)
                continue

            source = f"https://github.com/{OPENNEURO}/{dataset}.git"
            response = requests.get(source)
            if response.status_code != 200:
                cc_log.warning(f"error {response.status_code} for dataset {source}")
                progress.update(task, advance=1)
                continue

            cc_log.info(f"installing: {data_pth}")
            try:
                api.install(
                    path=data_pth,
                    source=source,
                    recursive=False,
                )
            except IncompleteResultsError:
                cc_log.error(f" could not install: {data_pth}")
            progress.update(task, advance=1)


def list_openneuro_raw(use_superdataset: bool) -> set[str]:
    if use_superdataset:
        path_known_datasets = Path(config()["local_paths"]["datalad"][OPENNEURO])
        known_datasets = [x.name for x in path_known_datasets.glob("*")]
    else:
        known_datasets = known_datasets_df()["name"].values.tolist()

    print()
    cc_log.info("Getting list of public openneuro raw datasets from the GitHub API.")
    datasets = get_list_of_datasets(OPENNEURO)
    unknown_datasets = set(datasets) - set(known_datasets)

    cc_log.info(f"{len(unknown_datasets)} unknown datasets")
    cc_log.info(sorted(unknown_datasets))

    df = pd.DataFrame({"name": datasets})
    df.to_csv(Path(__file__).parent / f"{OPENNEURO}.tsv", sep="\t", index=False)
    return unknown_datasets


def list_openneuro_derivatives() -> None:
    """List openeneuro derivatives datasets from the GitHub organization.

    Saves the listing to a TSV file.
    """
    print()
    cc_log.info("Getting list of public openneuro derivatives datasets from the GitHub API.")
    datasets = get_list_of_datasets(gh_orga=OPENNEURO_DERIVATIVES)
    df = pd.DataFrame({"name": datasets})
    df.to_csv(_data_dir() / f"{OPENNEURO_DERIVATIVES}.tsv", sep="\t", index=False)


def update_openneuro(reset: bool = False, debug: bool = True) -> None:
    """Update list of datasets on openneuro and overwrite old tsv file.

    - this will add new datasets,
    - this will update the values the links to the derivatives datasets
    - this should fail if a dataset is already in the tsv file
    if they now exist

    Parameters
    ----------
    debug : bool
        If ``False``, will overwrite the tsv file with the current openneuro datasets.
        If ``True`` will save output in current directory and only index a few datasets.
    """
    datasets = _load_known_datasets(_openneuro_listing_tsv())
    datasets.replace({pd.NA: "n/a"}, inplace=True)
    datasets = datasets.to_dict(orient="list")

    if reset:
        datasets = init_dataset()
        input_dir = Path(config()["local_paths"]["datalad"][OPENNEURO])
        datasets = list_datasets_in_dir(datasets, input_dir, debug=debug)

    input_file = _data_dir() / f"{OPENNEURO}.tsv"
    new_openneuro_datasets = pd.read_csv(input_file, sep="\t")
    if len(new_openneuro_datasets) > 0:
        if os.getenv("CI"):
            input_dir = Path(__file__).parent / "tmp"
        else:
            input_dir = Path(config()["local_paths"]["openneuro"][OPENNEURO])
        datasets = list_datasets_in_dir(datasets, input_dir, debug=debug)

    datasets_df = pd.DataFrame.from_dict(datasets)
    datasets_df = datasets_df.sort_values("name")

    datasets_df["created_on"] = datasets_df["created_on"].apply(lambda x: pd.to_datetime(x))

    output_file = _openneuro_listing_tsv()
    if debug:
        output_file = Path.cwd() / "openneuro.tsv"
    cc_log.info(f"Saving to {output_file}")
    datasets_df.to_csv(output_file, index=False, sep="\t")


def known_derivatives() -> list[str]:
    """Focus on openneuro derivatives repositories."""
    tsv = _data_dir() / f"{OPENNEURO_DERIVATIVES}.tsv"
    if not tsv.exists():
        raise FileNotFoundError(
            f"{tsv} not found.\n" f"Run 'list_derivatives.py' script to create it."
        )
    return pd.read_csv(tsv, sep="\t")["name"].values.tolist()


def gh_api_base_url() -> str:
    return "https://api.github.com/orgs/"


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


# TODO adatp to pass token from CLI
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
    else:
        cc_log.warning(f"Token file not found.\n{str(token_file)}")
    auth = None if username is None or token is None else (username, token)
    return auth


def request_list_of_repos(
    gh_orga: str, page: int, auth: tuple[str, str] | None = None
) -> dict[str, str] | None:
    url = f"{gh_api_base_url()}{gh_orga}/repos?per_page=100&page={page}"
    cc_log.info(url)
    response = requests.get(url, auth=auth)
    if response.status_code != 200:
        warn(f"Error {response.status_code}: {response.text}")
        return None
    return response.json()


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


def list_datasets_in_dir(
    datasets: dict[str, list[Any]],
    path: Path,
    debug: bool,
    dataset_name_prefix: str = "ds",
    study_prefix: str = "",
    include: None | list[str] = None,
    update_merge: bool = False,
) -> dict[str, list[Any]]:
    """List datasets in a directory.

    Parameters
    ----------
    datasets : dict[str, list[Any]]
        _description_
    path : Path
        _description_
    debug : bool
        If ``True`` will only go through a few datasets before returning.
    dataset_name_prefix : str, optional
        _description_, by default "ds"
    study_prefix : str, optional
        _description_, by default ""
    include : None | list[str], optional
        _description_, by default None
    update_merge: bool, default = False
        Pull latest version of each dataset before collecting its metadata

    Returns
    -------
    dict[str, list[Any]]
        _description_
    """
    MIN_NB_DATASETS = 5
    print()
    cc_log.info(f"Listing datasets in {path}")

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

    with progress_bar(text="Updating") as progress:
        task = progress.add_task(description="updating", total=len(raw_datasets))

        i = 0
        for dataset_pth in raw_datasets:
            print()
            cc_log.info(f"{dataset_pth.name}")

            if not _check_dataset(dataset_pth):
                progress.update(task, advance=1)
                continue
            i += 1
            if debug and i > MIN_NB_DATASETS:
                break

            # update dataset to make sure we get the latest version
            ds = api.Dataset(dataset_pth)
            if update_merge:
                ds.update(how="merge")
            try:
                ds.get(dataset_pth / "dataset_description.json")
            except IncompleteResultsError:
                cc_log.warning("Could not get dataset_description.json or is missing.")

            # for openneuro datasets try to eanabe annex remote on S3
            # to allow using datalad fsspec
            # if dataset_pth.name.startswith('ds'):
            enable_S3_remote(dataset_pth)

            dataset = get_info_dataset(dataset_pth, study_prefix)

            dataset = add_derivatives(dataset, dataset_pth, derivatives)

            if dataset["name"] in datasets["name"]:
                # raise ValueError(f"dataset {dataset['name']} already in datasets")
                cc_log.warning(f"dataset {dataset['name']} already in datasets")

            for keys in datasets:
                datasets[keys].append(dataset[keys])

            progress.update(task, advance=1)

    return datasets


def _check_dataset(dataset_pth: Path) -> bool:
    raw_url = get_raw_url(dataset_pth)
    if not raw_url.startswith("git@"):
        try:
            response = requests.get(raw_url)
        except requests.exceptions.InvalidSchema:
            cc_log.error(f"No connection adapters were found for: {raw_url}")
            return False
        if response.status_code != 200:
            cc_log.error(f"error {response.status_code} for dataset {dataset_pth}")
            return False
    if get_nb_subjects(dataset_pth) == 0:
        cc_log.warning(f"No subject in dataset {dataset_pth}")
        return False
    return True


def enable_S3_remote(dataset_pth: Path) -> None:
    # try using
    # http://docs.datalad.org/en/stable/generated/datalad.support.annexrepo.html#datalad.support.annexrepo.AnnexRepo
    enable_remote_cmd = f"cd {dataset_pth} && git annex enableremote s3-PUBLIC public=yes"
    cc_log.debug(enable_remote_cmd)
    try:
        subprocess.run(enable_remote_cmd, shell=True, capture_output=True, text=True)
        cc_log.info(" S3 remote enabled")
    except TypeError:
        cc_log.debug(" Could not enable S3 remote")


def get_raw_url(dataset_pth: Path) -> str:
    dataset_name = dataset_pth.name
    if dataset_name.startswith("ds"):
        return f"{URL_OPENNEURO}{dataset_name}"
    else:
        return api.Dataset.siblings(dataset_pth, name="origin")[0]["url"]


def get_info_dataset(dataset_pth: Path, study_prefix: str) -> DATASET_TYPE:
    dataset_name = dataset_pth.name

    dataset = new_dataset(f"{study_prefix}{dataset_name}")

    dataset["raw"] = get_raw_url(dataset_pth)

    dataset["created_on"] = created_on(dataset_pth)

    dataset["nb_subjects"] = get_nb_subjects(dataset_pth)

    sessions = list_sessions(dataset_pth)
    dataset["sessions"] = sessions

    datatypes = list_datatypes(dataset_pth, sessions=sessions)
    dataset["datatypes"] = datatypes

    dataset["size"] = get_dataset_size(dataset_pth)

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

    dataset["nb_sessions_tsv"] = count_sessions_tsv(dataset_pth)
    dataset["nb_scans_tsv"] = count_scans_tsv(dataset_pth)
    dataset["nb_physio_files"] = count_physio_files(dataset_pth)
    dataset["nb_stim_files"] = count_stim_files(dataset_pth)

    dataset["has_phenotype_dir"] = bool((dataset_pth / "phenotype").exists())
    dataset["has_stimuli_dir"] = bool((dataset_pth / "stimuli").exists())

    dataset["eeg_file_formats"] = count_eeg_file_formats(dataset_pth)
    dataset["ieeg_file_formats"] = count_ieeg_file_formats(dataset_pth)
    dataset["meg_file_formats"] = count_meg_file_formats(dataset_pth)
    dataset["nb_meeg_channels"] = get_number_meeg_channels(dataset_pth, datatypes)

    dataset["authors"] = get_authors(dataset_pth)
    dataset["license"] = get_license(dataset_pth)
    dataset["references_and_links"] = get_references_and_links(dataset_pth)

    dataset["institutions"] = get_institutions(dataset_pth)

    dataset["duration"] = get_duration(dataset_pth, datatypes, tasks)

    return dataset


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
    sub_dirs = [v.name for v in bids_pth.glob("sub-*/*") if v.is_dir()]
    if sessions:
        tmp = [v.name for v in bids_pth.glob("sub-*/ses-*/*") if v.is_dir()]
        sub_dirs.extend(tmp)
    datatypes = [v for v in set(sub_dirs) if is_known_bids_datatype(v)]
    return sorted(list(set(datatypes)))


def list_data_files(bids_pth: Path, sessions: list[str]) -> list[str]:
    """Return the list of files with the task entity."""
    files = [v.name for v in bids_pth.glob("sub-*/*/*_task-*")]
    if not sessions:
        return files
    tmp = [v.name for v in bids_pth.glob("sub-*/*/*/*_task-*")]
    files.extend(tmp)
    return files


def list_tasks(bids_pth: Path, sessions: list[str]) -> list[str]:
    files = list_data_files(bids_pth, sessions)
    tasks = [f.split("task-")[1].split("_")[0].split(".")[0] for f in files]
    tasks = list(set(tasks))
    return sorted(tasks)


def get_scan_duration(dataset_pth: Path, filepath: Path) -> tuple[int, float]:
    """Get only header of a nifti file and compute its acquisition time."""
    if "nii" in filepath.suffix or "gz" in filepath.suffix:
        script_path = _data_dir() / "read_nb_vols"

        cmd = f"   datalad fsspec-head -d {dataset_pth} -c 1024 {filepath.relative_to(dataset_pth)} | python {script_path}"
        cc_log.debug(cmd)
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if not result.stderr:
            tmp = result.stdout.replace("\n", "").split(" ")
            n_samples: int = int(tmp[0])
            repetition_time: float = float(tmp[1])
            return (n_samples, repetition_time)

        cc_log.error(f"   Could not get duration for: {filepath.relative_to(dataset_pth)}")
        cc_log.debug(result.stderr)
        return (0, np.nan)

    elif "vhdr" in filepath.suffix:
        info, n_samples = get_meeg_header(dataset_pth, filepath)
        if n_samples and info and info["sfreq"]:
            return (n_samples, info["sfreq"])

    return (0, np.nan)


def get_meeg_header(dataset_pth: Path, filepath: Path) -> tuple[None | dict[str, Any], int]:
    ds = api.Dataset(dataset_pth)
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
        return None, 0
    except FileNotFoundError:
        warn(f"FileNotFoundError for {filepath}", stacklevel=2)
        return None, 0


def created_on(dataset_pth: Path) -> str:
    """Use date of first commit as creation date."""
    result = subprocess.run(
        f'git -C {dataset_pth} log --reverse | sed -n -e "3,3p"',
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.replace("Date:", "").strip()


def count_stim_files(dataset_pth: Path) -> int:
    return len(list(dataset_pth.glob("sub-*/**/*stim.tsv.gz")))


def count_eeg_file_formats(dataset_pth: Path) -> dict[str, int]:
    SUPPORTED_FORMATS = ["bdf", "edf", "eeg", "set"]
    count = {
        format: len(list(dataset_pth.glob(f"sub-*/**/eeg/*_eeg.{format}")))
        for format in SUPPORTED_FORMATS
    }
    return count


def count_ieeg_file_formats(dataset_pth: Path) -> dict[str, int]:
    SUPPORTED_FORMATS = ["nwb", "edf", "eeg", "set", "mefd"]
    count = {
        format: len(list(dataset_pth.glob(f"sub-*/**/ieeg/*_ieeg.{format}")))
        for format in SUPPORTED_FORMATS
    }
    return count


def count_meg_file_formats(dataset_pth: Path) -> dict[str, int]:
    SUPPORTED_FORMATS = [".ds", "", ".fif", ".con", ".kdf", ".raw.mhd"]
    count = {
        format: len(list(dataset_pth.glob(f"sub-*/**/meg/*_meg{format}")))
        for format in SUPPORTED_FORMATS
    }
    return count


def get_number_meeg_channels(dataset_pth: Path, datatypes: list[str]) -> list[int]:
    first_sub = list_participants_in_dataset(dataset_pth)[0]
    nb_channels = []
    for target_datatype in ["ieeg", "eeg"]:
        if target_datatype in datatypes:
            files = dataset_pth.glob(f"{first_sub}/**/{target_datatype}/*_{target_datatype}.vhdr")
            for filepath in files:
                info, _ = get_meeg_header(dataset_pth, filepath)
                if info:
                    if nchan := info.get("nchan"):
                        nb_channels.append(nchan)
    return sorted(list(set(nb_channels)))


def get_duration(
    dataset_pth: Path, datatypes: list[str], tasks: list[str] | None
) -> dict[str, Iterable[tuple[int, float]] | dict[str, Iterable[tuple[int, float]]]]:
    first_sub = list_participants_in_dataset(dataset_pth)[0]

    cc_log.info(f" Getting 'scan' duration for {first_sub}")

    duration_all_datatypes: dict[
        str, Iterable[tuple[int, float]] | dict[str, Iterable[tuple[int, float]]]
    ] = {}

    for target_datatype in ["func", "pet", "ieeg", "eeg"]:
        if target_datatype in datatypes:
            if tasks is None:
                tasks = []
                if target_datatype == "pet":
                    files = dataset_pth.glob(f"{first_sub}/**/pet/{first_sub}*_pet.nii*")
                    duration_all_datatypes[target_datatype] = get_duration_for_datatype(
                        dataset_pth, files
                    )
                    return duration_all_datatypes
            for task_ in tasks:
                if target_datatype == "func":
                    files = dataset_pth.glob(
                        f"{first_sub}/**/func/{first_sub}*task-{task_}*_bold.nii*"
                    )
                if target_datatype == "pet":
                    files = dataset_pth.glob(
                        f"{first_sub}/**/func/{first_sub}*task-{task_}*_pet.nii*"
                    )
                elif target_datatype in ["eeg", "ieeg"]:
                    files = dataset_pth.glob(
                        f"{first_sub}/**/{target_datatype}/*_{target_datatype}.vhdr"
                    )
                if target_datatype not in duration_all_datatypes:
                    duration_all_datatypes[target_datatype] = {}
                duration_all_datatypes[target_datatype][task_] = get_duration_for_datatype(
                    dataset_pth, files
                )
    return duration_all_datatypes


def get_duration_for_datatype(
    dataset_pth: Path, files: Generator[Path, None, None]
) -> Iterable[tuple[int, float]]:
    scan_duration = []
    for filepath in files:
        cc_log.info(f"  {filepath.relative_to(dataset_pth)}")
        scan_duration.append(get_scan_duration(dataset_pth, filepath))
    return scan_duration


def get_authors(dataset_pth: Path) -> list[str]:
    if not (dataset_pth / "dataset_description.json").exists():
        return []
    with open(dataset_pth / "dataset_description.json") as f:
        dataset_description = json.load(f)
        return dataset_description.get("Authors", [])


def get_license(dataset_pth: Path) -> str:
    if not (dataset_pth / "dataset_description.json").exists():
        return "n/a"
    with open(dataset_pth / "dataset_description.json") as f:
        dataset_description = json.load(f)
        license = dataset_description.get("License", "n/a")
        license = license.replace("\n", "")
        if "Public Domain Dedication and License v1.0" in license:
            return "PDDL 1.0"
        return license


def get_references_and_links(dataset_pth: Path) -> list[str]:
    if not (dataset_pth / "dataset_description.json").exists():
        return []
    with open(dataset_pth / "dataset_description.json") as f:
        dataset_description = json.load(f)
        return dataset_description.get("ReferencesAndLinks", [])


def get_institutions(dataset_pth: Path) -> list[str]:
    """List institutions in JSON files in root folder and first subject.

    Assumes that first subject is representative of the dataset.
    """
    cc_log.info(" Getting institution")
    json_files = list(dataset_pth.glob("*.json"))
    first_subject = list_participants_in_dataset(dataset_pth)[0]
    json_files.extend(list(dataset_pth.glob(f"{first_subject}/**/*.json")))

    institutions = []
    ds = api.Dataset(dataset_pth)
    for json_file in json_files:
        if Path(json_file).name.startswith("."):
            continue

        cc_log.debug(f"  {json_file}")
        try:
            ds.get(json_file)
            with open(json_file) as f:
                json_dict = json.load(f)
                if tmp := construct_institution_string(json_dict).strip(", "):
                    institutions.append(tmp)

        except json.decoder.JSONDecodeError:
            cc_log.warning(f"Could not parse: {json_file}", stacklevel=2)
        except UnicodeDecodeError:
            cc_log.warning(f"Could not parse: {json_file}", stacklevel=2)
        except FileNotFoundError:
            cc_log.warning(f"Could not find: {json_file}", stacklevel=2)
        except IncompleteResultsError:
            cc_log.warning(f"Could not get: {json_file}", stacklevel=2)

    return sorted(list({x for x in institutions if x}))


def construct_institution_string(json_dict: Any) -> str:
    if not isinstance(json_dict, dict):
        return ""
    institution_name = json_dict.get("InstitutionName", "")
    if not isinstance(institution_name, str):
        institution_name = ""
    institution_address = json_dict.get("InstitutionAddress", "")
    if not isinstance(institution_address, str):
        institution_address = ""
    return ", ".join([institution_name.strip(), institution_address.strip()])


def get_dataset_size(dataset_pth: Path) -> str:
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


def count_sessions_tsv(dataset_pth: Path) -> int:
    return len(list(dataset_pth.glob("sub-*/*sessions.tsv")))


def count_scans_tsv(dataset_pth: Path) -> int:
    return len(list(dataset_pth.glob("sub-*/**/*scans.tsv")))


def count_physio_files(dataset_pth: Path) -> int:
    return len(list(dataset_pth.glob("sub-*/**/*physio.tsv.gz")))


def update(reset: bool = False, debug: bool = True) -> None:
    install_missing_datasets(use_superdataset=False)
    list_openneuro_derivatives()
    update_openneuro(reset=reset, debug=debug)


if __name__ == "__main__":
    update()
