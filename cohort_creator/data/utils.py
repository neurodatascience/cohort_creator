"""Utilities for data handling."""
from __future__ import annotations

import functools
from ast import literal_eval
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from rich import print

KNOWN_DATATYPES = [
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


@functools.lru_cache(maxsize=1)
def known_datasets_df() -> pd.DataFrame:
    openneuro_df = _load_known_datasets(_openneuro_listing_tsv())
    non_opnenneuro_df = _load_known_datasets(_non_openneuro_listing_tsv())
    return pd.concat([openneuro_df, non_opnenneuro_df])


def _openneuro_listing_tsv() -> Path:
    data_dir = Path(__file__).parent
    return data_dir / "openneuro.tsv"


def _non_openneuro_listing_tsv() -> Path:
    data_dir = Path(__file__).parent
    return data_dir / "non_openneuro.tsv"


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
            "duration": literal_eval,
            "references_and_links": pd.eval,
        },
        parse_dates=["created_on"],
    )

    return df


def is_known_dataset(dataset_name: str) -> bool:
    openneuro = known_datasets_df()
    mask = openneuro.name == dataset_name
    return mask.sum() != 0


# @functools.lru_cache(maxsize=3)
def wrangle_data(df: pd.DataFrame) -> pd.DataFrame:
    """Do general wrangling of the known datasets."""
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

    df["is_openneuro"] = df["raw"].apply(
        lambda x: bool(x.startswith("https://github.com/OpenNeuroDatasets"))
    )

    df["source"] = _get_source_study(df)

    # standardize size
    # convert to kilobytes
    for unit, exponent in zip(["TB", "GB", "MB", "KB"], [12, 9, 6, 3]):
        df["size"] = df["size"].apply(
            lambda x: float(x.split(" ")[0]) * 10**exponent
            if isinstance(x, str) and x.endswith(unit)
            else x
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
    print(
        f"\nMissing some duration for {df['missing_duration'].sum()} datasets ",
        f"({df['missing_duration'].sum() / len(df) * 100 :0.1f} %).",
    )
    for datatype in ["func", "ieeg", "eeg", "pet"]:
        mask = df[datatype]
        tmp_df = df[mask]
        print(
            f"Missing some duration for {tmp_df['missing_duration'].sum()} of {datatype} datasets ",
            f"({tmp_df['missing_duration'].sum() / len(tmp_df) * 100:0.1f} %).",
        )
    print()


def _detect_duplicate_datasets(df: pd.DataFrame) -> None:
    print("\nDuplicated datasets.")
    tmp = df.name.value_counts()
    print(tmp[tmp > 1])


def _get_source_study(df: pd.DataFrame) -> list[str]:
    source = []
    for row in df.iterrows():
        if row[1]["is_openneuro"]:
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


def filter_data(df: pd.Dataframe, config: Any = None) -> pd.DataFrame:
    ALL_TRUE = df["name"].apply(lambda x: bool(x))

    config = _check_config(config)

    mask_openneuro = ALL_TRUE
    if config["is_openneuro"] is not None:
        mask_openneuro = df["is_openneuro"] == config["is_openneuro"]

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
        mask_fmriprep = df["fmriprep"] == config["fmriprep"]

    mask_mriqc = ALL_TRUE
    if config["mriqc"] is not None:
        mask_mriqc = df["mriqc"] == config["mriqc"]

    mask_datatypes = df["datatypes"].apply(
        lambda x: len(set(x).intersection(config["datatypes"])) > 0
    )

    all_filters = pd.concat(
        (mask_openneuro, mask_task, mask_fmriprep, mask_mriqc, mask_physio, mask_datatypes), axis=1
    ).all(axis=1)

    return df[all_filters]


def _check_config(config: Any) -> dict[str, bool | str | list[str]]:
    DEFAULT_CONFIG: dict[str, bool | str | list[str] | None] = {
        "is_openneuro": None,
        "fmriprep": None,
        "mriqc": None,
        "physio": None,
        "task": "",
        "datatypes": KNOWN_DATATYPES,
    }
    if not config:
        config = DEFAULT_CONFIG

    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value

    if isinstance(config["datatypes"], bool):
        config["datatypes"] = KNOWN_DATATYPES
    if isinstance(config["datatypes"], str):
        config["datatypes"] = [config["datatypes"]]

    return config
