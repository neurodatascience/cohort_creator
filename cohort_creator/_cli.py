"""Command line interface for cohort_creator."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

import pandas as pd

from cohort_creator._parsers import global_parser
from cohort_creator._utils import get_bids_filter
from cohort_creator._utils import get_list_datasets_to_install
from cohort_creator._utils import load_dataset_listing
from cohort_creator._utils import load_participant_listing
from cohort_creator._utils import validate_dataset_types
from cohort_creator.cohort_creator import construct_cohort
from cohort_creator.cohort_creator import get_data
from cohort_creator.cohort_creator import install_datasets
from cohort_creator.logger import cc_logger

cc_log = cc_logger()


def set_verbosity(verbosity: int | list[int]) -> None:
    if isinstance(verbosity, list):
        verbosity = verbosity[0]
    if verbosity == 0:
        cc_log.setLevel("ERROR")
    elif verbosity == 1:
        cc_log.setLevel("WARNING")
    elif verbosity == 2:
        cc_log.setLevel("INFO")
    elif verbosity == 3:
        cc_log.setLevel("DEBUG")

    logging.getLogger("datalad").setLevel(logging.WARNING)
    logging.getLogger("datalad.gitrepo").setLevel(logging.ERROR)


def _get_participant_listing_from_args(args: argparse.Namespace) -> pd.DataFrame | None:
    if args.participant_listing is None:
        return None
    participant_listing = Path(args.participant_listing[0]).resolve()
    return load_participant_listing(participant_listing=participant_listing)


def cli(argv: Sequence[str] = sys.argv) -> None:
    """Entry point."""
    parser = global_parser()

    args, _ = parser.parse_known_args(argv[1:])

    output_dir = Path(args.output_dir[0]).resolve()

    verbosity = args.verbosity
    set_verbosity(verbosity)

    dataset_types = args.dataset_types
    validate_dataset_types(dataset_types)

    participant_listing = _get_participant_listing_from_args(args)

    dataset_listing = Path(args.dataset_listing[0]).resolve()
    dataset_listing = load_dataset_listing(dataset_listing=dataset_listing)

    sourcedata_dir = output_dir / "sourcedata"
    sourcedata_dir.mkdir(exist_ok=True, parents=True)

    if args.command in ["install", "all"]:
        _execute_install(dataset_listing, args, sourcedata_dir)
    if args.command == "install":
        return None

    datatypes = args.datatypes
    space = args.space

    bids_filter = _return_bids_filter(args=args)

    if args.command in ["get", "all"]:
        jobs = args.jobs
        if isinstance(jobs, list):
            jobs = jobs[0]
        get_data(
            sourcedata=sourcedata_dir,
            datasets=dataset_listing,
            participants=participant_listing,
            dataset_types=dataset_types,
            datatypes=datatypes,
            space=space,
            jobs=jobs,
            bids_filter=bids_filter,
        )
    if args.command == "get":
        return None

    if args.command in ["copy", "all"]:
        skip_group_mriqc = bool(args.skip_group_mriqc)
        construct_cohort(
            output_dir=output_dir,
            sourcedata_dir=sourcedata_dir,
            datasets=dataset_listing,
            participants=participant_listing,
            dataset_types=dataset_types,
            datatypes=datatypes,
            space=space,
            bids_filter=bids_filter,
            skip_group_mriqc=skip_group_mriqc,
        )
        return None


def _execute_install(
    dataset_listing: pd.DataFrame, args: argparse.Namespace, sourcedata_dir: Path
) -> None:
    participant_listing = _get_participant_listing_from_args(args)
    datasets_to_install = get_list_datasets_to_install(
        dataset_listing=dataset_listing, participant_listing=participant_listing
    )
    generate_participant_listing = getattr(args, "generate_participant_listing", False)
    if participant_listing is None:
        generate_participant_listing = True
    install_datasets(
        datasets=datasets_to_install,
        sourcedata=sourcedata_dir,
        dataset_types=args.dataset_types,
        generate_participant_listing=generate_participant_listing,
    )


def _return_bids_filter(args: argparse.Namespace) -> dict[str, dict[str, dict[str, str]]] | None:
    if args.bids_filter_file is None:
        return None
    bids_filter_file = Path(args.bids_filter_file[0]).resolve()
    return (
        get_bids_filter(bids_filter_file=bids_filter_file) if bids_filter_file.exists() else None
    )
