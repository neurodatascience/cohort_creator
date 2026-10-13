from __future__ import annotations

import functools
import json
import logging
import os
import shutil
import subprocess
import sys
import warnings
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import mne
import numpy as np
import pandas as pd
import requests
import yaml
from datalad import api
from datalad.support.exceptions import IncompleteResultsError
from mne.io.brainvision.brainvision import _get_hdr_info
from rich.progress import Progress

from bids_inventory._utils import glob_files, list_participants_in_dataset, progress_bar
from bids_inventory.listing import (
    KNOWN_DATATYPES,
    _data_dir,
    _load_known_datasets,
    _openneuro_listing,
    known_datasets_df,
    save_known_datasets,
)
from bids_inventory.logger import bi_logger, set_current_dataset

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

cc_log = bi_logger()

logging.getLogger("datalad").setLevel(logging.WARNING)
logging.getLogger("datalad.gitrepo").setLevel(logging.ERROR)
# MNE prints info messages ("Setting channel info structure...") when reading headers
mne.set_log_level("WARNING")


CONFIG_ENV_VAR = "BIDS_INVENTORY_CONFIG"


@functools.lru_cache(maxsize=1)
def config() -> dict[str, Any]:
    """Return the configuration.

    The default configuration (``bids_inventory/data/config.yml``)
    is updated with the content of the YAML file
    whose path is in the ``BIDS_INVENTORY_CONFIG`` environment variable.
    """
    with open(_data_dir() / "config.yml") as f:
        cfg: dict[str, Any] = yaml.safe_load(f)
    if user_config := os.getenv(CONFIG_ENV_VAR):
        with open(Path(user_config).expanduser()) as f:
            cfg = _merge(cfg, yaml.safe_load(f) or {})
    return cfg


def _merge(default: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    merged = dict(default)
    for key, value in user.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def config_path(*keys: str) -> Path:
    """Return a path from the configuration.

    Raises an error explaining how to set it if it is not set.
    """
    value: Any = config()
    for key in keys:
        value = value.get(key) if isinstance(value, dict) else None
    if not value:
        raise ValueError(
            f"'{'.'.join(keys)}' is not set in the configuration.\n"
            "Set it in a YAML file and pass it with "
            "'bids_inventory update --config <file>' "
            f"or with the {CONFIG_ENV_VAR} environment variable.\n"
            f"See {_data_dir() / 'config.yml'} for the available settings."
        )
    return Path(value).expanduser()


def install_missing_datasets(use_superdataset: bool = False, jobs: int = 1) -> None:
    """Install unknown openneuro datasets.

    This script installs all the datasets from openneuro:
    - that are not in the openneuro.tsv file
    - OR that are not part of the datalad superdatasets.

    Parameters
    ----------
    use_superdataset : bool
       Set to ``True`` to only use datasets from the datalad superdatasets as known.

    jobs : int
       Number of datasets to install in parallel.
    """
    unknown_datasets = list_openneuro_raw(use_superdataset)

    if not unknown_datasets:
        cc_log.info("No new dataset found")
        return

    if os.getenv("CI"):
        output_dir = _data_dir() / "tmp"
    else:
        output_dir = config_path("local_paths", "openneuro", OPENNEURO)
    output_dir.mkdir(exist_ok=True, parents=True)

    cc_log.info(f"Installing {len(unknown_datasets)} datasets in {output_dir} ({jobs} at a time)")

    with (
        Progress() as progress,
        ThreadPoolExecutor(max_workers=jobs) as executor,
    ):
        task = progress.add_task("[green]Installing...", total=len(unknown_datasets))
        futures = {
            executor.submit(_install_openneuro_dataset, output_dir / dataset): dataset
            for dataset in sorted(unknown_datasets)
        }
        for future in as_completed(futures):
            status, message = future.result()
            log = cc_log.error if status == "failed" else cc_log.info
            log(f"{status}: {futures[future]} {message}".rstrip())
            progress.update(task, advance=1)


def _datalad_executable() -> str:
    """Return the datalad executable of the current environment, if any."""
    in_env = Path(sys.executable).parent / "datalad"
    return str(in_env) if in_env.exists() else (shutil.which("datalad") or "datalad")


def _install_openneuro_dataset(data_pth: Path) -> tuple[str, str]:
    """Install one openneuro dataset.

    Runs ``datalad install`` in a subprocess
    so that several datasets can be installed in parallel.

    Returns
    -------
    The status ("already present", "not found", "installed" or "failed")
    and a message with more details.
    """
    if data_pth.exists():
        return "already present", ""

    source = f"https://github.com/{OPENNEURO}/{data_pth.name}.git"
    response = requests.get(source)
    if response.status_code != 200:
        return "not found", f"(error {response.status_code} for {source})"

    result = subprocess.run(
        [_datalad_executable(), "install", "--source", source, str(data_pth)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "failed", result.stderr.strip().splitlines()[-1] if result.stderr.strip() else ""
    return "installed", ""


def list_openneuro_raw(use_superdataset: bool) -> set[str]:
    if use_superdataset:
        path_known_datasets = config_path("local_paths", "datalad", OPENNEURO)
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
    df.to_csv(_data_dir() / f"{OPENNEURO}.tsv", sep="\t", index=False)
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


def update_openneuro(reset: bool = False, debug: bool = True, jobs: int = 1) -> None:
    """Update list of datasets on openneuro and overwrite old tsv file.

    - this will add new datasets,
    - this will update the values the links to the derivatives datasets
    - this should fail if a dataset is already in the tsv file
    if they now exist

    Parameters
    ----------
    debug : bool
        If ``False``, will overwrite the listing with the current openneuro datasets.
        If ``True`` will save output in current directory and only index a few datasets.
    """
    datasets_df = _load_known_datasets(_openneuro_listing())
    datasets_df.replace({pd.NA: "n/a"}, inplace=True)
    datasets: dict[str, list[Any]] = {
        str(k): v for k, v in datasets_df.to_dict(orient="list").items()
    }

    output_file = _openneuro_listing()
    if debug:
        output_file = Path.cwd() / output_file.name

    if reset:
        datasets = init_dataset()
        input_dir = config_path("local_paths", "datalad", OPENNEURO)
        datasets = list_datasets_in_dir(
            datasets, input_dir, debug=debug, jobs=jobs, output_file=output_file
        )

    input_file = _data_dir() / f"{OPENNEURO}.tsv"
    new_openneuro_datasets = pd.read_csv(input_file, sep="\t")
    if len(new_openneuro_datasets) > 0:
        if os.getenv("CI"):
            input_dir = _data_dir() / "tmp"
        else:
            input_dir = config_path("local_paths", "openneuro", OPENNEURO)
        datasets = list_datasets_in_dir(
            datasets, input_dir, debug=debug, jobs=jobs, output_file=output_file
        )

    datasets_df = pd.DataFrame.from_dict(datasets)

    cc_log.info(f"Saving to {output_file}")
    save_known_datasets(datasets_df, output_file)


def known_derivatives() -> list[str]:
    """Focus on openneuro derivatives repositories."""
    tsv = _data_dir() / f"{OPENNEURO_DERIVATIVES}.tsv"
    if not tsv.exists():
        raise FileNotFoundError(f"{tsv} not found.\nRun 'list_derivatives.py' script to create it.")
    return [str(x) for x in pd.read_csv(tsv, sep="\t")["name"]]


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


def get_auth() -> tuple[str, str] | None:
    """Return credentials for the GitHub API.

    Unauthenticated requests quickly hit the GitHub API rate limit.
    Uses the GITHUB_TOKEN environment variable if set,
    otherwise the token file from the configuration.
    """
    username = config()["auth"].get("username") or "bids-inventory"

    if token := os.getenv("GITHUB_TOKEN"):
        return (username, token)

    if not config()["auth"].get("token_file"):
        cc_log.warning(
            "No GitHub token: the GitHub API may rate limit the update.\n"
            "Set the GITHUB_TOKEN environment variable or 'auth.token_file' in the configuration."
        )
        return None

    token_file = config_path("auth", "token_file")
    if not token_file.exists():
        cc_log.warning(f"Token file not found: {token_file}")
        return None
    return (username, token_file.read_text().strip())


def request_list_of_repos(
    gh_orga: str, page: int, auth: tuple[str, str] | None = None
) -> dict[str, str] | None:
    url = f"{gh_api_base_url()}{gh_orga}/repos?per_page=100&page={page}"
    cc_log.info(url)
    response = requests.get(url, auth=auth)
    if response.status_code != 200:
        # fail loudly: an incomplete list of repos would silently skip datasets
        raise RuntimeError(f"Error {response.status_code} for {url}: {response.text}")
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
    jobs: int = 1,
    output_file: Path | None = None,
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

    jobs : int, default = 1
        Number of NIfTI headers to read in parallel.

    output_file : Path | None, default = None
        If set, the listing is saved to this file after each dataset is indexed,
        so that an interrupted update does not lose its progress.

    Datasets already in ``datasets`` are skipped:
    restarting an interrupted update only indexes the remaining datasets.

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

    known = set(datasets["name"])
    failed: list[str] = []
    try:
        with progress_bar(text="Updating") as progress:
            task = progress.add_task(description="updating", total=len(raw_datasets))

            i = 0
            for index, dataset_pth in enumerate(raw_datasets, start=1):
                print()
                cc_log.info(f"{dataset_pth.name}")
                set_current_dataset(f"{dataset_pth.name} {index}/{len(raw_datasets)}")

                if f"{study_prefix}{dataset_pth.name}" in known:
                    cc_log.info("  already in the listing: skipping")
                    progress.update(task, advance=1)
                    continue

                if not _check_dataset(dataset_pth):
                    progress.update(task, advance=1)
                    continue
                i += 1
                if debug and i > MIN_NB_DATASETS:
                    break

                # update dataset to make sure we get the latest version
                ds = api.Dataset(dataset_pth)
                if update_merge:
                    ds.update(how="merge", result_renderer="disabled")
                try:
                    _get_file(ds, dataset_pth / "dataset_description.json")
                except IncompleteResultsError:
                    cc_log.warning("Could not get dataset_description.json or is missing.")

                # for openneuro datasets try to eanabe annex remote on S3
                # to allow using datalad fsspec
                # if dataset_pth.name.startswith('ds'):
                enable_S3_remote(dataset_pth)

                try:
                    dataset = get_info_dataset(dataset_pth, study_prefix, jobs=jobs)
                    dataset = add_derivatives(dataset, dataset_pth, derivatives)
                except Exception:
                    cc_log.exception(f"Could not index {dataset_pth.name}: skipping it.")
                    failed.append(dataset_pth.name)
                    progress.update(task, advance=1)
                    continue

                for keys in datasets:
                    datasets[keys].append(dataset[keys])
                known.add(dataset["name"])

                if output_file is not None:
                    save_known_datasets(pd.DataFrame.from_dict(datasets), output_file)

                progress.update(task, advance=1)

    finally:
        set_current_dataset(None)

    if failed:
        cc_log.error(f"{len(failed)} datasets could not be indexed: {sorted(failed)}")

    return datasets


def _check_dataset(dataset_pth: Path) -> bool:
    raw_url = get_raw_url(dataset_pth)
    if not raw_url.startswith("git@"):
        try:
            response = requests.get(raw_url)
        except requests.exceptions.InvalidSchema:
            cc_log.error(f"No connection adapters were found for: {raw_url}")
            return False
        except requests.exceptions.ConnectionError:
            cc_log.error(f"Failed to establish a new connection for: {raw_url}")
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


def get_info_dataset(dataset_pth: Path, study_prefix: str, jobs: int = 1) -> DATASET_TYPE:
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

    dataset["duration"] = get_duration(dataset_pth, datatypes, tasks, jobs=jobs)

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
        cc_log.warning(f"Could not parse: {participant_tsv}")
        return ["cannot be parsed"]
    except UnicodeDecodeError:
        cc_log.warning(f"Could not parse: {participant_tsv}")
        return ["cannot be parsed"]


def is_known_bids_datatype(datatype: str) -> bool:
    return datatype in KNOWN_DATATYPES


def list_datatypes(bids_pth: Path, sessions: list[str]) -> list[str]:
    sub_dirs = [v.name for v in glob_files(bids_pth, "sub-*/*") if v.is_dir()]
    if sessions:
        tmp = [v.name for v in glob_files(bids_pth, "sub-*/ses-*/*") if v.is_dir()]
        sub_dirs.extend(tmp)
    datatypes = [v for v in set(sub_dirs) if is_known_bids_datatype(v)]
    return sorted(list(set(datatypes)))


def list_data_files(bids_pth: Path, sessions: list[str]) -> list[str]:
    """Return the list of files with the task entity."""
    files = [v.name for v in glob_files(bids_pth, "sub-*/*/*_task-*")]
    if not sessions:
        return files
    tmp = [v.name for v in glob_files(bids_pth, "sub-*/*/*/*_task-*")]
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

        # only stream the beginning of the file and read the header from it
        head_cmd = [
            _datalad_executable(),
            "fsspec-head",
            "-d",
            str(dataset_pth),
            "-c",
            "1024",
            str(filepath.relative_to(dataset_pth)),
        ]
        # use the python of this environment (with nibabel) whatever the PATH
        read_cmd = [sys.executable, str(script_path)]
        cc_log.debug(f"{' '.join(head_cmd)} | {' '.join(read_cmd)}")
        with subprocess.Popen(head_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as head:
            result = subprocess.run(
                read_cmd, stdin=head.stdout, capture_output=True, text=True, check=False
            )
            assert head.stdout is not None
            head.stdout.close()
            head_stderr = head.stderr.read().decode() if head.stderr else ""

        try:
            tmp = result.stdout.replace("\n", "").split(" ")
            n_samples: int = int(tmp[0])
            repetition_time: float = float(tmp[1])
            return (n_samples, repetition_time)
        except (ValueError, IndexError):
            cc_log.error(f"Could not get duration for: {filepath.relative_to(dataset_pth)}")
            cc_log.debug(f"{head_stderr}\n{result.stderr}")
            return (0, np.nan)

    elif "vhdr" in filepath.suffix:
        info, n_samples = get_meeg_header(dataset_pth, filepath)
        if n_samples and info and info["sfreq"]:
            # same convention as for MRI: (number of samples, duration of a sample)
            return (n_samples, 1 / float(info["sfreq"]))

    return (0, np.nan)


def _get_file(ds: api.Dataset, filepath: Path) -> None:
    """Get the content of a file without datalad printing its results."""
    ds.get(filepath, result_renderer="disabled")
    cc_log.debug(f"  got {filepath}")


def get_meeg_header(dataset_pth: Path, filepath: Path) -> tuple[None | dict[str, Any], int]:
    ds = api.Dataset(dataset_pth)
    try:
        _get_file(ds, filepath)
        _get_file(ds, filepath.with_suffix(".vmrk"))
        # MNE reports problems with the header as python warnings:
        # log them instead of printing them
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
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
        for w in caught:
            cc_log.warning(f"{filepath.relative_to(dataset_pth)}: {w.message}")
        return info, n_samples
    except IncompleteResultsError:
        cc_log.warning(f"Could not get {filepath.relative_to(dataset_pth)}")
        return None, 0
    except FileNotFoundError:
        cc_log.warning(f"File not found: {filepath.relative_to(dataset_pth)}")
        return None, 0
    except Exception as e:
        # headers in third party datasets can be malformed in many ways:
        # one bad file should not stop the update
        cc_log.warning(f"Could not read header of {filepath.relative_to(dataset_pth)}: {e!r}")
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
    return len(list(glob_files(dataset_pth, "sub-*/**/*stim.tsv.gz")))


def count_eeg_file_formats(dataset_pth: Path) -> dict[str, int]:
    SUPPORTED_FORMATS = ["bdf", "edf", "eeg", "set"]
    count = {
        format: len(list(glob_files(dataset_pth, f"sub-*/**/eeg/*_eeg.{format}")))
        for format in SUPPORTED_FORMATS
    }
    return count


def count_ieeg_file_formats(dataset_pth: Path) -> dict[str, int]:
    SUPPORTED_FORMATS = ["nwb", "edf", "eeg", "set", "mefd"]
    count = {
        format: len(list(glob_files(dataset_pth, f"sub-*/**/ieeg/*_ieeg.{format}")))
        for format in SUPPORTED_FORMATS
    }
    return count


def count_meg_file_formats(dataset_pth: Path) -> dict[str, int]:
    SUPPORTED_FORMATS = [".ds", "", ".fif", ".con", ".kdf", ".raw.mhd"]
    count = {
        format: len(list(glob_files(dataset_pth, f"sub-*/**/meg/*_meg{format}")))
        for format in SUPPORTED_FORMATS
    }
    return count


def get_number_meeg_channels(dataset_pth: Path, datatypes: list[str]) -> list[int]:
    first_sub = list_participants_in_dataset(dataset_pth)[0]
    nb_channels = []
    for target_datatype in ["ieeg", "eeg"]:
        if target_datatype in datatypes:
            files = glob_files(
                dataset_pth, f"{first_sub}/**/{target_datatype}/*_{target_datatype}.vhdr"
            )
            for filepath in files:
                info, _ = get_meeg_header(dataset_pth, filepath)
                if info:
                    if nchan := info.get("nchan"):
                        nb_channels.append(nchan)
    return sorted(list(set(nb_channels)))


def get_duration(
    dataset_pth: Path, datatypes: list[str], tasks: list[str] | None, jobs: int = 1
) -> dict[str, Iterable[tuple[int, float]] | dict[str, Iterable[tuple[int, float]]]]:
    """Get the duration of each run of the first subject.

    Parameters
    ----------
    jobs : int
        Number of NIfTI headers to read in parallel.
    """
    first_sub = list_participants_in_dataset(dataset_pth)[0]

    cc_log.info(f" Getting 'scan' duration for {first_sub}")

    files_per_datatype = _files_for_duration(dataset_pth, first_sub, datatypes, tasks)

    # then read all the headers at once
    all_files = []
    for value in files_per_datatype.values():
        for files in value.values() if isinstance(value, dict) else [value]:
            all_files.extend(files)
    durations = get_scan_durations(dataset_pth, all_files, jobs=jobs)

    duration_all_datatypes: dict[
        str, Iterable[tuple[int, float]] | dict[str, Iterable[tuple[int, float]]]
    ] = {}
    for datatype, value in files_per_datatype.items():
        if isinstance(value, dict):
            duration_all_datatypes[datatype] = {
                task: [durations[x] for x in files] for task, files in value.items()
            }
        else:
            duration_all_datatypes[datatype] = [durations[x] for x in value]
    return duration_all_datatypes


def _files_for_duration(
    dataset_pth: Path, first_sub: str, datatypes: list[str], tasks: list[str] | None
) -> dict[str, list[Path] | dict[str, list[Path]]]:
    """List the files to read to get the duration of each datatype (and task)."""
    files_per_datatype: dict[str, list[Path] | dict[str, list[Path]]] = {}
    for target_datatype in ["func", "pet", "ieeg", "eeg"]:
        if target_datatype in datatypes:
            if tasks is None:
                tasks = []
                if target_datatype == "pet":
                    files_per_datatype[target_datatype] = glob_files(
                        dataset_pth, f"{first_sub}/**/pet/{first_sub}*_pet.nii*"
                    )
                    break
            files_per_task: dict[str, list[Path]] = {}
            for task_ in tasks:
                if target_datatype == "func":
                    files = glob_files(
                        dataset_pth, f"{first_sub}/**/func/{first_sub}*task-{task_}*_bold.nii*"
                    )
                elif target_datatype == "pet":
                    files = glob_files(
                        dataset_pth, f"{first_sub}/**/pet/{first_sub}*task-{task_}*_pet.nii*"
                    )
                else:
                    files = glob_files(
                        dataset_pth,
                        f"{first_sub}/**/{target_datatype}/{first_sub}*task-{task_}*_{target_datatype}.vhdr",
                    )
                files_per_task[task_] = files
            if files_per_task:
                files_per_datatype[target_datatype] = files_per_task
    return files_per_datatype


def get_scan_durations(
    dataset_pth: Path, files: Iterable[Path], jobs: int = 1
) -> dict[Path, tuple[int, float]]:
    """Get the duration of several runs.

    NIfTI headers are read in parallel (each in its own subprocess).
    M/EEG headers are read one after the other
    as they are read with the datalad python API that is not guaranteed to be thread safe.
    """
    files = list(dict.fromkeys(files))
    for filepath in files:
        cc_log.info(f"  {filepath.relative_to(dataset_pth)}")

    nifti = [x for x in files if "nii" in x.suffix or "gz" in x.suffix]
    others = [x for x in files if x not in nifti]

    durations: dict[Path, tuple[int, float]] = {}
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        for filepath, duration in zip(
            nifti, executor.map(lambda x: get_scan_duration(dataset_pth, x), nifti)
        ):
            durations[filepath] = duration
    for filepath in others:
        durations[filepath] = get_scan_duration(dataset_pth, filepath)
    return durations


def get_duration_for_datatype(
    dataset_pth: Path, files: Iterable[Path], jobs: int = 1
) -> Iterable[tuple[int, float]]:
    files = list(files)
    durations = get_scan_durations(dataset_pth, files, jobs=jobs)
    return [durations[x] for x in files]


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
    json_files = list(glob_files(dataset_pth, "*.json"))
    first_subject = list_participants_in_dataset(dataset_pth)[0]
    json_files.extend(list(glob_files(dataset_pth, f"{first_subject}/**/*.json")))

    institutions = []
    ds = api.Dataset(dataset_pth)
    for json_file in json_files:
        if Path(json_file).name.startswith("."):
            continue

        cc_log.debug(f"  {json_file}")
        try:
            _get_file(ds, Path(json_file))
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
    return f"{institution_name.strip()}, {institution_address.strip()}"


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
    sessions = [
        v.name.replace("ses-", "") for v in glob_files(dataset_pth, "sub-*/ses-*") if v.is_dir()
    ]
    return sorted(list(set(sessions)))


def check_task(
    tasks: list[str], datatypes: list[str], sessions: list[str], dataset_pth: Path
) -> None:
    """Check if tasks are present in dataset with datatypes that can have tasks."""
    if (
        any(mod in datatypes for mod in ["func", "eeg", "ieeg", "meg", "beh", "motion"])
        and not tasks
    ):
        cc_log.warning(
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
        if der_datasets := glob_files(dataset_pth, f"derivatives/*{der}*"):
            for i in der_datasets:
                dataset[der] = f"{URL_OPENNEURO}{dataset_name}/tree/main/derivatives/{i.name}"

    return dataset


def count_sessions_tsv(dataset_pth: Path) -> int:
    return len(list(glob_files(dataset_pth, "sub-*/*sessions.tsv")))


def count_scans_tsv(dataset_pth: Path) -> int:
    return len(list(glob_files(dataset_pth, "sub-*/**/*scans.tsv")))


def count_physio_files(dataset_pth: Path) -> int:
    return len(list(glob_files(dataset_pth, "sub-*/**/*physio.tsv.gz")))


def update(reset: bool = False, debug: bool = True, jobs: int = 1) -> None:
    if not os.getenv("CI"):
        # fail early if the folder where to install new datasets is not set
        config_path("local_paths", "openneuro", OPENNEURO)
    install_missing_datasets(use_superdataset=False, jobs=jobs)
    list_openneuro_derivatives()
    update_openneuro(reset=reset, debug=debug, jobs=jobs)


if __name__ == "__main__":
    update()
