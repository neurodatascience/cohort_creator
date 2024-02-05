"""Command line interface for cohort_creator."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

import pandas as pd
from datalad import api
from rich_argparse import RichHelpFormatter

from cohort_creator._browse import browse
from cohort_creator._parsers import global_parser
from cohort_creator._utils import (
    get_bids_filter,
    get_list_datasets_to_install,
    load_dataset_listing,
    load_participant_listing,
    validate_dataset_types,
)
from cohort_creator.data._update import update
from cohort_creator.logger import cc_logger
from cohort_creator.main import construct_cohort, get_data, install_datasets

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

    if verbosity < 3:
        logging.getLogger("datalad").setLevel(logging.WARNING)
        logging.getLogger("datalad.gitrepo").setLevel(logging.ERROR)


def _get_participant_listing_from_args(args: argparse.Namespace) -> pd.DataFrame | None:
    if args.participant_listing is None:
        return None
    participant_listing = Path(args.participant_listing[0]).resolve()
    return load_participant_listing(participant_listing=participant_listing)


def create_yoda(output_dir: Path) -> None:
    if not output_dir.exists():
        api.create(path=output_dir, cfg_proc="yoda", result_renderer="disabled")
    if not (output_dir / ".datalad").exists():
        cc_log.info(f"Creating yoda dataset for output in: {output_dir}")
        api.create(path=output_dir, cfg_proc="yoda", force=True, result_renderer="disabled")


def cli(argv: Sequence[str] = sys.argv) -> None:
    """Entry point."""
    parser = global_parser(formatter_class=RichHelpFormatter)

    args, unknowns = parser.parse_known_args(argv[1:])
    if unknowns:
        cc_log.error(f"The following arguments are unknown: {unknowns}")
        exit(1)

    verbosity = args.verbosity
    set_verbosity(verbosity)

    if args.command in ["browse"]:
        debug = getattr(args, "debug", False)
        browse(debug=debug)
        exit(0)

    if args.command in ["update"]:
        debug = getattr(args, "debug", True)
        update(debug=debug)
        exit(0)

    output_dir = Path(args.output_dir[0]).resolve()

    dataset_types = args.dataset_types
    validate_dataset_types(dataset_types)

    participant_listing = _get_participant_listing_from_args(args)

    dataset_listing = load_dataset_listing(dataset_listing=args.dataset_listing)

    if args.command in ["install", "all"]:
        create_yoda(output_dir)
        (output_dir / "sourcedata").mkdir(exist_ok=True, parents=True)
        _execute_install(dataset_listing, args, output_dir)
    if args.command == "install":
        exit(0)

    datatypes = args.datatypes

    space = args.space
    if isinstance(space, list):
        # TODO handle case when several spaces are passed
        space = space[0]

    task = args.task
    if isinstance(task, list):
        # TODO handle case when several tasks are passed
        task = task[0]

    bids_filter = _return_bids_filter(args=args)

    if args.command in ["get", "all"]:
        jobs = args.jobs
        if isinstance(jobs, list):
            jobs = jobs[0]
        get_data(
            output_dir=output_dir,
            datasets=dataset_listing,
            participants=participant_listing,
            dataset_types=dataset_types,
            datatypes=datatypes,
            space=space,
            task=task,
            jobs=jobs,
            bids_filter=bids_filter,
        )
    if args.command == "get":
        exit(0)

    if args.command in ["copy", "all"]:
        skip_group_mriqc = bool(args.skip_group_mriqc)
        construct_cohort(
            output_dir=output_dir,
            datasets=dataset_listing,
            participants=participant_listing,
            dataset_types=dataset_types,
            datatypes=datatypes,
            task=task,
            space=space,
            bids_filter=bids_filter,
            skip_group_mriqc=skip_group_mriqc,
        )
        exit(0)


def _execute_install(
    dataset_listing: pd.DataFrame, args: argparse.Namespace, output_dir: Path
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
        output_dir=output_dir,
        dataset_types=args.dataset_types,
        generate_participant_listing=generate_participant_listing,
    )


def _return_bids_filter(args: argparse.Namespace) -> dict[str, dict[str, dict[str, str]]] | None:
    if args.bids_filter_file is None:
        return None
    bids_filter_file = Path(args.bids_filter_file[0]).resolve()
    return get_bids_filter(bids_filter_file=bids_filter_file) if bids_filter_file.exists() else None
