from __future__ import annotations

from pathlib import Path

import pandas as pd
from logger import cc_logger

cc_log = cc_logger()


def get_participant_ids(participants: pd.DataFrame, dataset_name: str) -> list[str] | None:
    mask = participants["DatasetName"] == dataset_name
    if mask.sum() == 0:
        cc_log.warning(f"  no participants in dataset {dataset_name}")
        return None
    participants_df = participants[mask]
    return participants_df["SubjectID"].tolist()


def list_files_for_subject(
    data_pth: Path, subject: str, session: str | None, data_type: str, glob_pattern: str
) -> list[str]:
    """Return a list of files for a participant with path relative to data_pth."""
    if not session:
        files = (data_pth / subject / data_type).glob(glob_pattern)
    else:
        files = (data_pth / subject / f"ses-{session}" / data_type).glob(glob_pattern)
    return [str(f.relative_to(data_pth)) for f in files]


def create_glob_pattern(dataset_type: str, suffix: str, ext: str, space: str | None = None) -> str:
    return f"*_{suffix}.{ext}" if dataset_type in {"raw", "mriqc"} else f"*{space}*_{suffix}.{ext}"


def dataset_path(root: Path, dataset_: str, derivative: str | None = None) -> Path:
    if derivative is None:
        return root / dataset_
    name = f"{dataset_}-{derivative}"
    return (root / dataset_).with_name(name)


def get_sessions(participants: pd.DataFrame, dataset_: str, participant: str) -> list[str | None]:
    mask = (participants["DatasetName"] == dataset_) & (participants["SubjectID"] == participant)
    sessions = participants[mask].SessionID.values
    if sessions[0] == "[]":
        return [None]
    else:
        return sessions[0].replace("[", "").replace("]", "").replace("'", "").split(", ")


def validate_dataset_types(dataset_types: list[str]) -> None:
    SUPPORTED_DATASET_TYPES = {"raw", "fmriprep", "mriqc", "freesurfer"}
    for dataset_type in dataset_types:
        if dataset_type not in SUPPORTED_DATASET_TYPES:
            raise ValueError(
                f"Dataset type '{dataset_type}' is not supported.\n"
                f"Supported types are '{SUPPORTED_DATASET_TYPES}'"
            )
