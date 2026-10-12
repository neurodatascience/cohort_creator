"""Convert the listings of datasets from TSV to JSON lines.

One-off migration script: the TSV listings stored lists and dicts
as python literals in strings that had to be parsed when loading.

While converting, this also:

- fixes task names in the durations that were corrupted
  when loading the TSV (``"nan"`` was replaced by ``"None"``,
  turning ``balloonanalogrisktask`` into ``ballooNonealogrisktask``),
- drops EEG / iEEG durations that were already converted to seconds:
  they were computed as ``n_samples * sampling_frequency``
  instead of ``n_samples / sampling_frequency``
  and are recomputed on the next update.
"""

from __future__ import annotations

import re
import sys
from ast import literal_eval
from pathlib import Path
from typing import Any

import pandas as pd

from cohort_creator.data.utils import _data_dir, save_known_datasets

NESTED_COLUMNS = [
    "participant_columns",
    "eeg_file_formats",
    "ieeg_file_formats",
    "meg_file_formats",
    "nb_meeg_channels",
    "datatypes",
    "sessions",
    "tasks",
    "authors",
    "institutions",
    "references_and_links",
]

BOOLEAN_COLUMNS = [
    "has_participant_tsv",
    "has_participant_json",
    "has_phenotype_dir",
    "has_stimuli_dir",
]


def parse_duration(value: str) -> dict[str, Any]:
    # numpy >= 2 serializes scalars as e.g. "np.float64(384.0)"
    value = re.sub(r"np\.float64\(([^)]*)\)", r"\1", value)
    durations: dict[str, Any] = literal_eval(re.sub(r"\bnan\b", "None", value))
    for datatype, per_task in durations.items():
        if not isinstance(per_task, dict):
            continue
        durations[datatype] = {task.replace("None", "nan"): runs for task, runs in per_task.items()}
        if datatype in ["eeg", "ieeg"]:
            for task, runs in durations[datatype].items():
                if runs and any(isinstance(run, float) for run in runs):
                    durations[datatype][task] = []
    return durations


def load_tsv(tsv_file: Path) -> pd.DataFrame:
    converters: dict[str, Any] = {col: literal_eval for col in NESTED_COLUMNS + BOOLEAN_COLUMNS}
    converters["duration"] = parse_duration
    return pd.read_csv(tsv_file, sep="\t", converters=converters)


def main(data_dir: Path) -> None:
    for name in ["openneuro", "non_openneuro"]:
        tsv_file = data_dir / f"{name}.tsv"
        output_file = data_dir / f"{name}.jsonl"
        save_known_datasets(load_tsv(tsv_file), output_file)
        print(f"{tsv_file} -> {output_file}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else _data_dir())
