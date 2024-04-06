"""Module to handle copying data out of source datalad datasets."""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from cohort_creator.logger import cc_logger

# from datalad import api
# from datalad.support.exceptions import IncompleteResultsError


cc_log = cc_logger()


def copy_files(
    output_dir: Path,
    datasets: pd.DataFrame,
    participants: pd.DataFrame | None,
    dataset_types: list[str],
    datatypes: list[str],
    task: str,
    space: str,
    bids_filter: None | dict[str, dict[str, dict[str, str]]] = None,
):
    pass


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
                shutil.copy(src=f, dst=target_pth, follow_symlinks=True)
            except FileNotFoundError:
                cc_log.error(f"      Could not find file '{f}'")
