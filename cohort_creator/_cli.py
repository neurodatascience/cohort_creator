"""Command line interface for cohort_creator."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Sequence

from rich_argparse import RichHelpFormatter

from cohort_creator._parsers import global_parser
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

    if verbosity < 3:
        logging.getLogger("datalad").setLevel(logging.WARNING)
        logging.getLogger("datalad.gitrepo").setLevel(logging.ERROR)


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
        from cohort_creator._browse import browse

        debug = getattr(args, "debug", False)
        browse(debug=debug)
        exit(0)

    if args.command in ["update"]:
        from cohort_creator.data._update import update

        debug = getattr(args, "debug", True)
        update(debug=debug)
        exit(0)

    from cohort_creator._run import _get_participant_listing_from_args
    from cohort_creator._utils import load_dataset_listing, validate_dataset_types

    output_dir = Path(args.output_dir[0]).resolve()

    dataset_types = args.dataset_types
    validate_dataset_types(dataset_types)

    participant_listing = _get_participant_listing_from_args(args)

    dataset_listing = load_dataset_listing(dataset_listing=args.dataset_listing)

    if args.command in ["install", "all"]:
        from cohort_creator._run import _execute_install, create_yoda

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

    from cohort_creator._run import _return_bids_filter

    bids_filter = _return_bids_filter(args=args)

    if args.command in ["get", "all"]:
        from cohort_creator.main import get_data

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
        from cohort_creator.main import construct_cohort

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


# if __name__ == "__main__":
#     cli(['cohort_creator', '--help'])
