import functools
import json
import logging
import os
import re
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
from mne.io.brainvision.brainvision import _fmt_byte_dict as _BRAINVISION_BYTES
from mne.io.brainvision.brainvision import _get_hdr_info
from rich.progress import Progress

from bids_inventory._utils import glob_files, list_participants_in_dataset, progress_bar
from bids_inventory.listing import (
    KNOWN_DATATYPES,
    _data_dir,
    _load_known_datasets,
    _non_openneuro_listing,
    _openneuro_listing,
    known_datasets_df,
    save_known_datasets,
    skipped_datasets,
)
from bids_inventory.logger import bi_logger, set_current_dataset
from bids_inventory.models import RUNS_DURATION, BidsDataset

OPENNEURO = "OpenNeuroDatasets"
OPENNEURO_DERIVATIVES = "OpenNeuroDerivatives"
URL_OPENNEURO = f"https://github.com/{OPENNEURO}/"
URL_OPENNEURO_DERIVATIVES = f"https://github.com/{OPENNEURO_DERIVATIVES}/"
URL_RAW_OPENNEURO_DERIVATIVES = f"https://raw.githubusercontent.com/{OPENNEURO_DERIVATIVES}/"

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


def install_missing_datasets(jobs: int = 1, reindex: bool = False) -> None:
    """Install the openneuro datasets that are not in the listing.

    - datasets of the datalad superdataset are installed in the superdataset,
    - the datasets missing from the superdataset are installed
      in ``local_paths.openneuro.OpenNeuroDatasets``.

    Parameters
    ----------
    jobs : int
       Number of datasets to install in parallel.

    reindex : bool
       Install all the datasets missing locally,
       not only those missing from the listing.
    """
    unknown_datasets = list_openneuro_raw(reindex=reindex)

    if not unknown_datasets:
        cc_log.info("No new dataset found")
        return

    if (superdataset := superdataset_dir()) is not None:
        in_superdataset, installed = superdataset_content()
        if to_install := sorted((unknown_datasets & in_superdataset) - installed):
            _install_in_superdataset(superdataset, to_install, jobs=jobs)
        unknown_datasets -= in_superdataset
        if not unknown_datasets:
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
        cc_log.debug(f"{result.stdout}\n{result.stderr}")
        return "failed", _error_reason(result.stdout, result.stderr)
    return "installed", ""


def superdataset_dir() -> Path | None:
    """Return the openneuro folder of the datalad superdataset.

    Set with ``local_paths.datalad.OpenNeuroDatasets``: required, except in CI.
    Datasets are indexed from the superdataset,
    and only the datasets missing from it are installed elsewhere.
    """
    if os.getenv("CI"):
        return None
    path = config_path("local_paths", "datalad", OPENNEURO)
    if not path.is_dir():
        raise ValueError(
            f"Datalad superdataset not found: {path}\n"
            "Install it with 'datalad install ///openneuro' "
            "or fix 'local_paths.datalad.OpenNeuroDatasets' in the configuration."
        )
    return path


def derivatives_superdataset_dir() -> Path | None:
    """Return the folder of the OpenNeuroDerivatives datalad superdataset.

    Set with ``local_paths.datalad.OpenNeuroDerivatives``: required, except in CI.
    """
    if os.getenv("CI"):
        return None
    path = config_path("local_paths", "datalad", OPENNEURO_DERIVATIVES)
    if not (path / ".git").exists():
        raise ValueError(
            f"Datalad superdataset of the derivatives not found or not installed: {path}\n"
            f"Install it with 'datalad get -n {path}' "
            "or fix 'local_paths.datalad.OpenNeuroDerivatives' in the configuration."
        )
    return path


def superdataset_content() -> tuple[set[str], set[str]]:
    """Return the datasets of the datalad superdataset, and those that are installed."""
    if (path := superdataset_dir()) is None:
        return set(), set()
    # datasets of the superdataset that are not installed are empty folders
    in_superdataset = {x.name for x in path.glob("ds*") if x.is_dir()}
    installed = {x for x in in_superdataset if (path / x / ".git").exists()}
    return in_superdataset, installed


def superdataset_datasets() -> list[str]:
    """List the datasets installed in the datalad superdataset."""
    return sorted(superdataset_content()[1])


def _install_in_superdataset(superdataset: Path, names: list[str], jobs: int = 1) -> None:
    """Install datasets of the datalad superdataset, in the superdataset.

    A single ``datalad get -n`` installs them ``jobs`` at a time:
    several datalad processes changing the same superdataset could conflict.
    """
    cc_log.info(
        f"Installing {len(names)} datasets in the datalad superdataset {superdataset} "
        f"({jobs} at a time)"
    )
    chunk_size = 50
    with Progress() as progress:
        task = progress.add_task("[green]Installing...", total=len(names))
        for i in range(0, len(names), chunk_size):
            chunk = names[i : i + chunk_size]
            result = subprocess.run(
                [_datalad_executable(), "-f", "json", "get", "-n", "-J", str(jobs), "-d", "."]
                + chunk,
                cwd=superdataset,
                capture_output=True,
                text=True,
            )
            reported = set()
            for line in result.stdout.splitlines():
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                name = Path(record.get("path", "")).name
                if name not in chunk or name in reported:
                    continue
                reported.add(name)
                if record.get("status") in ("ok", "notneeded"):
                    cc_log.info(f"installed: {name}")
                else:
                    cc_log.error(f"failed: {name} ({_datalad_message(record)})")
            for name in sorted(set(chunk) - reported):
                cc_log.error(
                    f"failed: {name} ({_error_reason(result.stderr) or 'no result from datalad'})"
                )
            progress.update(task, advance=len(chunk))


def _datalad_message(record: dict[str, Any]) -> str:
    """Format the message of a datalad result: a string or [format, *args]."""
    message = record.get("message", "")
    if isinstance(message, list) and message:
        try:
            message = message[0] % tuple(message[1:])
        except (TypeError, ValueError):
            message = " ".join(str(x) for x in message)
    return (
        str(message).strip().splitlines()[0] if str(message).strip() else str(record.get("status"))
    )


def list_openneuro_raw(reindex: bool = False) -> set[str]:
    """List the openneuro datasets that are not in the listing (all of them when re-indexing)."""
    known_datasets = [] if reindex else known_datasets_df()["name"].values.tolist()

    print()
    cc_log.info("Getting list of public openneuro raw datasets from the GitHub API.")
    datasets = get_list_of_datasets(OPENNEURO)
    unknown_datasets = set(datasets) - set(known_datasets)

    if skipped := unknown_datasets & set(skipped_datasets()):
        cc_log.info(f"Skipping {len(skipped)} datasets listed in skipped_datasets.csv")
        unknown_datasets -= skipped

    cc_log.info(f"{len(unknown_datasets)} unknown datasets")
    cc_log.info(sorted(unknown_datasets))

    df = pd.DataFrame({"name": datasets})
    df.to_csv(_data_dir() / f"{OPENNEURO}.tsv", sep="\t", index=False)
    return unknown_datasets


def list_openneuro_derivatives() -> None:
    """List the openneuro derivatives datasets.

    Those of the datalad superdataset first,
    then those of the GitHub organization that are missing from it.

    Saves the listing to a TSV file.
    """
    datasets: set[str] = set()
    if (superdataset := derivatives_superdataset_dir()) is not None:
        # subdatasets are listed as folders even when they are not installed
        datasets = {x.name for x in superdataset.glob("ds*-*") if x.is_dir()}
        cc_log.info(f"{len(datasets)} derivatives datasets in {superdataset}")

    print()
    cc_log.info("Getting list of public openneuro derivatives datasets from the GitHub API.")
    on_github = set(get_list_of_datasets(gh_orga=OPENNEURO_DERIVATIVES))
    if superdataset is not None and (only_on_github := on_github - datasets):
        cc_log.info(
            f"{len(only_on_github)} derivatives datasets only on GitHub "
            f"(not in the superdataset yet): {sorted(only_on_github)}"
        )
    datasets |= on_github

    df = pd.DataFrame({"name": sorted(datasets)})
    df.to_csv(_data_dir() / f"{OPENNEURO_DERIVATIVES}.tsv", sep="\t", index=False)


def update_openneuro(debug: bool = True, jobs: int = 1, reindex: bool = False) -> None:
    """Index the openneuro datasets installed locally and update the listing.

    Parameters
    ----------
    debug : bool
        If ``False``, will overwrite the listing with the current openneuro datasets.
        If ``True`` will save output in current directory and only index a few datasets.

    reindex : bool
        Index again the datasets already in the listing.
    """
    datasets_df = _load_known_datasets(_openneuro_listing())
    datasets_df.replace({pd.NA: "n/a"}, inplace=True)
    datasets = listing_to_dict(datasets_df)

    output_file = _openneuro_listing()
    if debug:
        output_file = Path.cwd() / output_file.name

    input_file = _data_dir() / f"{OPENNEURO}.tsv"
    new_openneuro_datasets = pd.read_csv(input_file, sep="\t")
    if len(new_openneuro_datasets) > 0:
        # datasets installed in the datalad superdataset are indexed from there,
        # the others from the folder where the update installs them
        superdataset = superdataset_dir()
        if superdataset is not None and (in_superdataset := superdataset_datasets()):
            datasets = list_datasets_in_dir(
                datasets,
                superdataset,
                debug=debug,
                include=in_superdataset,
                jobs=jobs,
                output_file=output_file,
                reindex=reindex,
            )
        if os.getenv("CI"):
            input_dir = _data_dir() / "tmp"
        else:
            input_dir = config_path("local_paths", "openneuro", OPENNEURO)
        datasets = list_datasets_in_dir(
            datasets,
            input_dir,
            debug=debug,
            jobs=jobs,
            output_file=output_file,
            reindex=reindex,
        )

    datasets_df = pd.DataFrame.from_dict(datasets)

    cc_log.info(f"Saving to {output_file}")
    save_known_datasets(datasets_df, output_file)

    if reindex:
        _finish_reindex(datasets, output_file)


# Datasets that are not on OpenNeuro:
# (folder in local_paths.non_openneuro, prefix added to their name, datasets to include)
NON_OPENNEURO_COLLECTIONS: list[tuple[str, str, list[str] | None]] = [
    ("abide", "ABIDE_", None),
    ("abide2", "ABIDE2_", None),
    ("adhd200", "ADHD200_", None),
    ("corr", "CORR_", None),
    (
        "cneuromod",
        "CNEUROMOD_",
        ["anat", "friends", "harrypotter", "hcptrt", "movie10", "shinobi", "shinobi_training"],
    ),
]


def update_non_openneuro(debug: bool = True, jobs: int = 1, reindex: bool = False) -> None:
    """Update the listing of datasets that are not on OpenNeuro (ABIDE, CoRR...).

    The datasets must be installed in the folder set by ``local_paths.non_openneuro``
    in the configuration, for example with ``tools/install_extra_datasets.sh``.
    """
    base_dir = config_path("local_paths", "non_openneuro")

    datasets_df = _load_known_datasets(_non_openneuro_listing())
    datasets_df.replace({pd.NA: "n/a"}, inplace=True)
    datasets = listing_to_dict(datasets_df)

    output_file = _non_openneuro_listing()
    if debug:
        output_file = Path.cwd() / output_file.name

    for folder, study_prefix, include in NON_OPENNEURO_COLLECTIONS:
        if not (base_dir / folder).is_dir():
            cc_log.warning(f"{base_dir / folder} not found: skipping {study_prefix.strip('_')}")
            continue
        datasets = list_datasets_in_dir(
            datasets,
            base_dir / folder,
            debug=debug,
            dataset_name_prefix="",
            study_prefix=study_prefix,
            include=include,
            jobs=jobs,
            output_file=output_file,
            reindex=reindex,
        )

    cc_log.info(f"Saving to {output_file}")
    save_known_datasets(pd.DataFrame.from_dict(datasets), output_file)

    if reindex:
        _finish_reindex(datasets, output_file)


def _finish_reindex(datasets: dict[str, list[Any]], output_file: Path) -> None:
    """Report the datasets not re-indexed, or remove the progress file if all were."""
    reindex_file = reindex_progress_file(output_file)
    if reindex_file is None:
        return
    not_reindexed = set(datasets["name"]) - _read_reindex_progress(reindex_file)
    if not_reindexed:
        # for example datasets not installed locally or that failed:
        # keep the progress file so that running the re-index again retries them
        cc_log.warning(
            f"{len(not_reindexed)} datasets were not re-indexed "
            f"and keep their previous entry: {sorted(not_reindexed)}"
        )
    else:
        reindex_file.unlink(missing_ok=True)
        cc_log.info("All datasets re-indexed")


def known_derivatives() -> list[str]:
    """Focus on openneuro derivatives repositories."""
    tsv = _data_dir() / f"{OPENNEURO_DERIVATIVES}.tsv"
    if not tsv.exists():
        raise FileNotFoundError(f"{tsv} not found.\nRun 'list_derivatives.py' script to create it.")
    return [str(x) for x in pd.read_csv(tsv, sep="\t")["name"]]


def gh_api_base_url() -> str:
    return "https://api.github.com/orgs/"


def get_list_of_datasets(gh_orga: str) -> list[str]:
    """List the datasets of a GitHub organization.

    Empty repositories are left out: OpenNeuro creates them for datasets
    that are not public (yet), or that were deleted.
    """
    auth = get_auth()
    repos: list[dict[str, Any]] = []
    resp: list[dict[str, Any]] | bool | None = True
    page = 1
    while resp:
        resp = request_list_of_repos(gh_orga, page=page, auth=auth)
        if resp is None:
            break
        repos.extend(resp)
        page += 1
    repos = [x for x in repos if str(x["name"]).startswith("ds")]
    if empty := sorted(str(x["name"]) for x in repos if x.get("size") == 0):
        cc_log.info(f"Ignoring {len(empty)} empty repositories (datasets not public on OpenNeuro)")
        cc_log.debug(empty)
    return [str(x["name"]) for x in repos if x.get("size") != 0]


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
) -> list[dict[str, Any]] | None:
    url = f"{gh_api_base_url()}{gh_orga}/repos?per_page=100&page={page}"
    cc_log.info(url)
    response = requests.get(url, auth=auth)
    if response.status_code != 200:
        # fail loudly: an incomplete list of repos would silently skip datasets
        raise RuntimeError(f"Error {response.status_code} for {url}: {response.text}")
    return response.json()


def init_dataset() -> dict[str, list[Any]]:
    """Return an empty listing: one list per field of a dataset."""
    return {key: [] for key in BidsDataset.model_fields}


def listing_to_dict(df: pd.DataFrame) -> dict[str, list[Any]]:
    """Convert a listing to the dict used during the update.

    Columns added since the listing was saved are filled with "n/a".
    """
    datasets: dict[str, list[Any]] = {str(k): v for k, v in df.to_dict(orient="list").items()}
    for key in init_dataset():
        datasets.setdefault(key, ["n/a"] * len(df))
    return datasets


def new_dataset(name: str) -> BidsDataset:
    return BidsDataset(name=name)


def _add_or_replace(datasets: dict[str, list[Any]], dataset: BidsDataset) -> None:
    """Add a dataset to the listing, or replace its entry if it is already there."""
    row = dataset.model_dump()
    if dataset.name in datasets["name"]:
        index = datasets["name"].index(dataset.name)
        for keys in datasets:
            datasets[keys][index] = row[keys]
    else:
        for keys in datasets:
            datasets[keys].append(row[keys])


def _save_progress(
    datasets: dict[str, list[Any]],
    name: str,
    output_file: Path | None,
    reindex_file: Path | None,
) -> None:
    """Save the listing after the dataset ``name`` was indexed."""
    if output_file is not None:
        save_known_datasets(pd.DataFrame.from_dict(datasets), output_file)
    if reindex_file is not None:
        with open(reindex_file, "a") as f:
            f.write(f"{name}\n")


def reindex_progress_file(output_file: Path | None) -> Path | None:
    """File listing the datasets re-indexed so far (one per line)."""
    if output_file is None:
        return None
    return output_file.with_name(f"{output_file.name}.reindexed")


def _read_reindex_progress(reindex_file: Path | None) -> set[str]:
    if reindex_file is None or not reindex_file.exists():
        return set()
    return {x.strip() for x in reindex_file.read_text().splitlines() if x.strip()}


def _skip_reason(name: str, study_prefix: str, known: set[str], skipped: dict[str, str]) -> str:
    """Return why a dataset must not be indexed (empty if it must be)."""
    if f"{study_prefix}{name}" in known:
        return "already indexed"
    if name in skipped:
        return f"in skipped_datasets.csv ({skipped[name]})"
    return ""


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
    reindex: bool = False,
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

    reindex : bool, default = False
        Index again the datasets already in ``datasets`` and replace their entry.
        The datasets re-indexed so far are tracked in ``<output_file>.reindexed``
        so that an interrupted re-index can be resumed.

    Otherwise datasets already in ``datasets`` are skipped:
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
    reindex_file = reindex_progress_file(output_file) if reindex else None
    if reindex:
        known = _read_reindex_progress(reindex_file)
        cc_log.info(f"Re-indexing: {len(known)} datasets already re-indexed")

    skipped = skipped_datasets()
    failed: list[str] = []
    try:
        with progress_bar(text="Updating") as progress:
            task = progress.add_task(description="updating", total=len(raw_datasets))

            i = 0
            for index, dataset_pth in enumerate(raw_datasets, start=1):
                print()
                cc_log.info(f"{dataset_pth.name}")
                set_current_dataset(f"{dataset_pth.name} {index}/{len(raw_datasets)}")

                if reason := _skip_reason(dataset_pth.name, study_prefix, known, skipped):
                    cc_log.info(f"  skipping: {reason}")
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

                _add_or_replace(datasets, dataset)
                known.add(dataset.name)
                _save_progress(datasets, dataset.name, output_file, reindex_file)

                progress.update(task, advance=1)

    finally:
        set_current_dataset(None)

    if failed:
        cc_log.error(f"{len(failed)} datasets could not be indexed: {sorted(failed)}")

    return datasets


def _is_empty_repository(dataset_pth: Path) -> bool:
    """Return True for a git repository without any commit."""
    if not (dataset_pth / ".git").exists():
        return False
    result = subprocess.run(
        ["git", "-C", str(dataset_pth), "rev-parse", "--quiet", "--verify", "HEAD"],
        capture_output=True,
    )
    return result.returncode != 0


def _check_dataset(dataset_pth: Path) -> bool:
    if _is_empty_repository(dataset_pth):
        # for example datasets that are not public on OpenNeuro
        cc_log.info(f"  empty repository: skipping {dataset_pth.name}")
        return False
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
        siblings = api.Dataset(dataset_pth).siblings(name="origin", result_renderer="disabled")
        return siblings[0]["url"]


def get_info_dataset(dataset_pth: Path, study_prefix: str, jobs: int = 1) -> BidsDataset:
    dataset_name = dataset_pth.name

    dataset = new_dataset(f"{study_prefix}{dataset_name}")

    dataset.raw = get_raw_url(dataset_pth)

    dataset.created_on = created_on(dataset_pth)

    dataset.nb_subjects = get_nb_subjects(dataset_pth)

    sessions = list_sessions(dataset_pth)
    dataset.sessions = sessions

    datatypes = list_datatypes(dataset_pth, sessions=sessions)
    dataset.datatypes = datatypes

    dataset.size = get_dataset_size(dataset_pth)

    tasks = None
    if any(
        mod in datatypes
        for mod in ["func", "eeg", "ieeg", "meg", "beh", "perf", "pet", "motion", "nirs"]
    ):
        tasks = list_tasks(dataset_pth, sessions=sessions)
        check_task(tasks, datatypes, sessions, dataset_pth)
        dataset.tasks = sorted(tasks)

    tsv_status, json_status, columns = has_participant_tsv(dataset_pth)
    dataset.has_participant_tsv = tsv_status
    dataset.has_participant_json = json_status
    dataset.participant_columns = columns

    dataset.nb_sessions_tsv = count_sessions_tsv(dataset_pth)
    dataset.nb_scans_tsv = count_scans_tsv(dataset_pth)
    dataset.nb_physio_files = count_physio_files(dataset_pth)
    dataset.nb_stim_files = count_stim_files(dataset_pth)

    dataset.has_phenotype_dir = bool((dataset_pth / "phenotype").exists())
    dataset.has_stimuli_dir = bool((dataset_pth / "stimuli").exists())

    dataset.eeg_file_formats = count_eeg_file_formats(dataset_pth)
    dataset.ieeg_file_formats = count_ieeg_file_formats(dataset_pth)
    dataset.meg_file_formats = count_meg_file_formats(dataset_pth)
    dataset.nb_meeg_channels = get_number_meeg_channels(dataset_pth, datatypes)

    dataset.authors = get_authors(dataset_pth)
    dataset.license = get_license(dataset_pth)
    dataset.references_and_links = get_references_and_links(dataset_pth)

    dataset.bids_version = get_bids_version(dataset_pth)

    sidecars = read_sidecars(dataset_pth)
    dataset.institutions = get_institutions(dataset_pth, sidecars)
    dataset.field_strength = get_field_strength(sidecars)

    dataset.duration = get_duration(dataset_pth, datatypes, tasks, jobs=jobs)

    return dataset


def get_nb_subjects(pth: Path) -> int:
    return len(list_participants_in_dataset(pth))


def has_participant_tsv(pth: Path) -> tuple[bool, bool, list[str]]:
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
        duration, reason = _read_nifti_header(dataset_pth, filepath)
        if duration is None:
            # streaming from S3 can fail temporarily: try once more
            cc_log.debug(f"Retrying {filepath.relative_to(dataset_pth)}: {reason}")
            duration, reason = _read_nifti_header(dataset_pth, filepath)
        if duration is not None:
            return duration
        cc_log.error(f"Could not get duration for: {filepath.relative_to(dataset_pth)} ({reason})")
        return (0, np.nan)

    elif "vhdr" in filepath.suffix:
        info, n_samples = get_meeg_header(dataset_pth, filepath)
        if n_samples and info and info["sfreq"]:
            # same convention as for MRI: (number of samples, duration of a sample)
            return (n_samples, 1 / float(info["sfreq"]))

    return (0, np.nan)


def _read_nifti_header(dataset_pth: Path, filepath: Path) -> tuple[tuple[int, float] | None, str]:
    """Stream the beginning of a nifti file and read its number of volumes and TR.

    Returns
    -------
    ``(n_volumes, repetition_time)`` or ``None`` if the header could not be read,
    and the reason why it could not be read.
    """
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
        return (int(tmp[0]), float(tmp[1])), ""
    except (ValueError, IndexError):
        cc_log.debug(f"{head_stderr}\n{result.stderr}")
        # the error from datalad (could not stream the file) explains
        # the error from the header reader (nothing to read): report it first
        reason = _error_reason(head_stderr) or _error_reason(result.stderr) or "unknown error"
        # the file is already named in the error message: keep the reason short
        for redundant in [f" within {dataset_pth}", f" for {filepath.relative_to(dataset_pth)}"]:
            reason = reason.replace(redundant, "")
        return None, reason


def _error_reason(*outputs: str) -> str:
    """Find the line explaining why a datalad command failed.

    datalad also reports progress as "[INFO] ..." lines on stderr,
    so the last line is often not the error:
    prefer error lines, then any line that is not information.
    """
    lines = [line.strip() for output in outputs for line in output.splitlines() if line.strip()]
    is_error = re.compile(r"^\[ERROR\]|^(error|fatal):|\((error|impossible)\):", re.IGNORECASE)
    errors = [line for line in lines if is_error.search(line)]
    not_info = [
        line
        for line in lines
        if not line.startswith(("[INFO]", "|")) and not re.search(r"\((ok|notneeded)\):", line)
    ]
    for candidates in (errors, not_info, lines):
        if candidates:
            return candidates[-1].removeprefix("[ERROR]").strip()
    return ""


def _get_file(ds: api.Dataset, filepath: Path) -> None:
    """Get the content of a file without datalad printing its results."""
    ds.get(filepath, result_renderer="disabled")
    cc_log.debug(f"  got {filepath}")


def _annexed_file_size(filepath: Path) -> int | None:
    """Return the size of a file, even if its content is not downloaded.

    For files whose content is not present,
    the size is read from their git-annex key (``<backend>-s<size>--<hash>``).
    """
    if filepath.exists():
        return filepath.stat().st_size
    if filepath.is_symlink():
        if match := re.search(r"-s(\d+)--", os.readlink(filepath)):
            return int(match.group(1))
    return None


def _brainvision_n_samples(data_fname: Path, fmt: str, nchan: int) -> int | None:
    """Compute the number of samples of a binary BrainVision data file from its size."""
    size = _annexed_file_size(data_fname)
    if size is None or nchan == 0:
        return None
    return size // (_BRAINVISION_BYTES[fmt] * nchan)


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
                data_fname,
                fmt,
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
        if not n_samples and isinstance(fmt, str):
            # MNE only computes the number of samples when reading the data:
            # for binary data compute it from the size of the data file
            # (without downloading it)
            n_samples = _brainvision_n_samples(Path(data_fname), fmt, int(info["nchan"]))
        return info, n_samples or 0
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
) -> dict[str, RUNS_DURATION | dict[str, RUNS_DURATION]]:
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

    duration_all_datatypes: dict[str, RUNS_DURATION | dict[str, RUNS_DURATION]] = {}
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
) -> RUNS_DURATION:
    files = list(files)
    durations = get_scan_durations(dataset_pth, files, jobs=jobs)
    return [durations[x] for x in files]


def get_authors(dataset_pth: Path) -> list[str]:
    if not (dataset_pth / "dataset_description.json").exists():
        return []
    with open(dataset_pth / "dataset_description.json") as f:
        dataset_description = json.load(f)
        return dataset_description.get("Authors", [])


def get_bids_version(dataset_pth: Path) -> str:
    if not (dataset_pth / "dataset_description.json").exists():
        return "n/a"
    with open(dataset_pth / "dataset_description.json") as f:
        version = str(json.load(f).get("BIDSVersion", "")).strip()
    # some datasets use "v1.2.2"
    return version.lstrip("vV") or "n/a"


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


def read_sidecars(dataset_pth: Path) -> list[dict[str, Any]]:
    """Read the JSON files in the root folder and of the first subject.

    Assumes that first subject is representative of the dataset.
    """
    json_files = list(glob_files(dataset_pth, "*.json"))
    first_subject = list_participants_in_dataset(dataset_pth)[0]
    json_files.extend(list(glob_files(dataset_pth, f"{first_subject}/**/*.json")))

    sidecars = []
    ds = api.Dataset(dataset_pth)
    for json_file in json_files:
        if Path(json_file).name.startswith("."):
            continue

        cc_log.debug(f"  {json_file}")
        try:
            _get_file(ds, Path(json_file))
            with open(json_file) as f:
                json_dict = json.load(f)
        except (json.decoder.JSONDecodeError, UnicodeDecodeError):
            cc_log.warning(f"Could not parse: {json_file}", stacklevel=2)
            continue
        except FileNotFoundError:
            cc_log.warning(f"Could not find: {json_file}", stacklevel=2)
            continue
        except IncompleteResultsError:
            cc_log.warning(f"Could not get: {json_file}", stacklevel=2)
            continue
        if isinstance(json_dict, dict):
            sidecars.append(json_dict)
    return sidecars


def get_institutions(dataset_pth: Path, sidecars: list[dict[str, Any]] | None = None) -> list[str]:
    """List institutions in JSON files in root folder and first subject."""
    cc_log.info(" Getting institution")
    if sidecars is None:
        sidecars = read_sidecars(dataset_pth)
    institutions = [construct_institution_string(x).strip(", ") for x in sidecars]
    return sorted({x for x in institutions if x})


def get_field_strength(sidecars: list[dict[str, Any]]) -> list[float]:
    """List the unique MagneticFieldStrength (in Tesla) found in the JSON sidecars."""
    field_strengths = set()
    for sidecar in sidecars:
        value = sidecar.get("MagneticFieldStrength")
        if isinstance(value, str):
            # for example "3T"
            match = re.search(r"\d+(\.\d+)?", value)
            value = float(match.group()) if match else None
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            field_strengths.add(round(float(value), 2))
    return sorted(field_strengths)


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
    """Return the total size of the annexed files, for example "2.2 GB".

    Read from the summary line of ``datalad status --annex all``:
    "3235 annex'd files (0.0 B/54.0 GB present/total size)".
    """
    result = subprocess.run(
        [_datalad_executable(), "status", "-d", str(dataset_pth), "--annex", "all"],
        capture_output=True,
        text=True,
    )
    return parse_dataset_size(result.stdout)


def parse_dataset_size(status_output: str) -> str:
    """Parse the total size from the output of ``datalad status --annex all``.

    The output can also list modified or untracked files,
    so only the summary line is used.
    """
    if match := re.search(
        r"\(([0-9.]+ ?[KMGTP]?B)/([0-9.]+ ?[KMGTP]?B) present/total size\)", status_output
    ):
        return match.group(2)
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


def add_derivatives(dataset: BidsDataset, dataset_pth: Path, derivatives: list[str]) -> BidsDataset:
    """Update dataset with links to derivatives and their pipeline version if they exist."""
    dataset_name = dataset.name
    for der in ["fmriprep", "mriqc"]:
        if f"{dataset_name}-{der}" in derivatives:
            setattr(dataset, der, f"{URL_OPENNEURO_DERIVATIVES}{dataset_name}-{der}")
            description = _derivative_description(f"{dataset_name}-{der}")
            setattr(dataset, f"{der}_version", pipeline_version(description, der))

    for der in [
        "fmriprep",
        "freesurfer",
        "mriqc",
    ]:
        if getattr(dataset, der) is not None:
            continue
        if der_datasets := glob_files(dataset_pth, f"derivatives/*{der}*"):
            for i in der_datasets:
                setattr(
                    dataset, der, f"{URL_OPENNEURO}{dataset_name}/tree/main/derivatives/{i.name}"
                )
            description = _local_dataset_description(dataset_pth, i)
            setattr(dataset, f"{der}_version", pipeline_version(description, der))

    return dataset


def pipeline_version(description: dict[str, Any] | None, pipeline: str) -> str:
    """Return the version of the pipeline that generated a derivative dataset.

    Uses ``GeneratedBy`` (BIDS >= 1.4) or ``PipelineDescription`` (BIDS < 1.4)
    from its dataset_description.json.
    """
    if not description:
        return "n/a"
    generated_by = description.get("GeneratedBy") or []
    if isinstance(generated_by, dict):
        generated_by = [generated_by]
    if not isinstance(generated_by, list):
        generated_by = []
    if isinstance(description.get("PipelineDescription"), dict):
        generated_by.append(description["PipelineDescription"])
    generated_by = [x for x in generated_by if isinstance(x, dict) and x.get("Version")]
    # prefer the entry about the pipeline, if there are several
    matching = [x for x in generated_by if pipeline in str(x.get("Name", "")).lower()]
    for entry in matching or generated_by:
        return str(entry["Version"]).strip()
    return "n/a"


def _derivative_description(name: str) -> dict[str, Any] | None:
    """Read the dataset_description.json of an OpenNeuroDerivatives dataset.

    From the datalad superdataset if the dataset is installed there,
    otherwise from GitHub.
    """
    superdataset = derivatives_superdataset_dir()
    if superdataset is not None and (superdataset / name / ".git").exists():
        if description := _local_dataset_description(superdataset / name, superdataset / name):
            return description
    return _remote_dataset_description(
        f"{URL_RAW_OPENNEURO_DERIVATIVES}{name}/main/dataset_description.json"
    )


def _remote_dataset_description(url: str) -> dict[str, Any] | None:
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            description = response.json()
            return description if isinstance(description, dict) else None
        cc_log.warning(f"Could not get {url}: error {response.status_code}")
    except (requests.RequestException, ValueError) as e:
        cc_log.warning(f"Could not get {url}: {e!r}")
    return None


def _local_dataset_description(dataset_pth: Path, derivative_pth: Path) -> dict[str, Any] | None:
    description_file = derivative_pth / "dataset_description.json"
    try:
        _get_file(api.Dataset(dataset_pth), description_file)
        with open(description_file) as f:
            description = json.load(f)
            return description if isinstance(description, dict) else None
    except (OSError, json.decoder.JSONDecodeError, UnicodeDecodeError, IncompleteResultsError):
        cc_log.debug(f"Could not read {description_file}")
    return None


def count_sessions_tsv(dataset_pth: Path) -> int:
    return len(list(glob_files(dataset_pth, "sub-*/*sessions.tsv")))


def count_scans_tsv(dataset_pth: Path) -> int:
    return len(list(glob_files(dataset_pth, "sub-*/**/*scans.tsv")))


def count_physio_files(dataset_pth: Path) -> int:
    return len(list(glob_files(dataset_pth, "sub-*/**/*physio.tsv.gz")))


def update(
    debug: bool = True,
    jobs: int = 1,
    reindex: bool = False,
    source: str = "openneuro",
) -> None:
    """Update the listing of OpenNeuro datasets.

    Parameters
    ----------
    reindex : bool
        Index again all the datasets, not only those missing from the listing.
        Can be resumed if interrupted.

    source : "openneuro" | "non-openneuro"
        Which listing to update.
    """
    if source == "non-openneuro":
        update_non_openneuro(debug=debug, jobs=jobs, reindex=reindex)
        return
    if source != "openneuro":
        raise ValueError(f"Unknown source: {source}")

    if not os.getenv("CI"):
        # fail early if the superdatasets or the folder for the other datasets are not set
        superdataset_dir()
        derivatives_superdataset_dir()
        config_path("local_paths", "openneuro", OPENNEURO)
    install_missing_datasets(jobs=jobs, reindex=reindex)
    list_openneuro_derivatives()
    update_openneuro(debug=debug, jobs=jobs, reindex=reindex)


if __name__ == "__main__":
    update()
