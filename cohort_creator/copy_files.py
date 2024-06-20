"""Module to handle copying data out of source datalad datasets."""

from __future__ import annotations

from pathlib import Path

from datalad import api

from cohort_creator._utils import (
    get_filters,
    list_all_files_with_filter,
    no_files_found_msg,
)
from cohort_creator.logger import cc_logger

cc_log = cc_logger()


def copy_top_files(src_pth: Path, target_pth: Path, datatypes: list[str]) -> None:
    """Copy top files from BIDS src_pth to BIDS target_pth."""
    top_files = ["dataset_description.json", "participants.*", "README*"]
    if "func" in datatypes:
        top_files.extend(["*task-*_events.tsv", "*task-*_events.json", "*task-*_bold.json"])
    if "anat" in datatypes:
        top_files.append("*T1w.json")

    for top_file_ in top_files:
        for f in src_pth.glob(top_file_):
            if (target_pth / f.name).exists():
                cc_log.debug(f"      file already present:\n       '{(target_pth / f.name)}'")
                continue
            try:
                api.copy_file(path=f, target_dir=target_pth)
            except FileNotFoundError:
                cc_log.error(f"      Could not find file '{f}'")


def copy_this_subject(
    subject: str,
    datatypes: list[str],
    dataset_type: str,
    src_pth: Path,
    target_pth: Path,
    space: str = "MNI152NLin2009cAsym",
    task: str = "*",
    sessions: list[str] | list[None] | None = None,
    bids_filter: None | dict[str, dict[str, dict[str, str]]] = None,
) -> None:
    if sessions is None:
        sessions = [None]
    for datatype_ in datatypes:
        filters = get_filters(
            dataset_type=dataset_type, datatype=datatype_, bids_filter=bids_filter
        )
        files = list_all_files_with_filter(
            data_pth=src_pth,
            dataset_type=dataset_type,
            filters=filters,
            subject=subject,
            sessions=sessions,
            datatype=datatype_,
            task=task,
            space=space,
        )
        if not files:
            cc_log.warning(no_files_found_msg(src_pth, subject, datatype_, filters))
            continue

        cc_log.debug(f"    {subject} - copying files:\n     {files}")

        dataset_root = src_pth
        if "derivatives" in str(dataset_root):
            dataset_root = Path(str(dataset_root).split("/derivatives")[0])

        for f in files:
            sub_dirs = Path(f).parents
            (target_pth / sub_dirs[0]).mkdir(exist_ok=True, parents=True)
            if (target_pth / f).exists():
                cc_log.debug(f"      file already present:\n       '{f}'")
                continue
            try:
                api.copy_file(path=dataset_root / f, target_dir=target_pth / sub_dirs[0])
            except FileNotFoundError:
                cc_log.error(f"      Could not find file '{f}' in {dataset_root}")
