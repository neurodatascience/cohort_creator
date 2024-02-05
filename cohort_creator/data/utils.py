"""Utilities for data handling."""

from __future__ import annotations

import functools
from ast import literal_eval
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from cohort_creator.logger import cc_logger

cc_log = cc_logger()

KNOWN_DATATYPES = sorted(
    [
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
)


@functools.lru_cache(maxsize=1)
def known_datasets_df() -> pd.DataFrame:
    """Return dataframe of all datasets known to the cohort creator.

    Returns
    -------
    pd.DataFrame
        Dataframe containing list of datasets known to the cohort creator.

    A data dictionary can be found in:
    ``cohort_creator/data/columns_description.json``
    """
    openneuro_df = _load_known_datasets(_openneuro_listing_tsv())
    non_opnenneuro_df = _load_known_datasets(_non_openneuro_listing_tsv())
    return pd.concat([openneuro_df, non_opnenneuro_df])


def _data_dir() -> Path:
    return Path(__file__).parent


def _openneuro_listing_tsv() -> Path:
    return _data_dir() / "openneuro.tsv"


def _non_openneuro_listing_tsv() -> Path:
    return _data_dir() / "non_openneuro.tsv"


def _load_known_datasets(tsv_file: Path) -> pd.DataFrame:
    df = pd.read_csv(
        tsv_file,
        sep="\t",
        converters={
            "has_participant_tsv": pd.eval,
            "has_participant_json": pd.eval,
            "participant_columns": pd.eval,
            "has_phenotype_dir": pd.eval,
            "datatypes": pd.eval,
            "sessions": pd.eval,
            "tasks": pd.eval,
            "authors": pd.eval,
            "institutions": pd.eval,
            "has_stimuli_dir": pd.eval,
            "eeg_file_formats": literal_eval,
            "ieeg_file_formats": literal_eval,
            "meg_file_formats": literal_eval,
            "references_and_links": pd.eval,
        },
        parse_dates=["created_on"],
    )

    df["duration"] = df["duration"].apply(_convert_duration)

    return df


def _convert_duration(
    x: str,
) -> dict[str, Iterable[tuple[int, float]] | dict[str, Iterable[tuple[int, float]]]]:
    x = literal_eval(x.replace("nan", "None"))
    for datatype, value in x.items():
        if isinstance(value, list):
            value = [np.nan if None in run else np.prod(run) for run in value]
            x[datatype] = value

        if isinstance(value, dict):
            for task, runs in value.items():
                runs = [np.nan if None in run else np.prod(run) for run in runs]
                x[datatype][task] = runs

    return x


def is_known_dataset(dataset_name: str) -> bool:
    """Check if a dataset is known to the cohort creator.

    Parameters
    ----------
    dataset_name : :obj:`str`
        Name of the dataset to check, for example ``ds000117``.
    """
    openneuro = known_datasets_df()
    mask = openneuro.name == dataset_name
    return mask.sum() != 0


def wrangle_data(df: pd.DataFrame) -> pd.DataFrame:
    """Do general wrangling of the known datasets.

    Parameters
    ----------
    df : pd.DataFrame
        dataframe of known datasets

    Returns
    -------
    df : pd.DataFrame
        dataframe of known datasets with extra columns

    - ``nb_datatypes``: :obj:`int` Number of unique BIDS supported datatypes in the dataset.
    - ``nb_sessions``: :obj:`int` Total number of unique sessions in the dataset.
    - ``nb_authors``: :obj:`int` Number of authors as reported in the description of the dataset.
    - ``nb_tasks``: :obj:`int` Total number of unique tasks in the dataset.
    - ``useful_participants_tsv``: :obj:`bool`
    - ``has_physio``: :obj:`bool` ``True`` if the dataset contains any ``*_physio.tsv.gz`` files.
    - ``has_fmriprep``: :obj:`bool`` ``True`` if the dataset has knwow fmriprep preprocessed derivatives.
    - ``has_freesurfer``: :obj:`bool` ``True`` if the dataset has knwow freesurfer preprocessed derivatives.
    - ``has_mriqc``: :obj:`bool` ``True`` if the dataset has knwow mriqc derivatives.
    - ``source``: Specifies the source of the dataset.
    - ``mean_size``: size per subject in kilobytes
    - datatype: one column for each BIDS known datatype with ``True`` if this dataset contains that datatype.
    - ``total_duration``: Total "scanned" duration per participant (combines runs from: ``func``, ``eeg``, ``ieeg``)
    """
    _detect_duplicate_datasets(df)

    df["nb_sessions"] = df["sessions"].apply(lambda x: max(len(x), 1))

    df["nb_datatypes"] = df["datatypes"].apply(lambda x: len(x))

    # if only one column we assume it is only a participant_id file
    useful_participants_tsv = [(len(row[1]["participant_columns"]) > 1) for row in df.iterrows()]
    df["useful_participants_tsv"] = useful_participants_tsv

    # set non empty fmriprep / freesurfer / mriqc to true
    for der in [
        "fmriprep",
        "freesurfer",
        "mriqc",
    ]:
        df[der].fillna(False, inplace=True)
        df[f"has_{der}"] = df[der].apply(lambda x: bool(x))

    df["nb_tasks"] = df["tasks"].apply(lambda x: len(x))

    df["source"] = _get_source_study(df)

    # standardize size
    # convert to kilobytes
    for unit, exponent in zip(["TB", "GB", "MB", "KB"], [12, 9, 6, 3]):
        df["size"] = df["size"].apply(
            lambda x: (
                float(x.split(" ")[0]) * 10**exponent
                if isinstance(x, str) and x.endswith(unit)
                else x
            )
        )
    df["mean_size"] = df["size"] / df["nb_subjects"]

    for datatype in KNOWN_DATATYPES:
        df[datatype] = df["datatypes"].apply(lambda x: datatype in x)

    _detect_missing_duration(df)

    df["nb_authors"] = df["authors"].apply(lambda x: len(x))

    df["has_physio"] = df["nb_physio_files"] > 0

    df["total_duration"] = df.apply(_compute_total_duration, axis=1)

    # new_cols = {
    #     "author_male": [],
    #     "author_female": [],
    #     "author_andy": [],
    #     "author_unknown": [],
    #     "author_mostly_male": [],
    #     "author_mostly_female": [],
    # }
    # for row in df.iterrows():
    #     if len(row[1]["authors"]) == 0:
    #         for key in new_cols:
    #             new_cols[key].append(np.nan)
    #     else:
    #         print(row[1]["name"])
    #         results = {
    #             "male": 0,
    #             "female": 0,
    #             "andy": 0,
    #             "unknown": 0,
    #             "mostly_male": 0,
    #             "mostly_female": 0,
    #         }
    #         total = 0
    #         for author in row[1]["authors"]:
    #             d = gender.Detector()
    #             #  TODO assuming the surname comes first
    #             guess = d.get_gender(author.replace(", ", " ").split(" ")[0])
    #             # print(f"{author}: {guess}")
    #             results[guess] += 1
    #             total += 1
    #         for key in results:
    #             new_cols[f"author_{key}"].append(results[key] / total)

    return df


def _missing_duration(row: pd.Series) -> None | bool:
    if not set(row["datatypes"]).intersection(
        ("pet", "eeg", "ieeg", "meg", "motion", "nirs", "func")
    ):
        return None
    for _, value in row["duration"].items():
        if isinstance(value, list) and len(value) == 0:
            return True
        if isinstance(value, dict):
            for _, tmp in value.items():
                if len(tmp) == 0:
                    return True
    return False


def _compute_total_duration(row: pd.Series) -> float:
    duration = []
    for _, value in row["duration"].items():
        if isinstance(value, list):
            duration.extend(value)
        if isinstance(value, dict):
            for _, tmp in value.items():
                duration.extend(tmp)
    return np.cumsum(duration)[-1] / 3600 if duration else np.nan


def _detect_missing_duration(df: pd.DataFrame) -> None:
    df["missing_duration"] = df.apply(_missing_duration, axis=1)
    cc_log.debug(
        f"\nMissing some duration for {df['missing_duration'].sum()} datasets "
        f"({df['missing_duration'].sum() / len(df) * 100 :0.1f} %)."
    )
    for datatype in ["func", "ieeg", "eeg", "pet"]:
        mask = df[datatype]
        tmp_df = df[mask]
        cc_log.debug(
            f"Missing some duration for {tmp_df['missing_duration'].sum()} of {datatype} datasets "
            f"({tmp_df['missing_duration'].sum() / len(tmp_df) * 100:0.1f} %)."
        )


def _detect_duplicate_datasets(df: pd.DataFrame) -> None:
    cc_log.debug("\nDuplicated datasets.")
    tmp = df.name.value_counts()
    cc_log.debug(tmp[tmp > 1])


def _get_source_study(df: pd.DataFrame) -> list[str]:
    source = []
    for row in df.iterrows():
        if row[1]["name"].startswith("ds"):
            source.append("openneuro")
        elif row[1]["name"].startswith("ABIDE2"):
            source.append("abide 2")
        elif row[1]["name"].startswith("ABIDE"):
            source.append("abide")
        elif row[1]["name"].startswith("ADHD200"):
            source.append("adhd200")
        elif row[1]["name"].startswith("CORR"):
            source.append("corr")
        elif row[1]["name"].startswith("CNEUROMOD"):
            source.append("neuromod")
    return source


DEFAULT_CONFIG: dict[str, bool | str | list[str] | None] = {
    "fmriprep": None,
    "mriqc": None,
    "physio": None,
    "participants": None,
    "task": "",
    "datatypes": KNOWN_DATATYPES,
    "datatypes_and_or": "OR",
    "sources": None,
    "sources_and_or": "OR",
}


def filter_data(df: pd.Dataframe, config: Any = None) -> pd.DataFrame:
    """Filter the listing of datasets based on some configuration.

    Parameters
    ----------
    df : pd.Dataframe
        Listing of datasets to filter.
    config : Any, default=None
        Should be a :obj:`dict` with any of the following keys.

    - ``"fmriprep"`` : None | bool
    - ``"mriqc"`` : None | bool
    - ``"physio"`` : None | bool
    - ``"task"``: str
    - ``"datatypes"`` : list[str] of any of the BIDS datatypes
    - ``"datatypes_and_or"`` : "OR" | "AND" if any or all of the datatypes must be present
    - ``"sources"`` : list[str] source of the dataset (openneuro, abide...)
    - ``"sources_and_or"`` : "OR" | "AND" if any or all of the sources must be present

    If ``None`` is passed will default to the DEFAULT_CONFIG.

    Returns
    -------
    pd.DataFrame
        Filtered listing of datasets.
    """
    ALL_TRUE = df["name"].apply(lambda x: bool(x))

    config = _check_config(config)

    mask_sources = ALL_TRUE
    if config["sources"] is not None:
        mask_sources = df["source"].apply(lambda x: len({x}.intersection(config["sources"])) > 0)
        if config["sources_and_or"] == "AND":
            mask_sources = df["source"].apply(
                lambda x: len({x}.intersection(config["sources"])) == len(config["sources"])
            )

    # better filtering should make sure
    # that the one of the requested datatypes has the task of interest
    mask_task = ALL_TRUE
    if config["task"] != "":
        mask_task = df["tasks"].apply(lambda x: config["task"] in "".join(x).lower())

    mask_physio = ALL_TRUE
    if config["physio"] is not None:
        mask_physio = df["has_physio"] == config["physio"]

    mask_fmriprep = ALL_TRUE
    if config["fmriprep"] is not None:
        mask_fmriprep = df["has_fmriprep"] == config["fmriprep"]

    mask_mriqc = ALL_TRUE
    if config["mriqc"] is not None:
        mask_mriqc = df["has_mriqc"] == config["mriqc"]

    mask_participants = ALL_TRUE
    if config["participants"] is not None:
        mask_participants = df["useful_participants_tsv"] == config["participants"]

    mask_datatypes = df["datatypes"].apply(
        lambda x: len(set(x).intersection(config["datatypes"])) > 0
    )
    if config["datatypes_and_or"] == "AND":
        mask_datatypes = df["datatypes"].apply(
            lambda x: len(set(x).intersection(config["datatypes"])) == len(config["datatypes"])
        )

    all_filters = pd.concat(
        (
            mask_task,
            mask_physio,
            mask_fmriprep,
            mask_mriqc,
            mask_participants,
            mask_datatypes,
            mask_sources,
        ),
        axis=1,
    ).all(axis=1)

    filtered_df = df[all_filters]

    return filtered_df


def _check_config(config: None | dict[Any, Any]) -> dict[str, bool | str | list[str]]:
    if not config:
        config = DEFAULT_CONFIG

    if not isinstance(config, dict):
        raise (TypeError, "config must be a dictionary or None.")

    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value

    for key, value in config.items():
        config[key] = booleanify(value)

    if isinstance(config["datatypes"], bool):
        config["datatypes"] = KNOWN_DATATYPES
    if isinstance(config["datatypes"], str):
        config["datatypes"] = [config["datatypes"]]

    if isinstance(config["sources"], str):
        config["sources"] = [config["sources"]]

    return config


def booleanify(value: bool | str | list[str] | None) -> bool | str | list[str] | None:
    if value == "both":
        return None
    elif value == "true":
        return True
    elif value == "false":
        return False
    return value


def save_dataset_listing(df: pd.DataFrame) -> None:
    df["DatasetID"] = df["name"].copy()
    df = df.rename(
        columns={
            "nb_subjects": "NumMatchingSubjects",
            "datatypes": "AvailableImageModalites",
            "raw": "PortalURI",
            "name": "DatasetName",
        }
    )
    output_df = df[
        [
            "DatasetID",
            "PortalURI",
            "NumMatchingSubjects",
            "AvailableImageModalites",
            "sessions",
            "tasks",
            "fmriprep",
            "mriqc",
        ]
    ].copy()

    output_file = Path.cwd() / "datasets_results.tsv"
    output_df.to_csv(output_file, sep="\t", index=False)
    cc_log.info(f"Dataset listing saved to: {output_file}")


def _count_extensions(df: pd.DataFrame, datatype: str) -> pd.DataFrame:
    if datatype == "eeg":
        file_formats = {"bdf": 0, "edf": 0, "eeg": 0, "set": 0}
    elif datatype == "ieeg":
        file_formats = {"nwb": 0, "edf": 0, "eeg": 0, "set": 0, "mefd": 0}
    elif datatype == "meg":
        file_formats = {".ds": 0, "": 0, ".fif": 0, ".con": 0, ".kdf": 0, ".raw.mhd": 0}

    datatype_df = df[df[datatype]]

    for row in datatype_df.iterrows():
        for key, value in row[1][f"{datatype}_file_formats"].items():
            if value > 0:
                file_formats[key] += 1

    for key, value in file_formats.items():
        file_formats[key] = value / len(datatype_df) * 100

    data: dict[str, list[str | float]] = {"extension": [], "count": []}
    for key, value in file_formats.items():
        data["extension"].append(key)
        data["count"].append(value)

    return pd.DataFrame(data)
