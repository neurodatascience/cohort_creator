"""Load and save the listing of known BIDS datasets."""

from __future__ import annotations

import functools
import json
from math import isnan
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

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
    """Return dataframe of all datasets in the inventory.

    Returns
    -------
    pd.DataFrame
        Dataframe containing list of datasets known to the inventory.

    A data dictionary can be found in:
    ``bids_inventory/data/columns_description.json``
    """
    openneuro_df = _load_known_datasets(_openneuro_listing())
    non_opnenneuro_df = _load_known_datasets(_non_openneuro_listing())
    return pd.concat([openneuro_df, non_opnenneuro_df])


def _data_dir() -> Path:
    return Path(__file__).parent / "data"


def _openneuro_listing() -> Path:
    return _data_dir() / "openneuro.jsonl"


def _non_openneuro_listing() -> Path:
    return _data_dir() / "non_openneuro.jsonl"


def _skipped_datasets_file() -> Path:
    return _data_dir() / "skipped_datasets.csv"


def skipped_datasets() -> dict[str, str]:
    """Return the datasets that must not be indexed, with the reason why.

    For example datasets deleted from OpenNeuro but still mirrored on GitHub.
    """
    df = pd.read_csv(_skipped_datasets_file(), dtype=str, keep_default_na=False)
    return dict(zip(df["name"], df["reason"]))


def _load_known_datasets(listing: Path) -> pd.DataFrame:
    """Load a listing of datasets stored as JSON lines (one dataset per line)."""
    df = pd.read_json(listing, lines=True, dtype=False, convert_dates=False)
    df["created_on"] = pd.to_datetime(df["created_on"], utc=True)
    return df


def save_known_datasets(df: pd.DataFrame, output_file: Path) -> None:
    """Save a listing of datasets as JSON lines (one dataset per line, sorted by name).

    Missing values (``NaN``, ``None``, ``"n/a"``) are saved as ``null``
    and durations are saved in seconds.
    """
    df = df.copy()
    df["duration"] = df["duration"].apply(_convert_duration)
    # dates can come in different formats (from the listing or from git):
    # parse them one by one to avoid pandas guessing a single format
    df["created_on"] = df["created_on"].apply(
        lambda x: pd.to_datetime(x, utc=True, errors="coerce")
    )
    records = sorted(df.to_dict(orient="records"), key=lambda x: str(x["name"]))
    # write to a temporary file first so that an interrupted save
    # cannot leave a truncated listing behind
    tmp_file = output_file.with_name(f"{output_file.name}.tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        for record in records:
            record = {str(k): _to_json_value(v) for k, v in record.items()}
            f.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    tmp_file.replace(output_file)


def _to_json_value(value: Any) -> Any:
    """Convert a value to something that can be saved as JSON."""
    if isinstance(value, dict):
        return {str(k): _to_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_to_json_value(v) for v in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        value = value.item()
    if value is None or value is pd.NaT or value is pd.NA or value == "n/a":
        return None
    if isinstance(value, float) and isnan(value):
        return None
    return value


def _run_duration(run: Any) -> float | None:
    """Return the duration of a run in seconds.

    A run can already be a duration in seconds,
    or a pair ``(number of samples, duration of a sample)``
    (for example ``(number of volumes, repetition time)``).
    Returns ``None`` if the duration is unknown.
    """
    if run is None:
        return None
    if isinstance(run, (int, float)):
        duration = float(run)
    elif any(i is None or isnan(i) for i in run):
        return None
    else:
        duration = float(np.prod(run))
    # a duration of 0 means the duration could not be read
    return None if isnan(duration) or duration <= 0 else duration


def _convert_duration(
    durations: dict[str, Any],
) -> dict[str, list[float] | dict[str, list[float] | None]]:
    """Convert the duration of all runs to seconds.

    ``durations`` is either ``{datatype: [run, ...]}``
    or ``{datatype: {task: [run, ...]}}``.
    Runs with an unknown duration are dropped from the task lists
    and tasks without any known duration are set to ``None``.
    """
    if not isinstance(durations, dict) or not durations:
        return {}

    converted: dict[str, list[float] | dict[str, list[float] | None]] = {}
    for datatype, value in durations.items():
        if isinstance(value, list):
            converted[datatype] = [
                np.nan if (d := _run_duration(run)) is None else d for run in value
            ]
        elif isinstance(value, dict):
            converted[datatype] = {
                task: [d for run in runs or [] if (d := _run_duration(run)) is not None] or None
                for task, runs in value.items()
            }

    return converted


def is_known_dataset(dataset_name: str) -> bool:
    """Check if a dataset is in the inventory.

    Parameters
    ----------
    dataset_name : :obj:`str`
        Name of the dataset to check, for example ``ds000117``.
    """
    openneuro = known_datasets_df()
    mask = openneuro.name == dataset_name
    return mask.sum() != 0
