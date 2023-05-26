"""Install a set of datalad datasets from openneuro and get the data for a set of participants.

Then copy the data to a new directory structure to create a "cohort".

"""
from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from datalad import api
from datalad.support.exceptions import (
    IncompleteResultsError,
)
from logger import cc_logger
from parsers import common_parser
from utils import create_glob_pattern
from utils import dataset_path
from utils import get_participant_ids
from utils import get_sessions
from utils import list_files_for_subject
from utils import validate_dataset_types

# from rich import print

# DATASET_LISTING_FILENAME = "datasets.tsv"  # "datasets_with_mriqc.tsv"  # "datasets.tsv"
# PARTICIPANT_LISTING_FILENAME = (
#     "participants.tsv"  # "participants_with_mriqc.tsv"  # "participants.tsv"
# )

DATA_TYPES = ["anat"]
TASKS = ["*"]  # TODO: implement filtering by task
SUFFIX = ["T1w"]
EXT = "nii.gz"
DATASET_TYPES = ["raw", "mriqc"]  # raw, mriqc, fmriprep, freesurfer
SPACE = "MNI152NLin2009cAsym"  # for fmriprep only

LOG_LEVEL = "INFO"

NB_JOBS = 6

cc_log = cc_logger()
cc_log.setLevel(LOG_LEVEL)

logging.getLogger("datalad").setLevel(logging.WARNING)


def install_datasets(datasets: pd.DataFrame, openneuro: pd.DataFrame, sourcedata: Path) -> None:
    cc_log.info("Installing datasets")

    for dataset_ in datasets["DatasetName"]:
        cc_log.info(dataset_)

        mask = openneuro.name == dataset_
        if mask.sum() == 0:
            cc_log.warning(f"  {dataset_} not found in openneuro")
            continue
        dataset_df = openneuro[mask]

        for dataset_type in DATASET_TYPES:
            derivative = None if dataset_type == "raw" else dataset_type

            data_pth = dataset_path(sourcedata, dataset_, derivative=derivative)

            if data_pth.exists():
                cc_log.info(f"  {dataset_type} data already present at {data_pth}")
            else:
                cc_log.info(f"  installing {dataset_type} data at: {data_pth}")
                if uri := dataset_df[dataset_type].values[0]:
                    api.install(path=data_pth, source=uri)


def get_data(datasets: pd.DataFrame, sourcedata: Path, participants: pd.DataFrame) -> None:
    cc_log.info("Getting data")

    for dataset_ in datasets["DatasetName"]:
        cc_log.info(dataset_)

        participants_ids = get_participant_ids(participants, dataset_)
        if not participants_ids:
            cc_log.warning(f"  no participants in dataset {dataset_}")
            continue

        cc_log.info(f"  getting data for: {participants_ids}")

        for dataset_type in DATASET_TYPES:
            cc_log.info(dataset_type)

            derivative = None if dataset_type == "raw" else dataset_type

            extension_list = ["json"] if dataset_type == "mriqc" else [EXT, "json"]

            data_pth = dataset_path(sourcedata, dataset_, derivative=derivative)

            dl_dataset = api.Dataset(data_pth)

            for subject in participants_ids:
                sessions = get_sessions(participants, dataset_, subject)
                get_data_this_subject(
                    subject=subject,
                    sessions=sessions,
                    data_type_list=DATA_TYPES,
                    suffix_list=SUFFIX,
                    extension_list=extension_list,
                    dataset_type=dataset_type,
                    data_pth=data_pth,
                    dl_dataset=dl_dataset,
                )


def get_data_this_subject(
    subject: str,
    sessions: list[str | None],
    data_type_list: list[str],
    suffix_list: list[str],
    extension_list: list[str],
    dataset_type: str,
    data_pth: Path,
    dl_dataset: api.Dataset,
) -> None:
    for session_ in sessions:
        for data_type in data_type_list:
            for suffix in suffix_list:
                for ext in extension_list:
                    glob_pattern = create_glob_pattern(
                        dataset_type, suffix=suffix, ext=ext, space=SPACE
                    )

                    # TODO handle session level
                    files = list_files_for_subject(
                        data_pth,
                        subject,
                        session=session_,
                        data_type=data_type,
                        glob_pattern=glob_pattern,
                    )
                    if not files:
                        cc_log.warning(
                            f"    no files found for: {subject} - {session_} - {data_type} - {suffix} - {ext}"
                        )
                        continue
                    cc_log.info(f"    {subject} - getting files:\n     {files}")
                    try:
                        dl_dataset.get(path=files, jobs=NB_JOBS)
                    except IncompleteResultsError:
                        cc_log.error(f"    {subject} - failed to get files:\n     {files}")


def construct_cohort(
    datasets: pd.DataFrame, ouput_dir: Path, sourcedata: Path, participants: pd.DataFrame
) -> None:
    cc_log.info("Constructing cohort")

    for dataset_ in datasets["DatasetName"]:
        cc_log.info(dataset_)

        for dataset_type in DATASET_TYPES:
            cc_log.info(dataset_type)

            derivative = None if dataset_type == "raw" else dataset_type

            extension_list = ["json"] if dataset_type == "mriqc" else [EXT, "json"]

            src_dir = dataset_path(sourcedata, dataset_, derivative=derivative)
            target_dir = dataset_path(ouput_dir, dataset_, derivative=derivative)

            target_dir.mkdir(exist_ok=True, parents=True)

            shutil.copy(
                src=(src_dir / "dataset_description.json"), dst=target_dir, follow_symlinks=True
            )

            participants_ids = get_participant_ids(participants, dataset_)
            if not participants_ids:
                cc_log.warning(f"  no participants in dataset {dataset_}")
                continue

            for subject in participants_ids:
                sessions = get_sessions(participants, dataset_, subject)
                copy_this_subject(
                    subject=subject,
                    sessions=sessions,
                    data_type_list=DATA_TYPES,
                    suffix_list=SUFFIX,
                    extension_list=extension_list,
                    dataset_type=dataset_type,
                    src_dir=src_dir,
                    target_dir=target_dir,
                )


def copy_this_subject(
    subject: str,
    sessions: list[str | None],
    data_type_list: list[str],
    suffix_list: list[str],
    extension_list: list[str],
    dataset_type: str,
    src_dir: Path,
    target_dir: Path,
) -> None:
    for session_ in sessions:
        for data_type in data_type_list:
            for suffix in suffix_list:
                for ext in extension_list:
                    glob_pattern = create_glob_pattern(
                        dataset_type, suffix=suffix, ext=ext, space=SPACE
                    )

                    files = list_files_for_subject(
                        data_pth=src_dir,
                        subject=subject,
                        session=session_,
                        data_type=data_type,
                        glob_pattern=glob_pattern,
                    )
                    if not files:
                        cc_log.warning(
                            f"    no files found for: {subject} - {session_} - {data_type} - {suffix} - {ext}"
                        )
                        continue

                    cc_log.info(f"    {subject} - copying files:\n     {files}")
                    for f in files:
                        sub_dirs = Path(f).parents
                        (target_dir / sub_dirs[0]).mkdir(exist_ok=True, parents=True)
                        if (target_dir / f).exists():
                            cc_log.info(f"      file '{f}' already present")
                            continue
                        try:
                            shutil.copy(src=src_dir / f, dst=target_dir / f, follow_symlinks=True)
                            # TODO deal with permission
                        except FileNotFoundError:
                            cc_log.error(f"      Could not find file '{f}'")


def main(argv: Any = sys.argv) -> None:
    parser = common_parser()

    args, unknowns = parser.parse_known_args(argv[1:])

    datasets_listing = Path(args.datasets_listing[0]).resolve()
    participants_listing = Path(args.participants_listing[0]).resolve()
    output_dir = Path(args.output_dir[0]).resolve()

    validate_dataset_types(DATASET_TYPES)

    root_dir = Path(__file__).parent
    data_dir = root_dir / "data"

    sourcedata = output_dir / "sourcedata"
    sourcedata.mkdir(exist_ok=True, parents=True)

    datasets = pd.read_csv(datasets_listing, sep="\t")
    participants = pd.read_csv(participants_listing, sep="\t")
    openneuro = pd.read_csv(data_dir / "openneuro_derivatives.tsv", sep="\t")

    install_datasets(datasets, openneuro, sourcedata)

    get_data(datasets, sourcedata, participants)

    construct_cohort(datasets, output_dir, sourcedata, participants)


if __name__ == "__main__":
    main()
