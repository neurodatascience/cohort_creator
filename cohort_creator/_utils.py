"""General utility functions for the cohort creator."""
from __future__ import annotations

import functools
import itertools
import shutil
from pathlib import Path

import pandas as pd

from .logger import cc_logger

cc_log = cc_logger()


def filter_excluded_participants(pth: Path, participants: list[str]) -> None:
    """Remove subjects from participants.tsv that were not included in the cohort."""
    participants_tsv = pth / "participants.tsv"
    if not (participants_tsv).exists():
        return
    participants_df = pd.read_csv(participants_tsv, sep="\t")
    participants_df = participants_df[participants_df["participant_id"].isin(participants)]
    participants_df.to_csv(participants_tsv, sep="\t", index=False)


def copy_top_files(src_dir: Path, target_dir: Path, datatypes: list[str]) -> None:
    """Copy top files from BIDS src_dir to BIDS target_dir."""
    top_files = ["dataset_description.json", "participants.*", "README*"]
    if "func" in datatypes:
        top_files.extend(["*task-*_events.tsv", "*task-*_events.json", "*task-*_bold.json"])
    if "anat" in datatypes:
        top_files.append("*T1w.json")
    for top_file_ in top_files:
        for f in src_dir.glob(top_file_):
            if (target_dir / f).exists():
                cc_log.info(f"      file '{f}' already present")
                continue
            try:
                shutil.copy(src=f, dst=target_dir, follow_symlinks=True)
            except FileNotFoundError:
                cc_log.error(f"      Could not find file '{f}'")


def check_tsv_content(tsv_file: Path) -> pd.DataFrame:
    df = pd.read_csv(tsv_file, sep="\t")
    if "DatasetName" not in df.columns:
        raise ValueError(f"Column 'DatasetName' not found in {tsv_file}")
    return df


def check_participant_listing(participants_listing: pd.DataFrame) -> None:
    for col in ["SessionID", "SubjectID"]:
        if "SubjectID" not in participants_listing.columns:
            raise ValueError(f"Column '{col}' not found in participants listing data.")


def get_participant_ids(participants: pd.DataFrame, dataset_name: str) -> list[str] | None:
    mask = participants["DatasetName"] == dataset_name
    if mask.sum() == 0:
        cc_log.warning(f"  no participants in dataset {dataset_name}")
        return None
    participants_df = participants[mask]
    return participants_df["SubjectID"].tolist()


def _is_dataset_in_openneuro(dataset_name: str) -> bool:
    openneuro = openneuro_df()
    mask = openneuro.name == dataset_name
    return mask.sum() != 0


def is_subject_in_dataset(subject: str, dataset_pth: Path) -> bool:
    return (dataset_pth / subject).exists()


def get_extensions(dataset_type: str, suffix: str) -> list[str]:
    if dataset_type == "mriqc":
        return ["json"]
    return ["tsv", "json"] if suffix == "events" else ["nii.gz", "nii", "json"]


def get_suffixes(datatype: str) -> list[str]:
    if datatype == "func":
        return ["events", "bold"]
    elif datatype == "anat":
        return ["T1w"]
    return ["*"]


def no_files_found_msg(
    subject: str,
    datatype: str,
) -> str:
    return f"""    no files found for:
     - subject: {subject}
     - datatype: {datatype}"""


@functools.lru_cache(maxsize=1)
def openneuro_df() -> pd.DataFrame:
    root_dir = Path(__file__).parent
    data_dir = root_dir / "data"
    return pd.read_csv(data_dir / "openneuro.tsv", sep="\t")


def list_all_files(
    data_pth: Path,
    dataset_type: str,
    subject: str,
    sessions: list[str] | list[None],
    datatype: str,
    space: str,
) -> list[str]:
    files: list[str] = []
    for session_, suffix in itertools.product(sessions, get_suffixes(datatype)):
        if not session_:
            datatype_pth = data_pth / subject / datatype
        else:
            datatype_pth = data_pth / subject / f"ses-{session_}" / datatype
        if not datatype_pth.exists():
            cc_log.warning(f"Path '{datatype_pth}' does not exist")
            continue

        for ext in get_extensions(dataset_type, suffix):
            glob_pattern = create_glob_pattern(dataset_type, suffix=suffix, ext=ext, space=space)
            tmp = datatype_pth.glob(glob_pattern)
            files.extend([str(f.relative_to(data_pth)) for f in tmp])

    return files


def create_glob_pattern(dataset_type: str, suffix: str, ext: str, space: str | None = None) -> str:
    return (
        f"*_{suffix}.{ext}"
        if dataset_type in {"raw", "mriqc"}
        else f"*{space}*preproc*_{suffix}.{ext}"
    )


def dataset_path(root: Path, dataset_: str, derivative: str | None = None) -> Path:
    if derivative is None:
        return root / dataset_
    name = f"{dataset_}-{derivative}"
    return (root / dataset_).with_name(name)


def get_sessions(
    participants: pd.DataFrame, dataset_: str, participant: str
) -> list[str] | list[None]:
    mask = (participants["DatasetName"] == dataset_) & (participants["SubjectID"] == participant)
    sessions = participants[mask].SessionID.values
    return listify(sessions[0])


def listify(some_str: str) -> list[str] | list[None]:
    """Return a list from a string literal `"['foo', 'bar']"`."""
    if some_str == "[]":
        return [None]
    else:
        return some_str.replace("[", "").replace("]", "").replace("'", "").split(", ")


def validate_dataset_types(dataset_types: list[str]) -> None:
    SUPPORTED_DATASET_TYPES = {"raw", "fmriprep", "mriqc"}
    for dataset_type in dataset_types:
        if dataset_type not in SUPPORTED_DATASET_TYPES:
            raise ValueError(
                f"Dataset type '{dataset_type}' is not supported.\n"
                f"Supported types are '{SUPPORTED_DATASET_TYPES}'"
            )
