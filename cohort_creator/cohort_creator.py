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

from cohort_creator.logger import cc_logger
from cohort_creator.parsers import common_parser
from cohort_creator.utils import _is_dataset_in_openneuro
from cohort_creator.utils import check_tsv_content
from cohort_creator.utils import chek_participant_listing
from cohort_creator.utils import copy_top_files
from cohort_creator.utils import dataset_path
from cohort_creator.utils import filter_excluded_participants
from cohort_creator.utils import get_participant_ids
from cohort_creator.utils import get_sessions
from cohort_creator.utils import is_subject_in_dataset
from cohort_creator.utils import list_all_files
from cohort_creator.utils import no_files_found_msg
from cohort_creator.utils import openneuro_derivatives_df
from cohort_creator.utils import validate_dataset_types


cc_log = cc_logger()

logging.getLogger("datalad").setLevel(logging.WARNING)


def install_datasets(datasets: list[str], sourcedata: Path, dataset_types: list[str]) -> None:
    cc_log.info("Installing datasets")
    for dataset_ in datasets:
        cc_log.info(f" {dataset_}")
        install(dataset_name=dataset_, dataset_types=dataset_types, output_path=sourcedata)


def install(dataset_name: str, dataset_types: list[str], output_path: Path) -> None:
    if not _is_dataset_in_openneuro(dataset_name):
        cc_log.warning(f"  {dataset_name} not found in openneuro")
        return None

    openneuro = openneuro_derivatives_df()
    mask = openneuro.name == dataset_name
    dataset_df = openneuro[mask]

    for dataset_type_ in dataset_types:
        derivative = None if dataset_type_ == "raw" else dataset_type_

        data_pth = dataset_path(output_path, dataset_name, derivative=derivative)

        if data_pth.exists():
            cc_log.info(f"  {dataset_type_} data already present at {data_pth}")
        else:
            cc_log.info(f"    installing {dataset_type_} data at: {data_pth}")
            if uri := dataset_df[dataset_type_].values[0]:
                api.install(path=data_pth, source=uri)


def get_data(
    datasets: pd.DataFrame,
    sourcedata: Path,
    participants: pd.DataFrame,
    dataset_types: list[str],
    datatypes: list[str],
    space: str,
    jobs: int,
) -> None:
    cc_log.info("Getting data")

    if isinstance(datatypes, str):
        datatypes = [datatypes]

    for dataset_ in datasets["DatasetName"]:
        cc_log.info(f" {dataset_}")

        participants_ids = get_participant_ids(participants, dataset_)
        if not participants_ids:
            cc_log.warning(f"  no participants in dataset {dataset_}")
            continue

        cc_log.info(f"  getting data for: {participants_ids}")

        for dataset_type_ in dataset_types:
            cc_log.info(f"  {dataset_type_}")

            derivative = None if dataset_type_ == "raw" else dataset_type_

            data_pth = dataset_path(sourcedata, dataset_, derivative=derivative)

            dl_dataset = api.Dataset(data_pth)

            for subject in participants_ids:
                if not is_subject_in_dataset(subject, data_pth):
                    cc_log.warning(f"  no participant {subject} in dataset {dataset_}")
                    continue
                sessions = get_sessions(participants, dataset_, subject)
                get_data_this_subject(
                    subject=subject,
                    sessions=sessions,
                    datatypes=datatypes,
                    space=space,
                    dataset_type=dataset_type_,
                    data_pth=data_pth,
                    dl_dataset=dl_dataset,
                    jobs=jobs,
                )


def get_data_this_subject(
    subject: str,
    sessions: list[str | None],
    datatypes: list[str],
    space: str,
    dataset_type: str,
    data_pth: Path,
    dl_dataset: api.Dataset,
    jobs: int,
) -> None:
    for datatype_ in datatypes:
        files = list_all_files(
            data_pth=data_pth,
            dataset_type=dataset_type,
            subject=subject,
            sessions=sessions,
            datatype=datatype_,
            space=space,
        )
        if not files:
            cc_log.warning(no_files_found_msg(subject, datatype_))
            continue
        cc_log.info(f"    {subject} - getting files:\n     {files}")
        try:
            dl_dataset.get(path=files, jobs=jobs)
        except IncompleteResultsError:
            cc_log.error(f"    {subject} - failed to get files:\n     {files}")


def construct_cohort(
    datasets: pd.DataFrame,
    output_dir: Path,
    sourcedata_dir: Path,
    participants: pd.DataFrame,
    dataset_types: list[str],
    datatypes: list[str],
    space: str,
) -> None:
    cc_log.info("Constructing cohort")

    for dataset_ in datasets["DatasetName"]:
        cc_log.info(f" {dataset_}")

        participants_ids = get_participant_ids(participants, dataset_)
        if not participants_ids:
            cc_log.warning(f"  no participants in dataset {dataset_}")
            continue

        cc_log.info(f"  creating cohort with: {participants_ids}")

        for dataset_type_ in dataset_types:
            cc_log.info(f"  {dataset_type_}")

            derivative = None if dataset_type_ == "raw" else dataset_type_

            src_dir = dataset_path(sourcedata_dir, dataset_, derivative=derivative)
            target_dir = dataset_path(output_dir, dataset_, derivative=derivative)

            target_dir.mkdir(exist_ok=True, parents=True)

            copy_top_files(src_dir=src_dir, target_dir=target_dir, datatypes=datatypes)
            filter_excluded_participants(pth=target_dir, participants=participants_ids)

            for subject in participants_ids:
                if not is_subject_in_dataset(subject, src_dir):
                    cc_log.warning(f"  no participant {subject} in dataset {dataset_}")
                    continue
                sessions = get_sessions(participants, dataset_, subject)
                copy_this_subject(
                    subject=subject,
                    sessions=sessions,
                    datatypes=datatypes,
                    dataset_type=dataset_type_,
                    space=space,
                    src_dir=src_dir,
                    target_dir=target_dir,
                )


def copy_this_subject(
    subject: str,
    sessions: list[str | None],
    datatypes: list[str],
    dataset_type: str,
    space: str,
    src_dir: Path,
    target_dir: Path,
) -> None:
    for datatype_ in datatypes:
        files = list_all_files(
            data_pth=src_dir,
            dataset_type=dataset_type,
            subject=subject,
            sessions=sessions,
            datatype=datatype_,
            space=space,
        )
        if not files:
            cc_log.warning(no_files_found_msg(subject, datatype_))
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


def cli(argv: Any = sys.argv) -> None:
    """Entry point."""
    parser = common_parser()

    args, unknowns = parser.parse_known_args(argv[1:])

    datasets_listing = Path(args.datasets_listing[0]).resolve()
    participants_listing = Path(args.participants_listing[0]).resolve()
    output_dir = Path(args.output_dir[0]).resolve()
    action = args.action[0]
    datatypes = args.datatypes
    space = args.space

    jobs = args.jobs
    if isinstance(jobs, list):
        jobs = jobs[0]

    dataset_types = args.dataset_types
    validate_dataset_types(dataset_types)

    verbosity = args.verbosity
    if isinstance(verbosity, list):
        verbosity = verbosity[0]

    main(
        datasets_listing=datasets_listing,
        participants_listing=participants_listing,
        output_dir=output_dir,
        action=action,
        dataset_types=dataset_types,
        datatypes=datatypes,
        space=space,
        verbosity=verbosity,
        jobs=jobs,
    )


def main(
    datasets_listing: Path,
    participants_listing: Path,
    output_dir: Path,
    action: str,
    dataset_types: list[str],
    datatypes: list[str],
    space: str,
    verbosity: int,
    jobs: int,
) -> None:
    sourcedata_dir = output_dir / "sourcedata"
    sourcedata_dir.mkdir(exist_ok=True, parents=True)

    datasets = check_tsv_content(datasets_listing)

    participants = check_tsv_content(participants_listing)
    chek_participant_listing(participants_listing)

    datasets_to_install = participants["DatasetName"].unique()

    if verbosity == 0:
        cc_log.setLevel("ERROR")
    elif verbosity == 1:
        cc_log.setLevel("WARNING")
    elif verbosity == 2:
        cc_log.setLevel("INFO")
    elif verbosity == 3:
        cc_log.setLevel("DEBUG")

    if action in ["install", "all"]:
        install_datasets(
            datasets=datasets_to_install,
            sourcedata=sourcedata_dir,
            dataset_types=dataset_types,
        )

    if action in ["get", "all"]:
        get_data(
            datasets=datasets,
            sourcedata=sourcedata_dir,
            participants=participants,
            dataset_types=dataset_types,
            datatypes=datatypes,
            space=space,
            jobs=jobs,
        )

    if action in ["copy", "all"]:
        construct_cohort(
            datasets=datasets,
            output_dir=output_dir,
            sourcedata_dir=sourcedata_dir,
            participants=participants,
            dataset_types=dataset_types,
            datatypes=datatypes,
            space=space,
        )
