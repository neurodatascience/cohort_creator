"""General parser for the cohort_creator package."""
from __future__ import annotations

import argparse
from typing import IO

import rich

__version__ = "0.1.0"


class MuhParser(argparse.ArgumentParser):
    def _print_message(self, message: str, file: IO[str] | None = None) -> None:
        rich.print(message, file=file)


def common_parser() -> MuhParser:
    parser = MuhParser(
        description="Creates a cohort by grabbing specific subjects from opennneuro datasets.",
        epilog="""
        For a more readable version of this help section,
        see the online doc https://github.com/neurodatascience/cohort_creator
        """,
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{__version__}",
    )
    parser.add_argument(
        "datasets_listing",
        help="Path to TSV file containing the list of datasets to install.",
        nargs=1,
    )
    parser.add_argument(
        "participants_listing",
        help="Path to TSV file containing the list of participants to get.",
        nargs=1,
    )
    parser.add_argument(
        "output_dir",
        help="Fullpath to the directory where the output files will be stored.",
        nargs=1,
    )
    parser.add_argument(
        "--action",
        help="Action to perform.",
        choices=[
            "all",
            "install",
            "get",
            "copy",
        ],
        required=False,
        default="all",
        type=str,
        nargs=1,
    )
    parser.add_argument(
        "--dataset_types",
        help="""Dataset to install and get data from.""",
        choices=[
            "raw",
            "mriqc",
            "fmriprep",
        ],
        required=False,
        default=["raw"],
        type=str,
        nargs="+",
    )
    parser.add_argument(
        "--verbosity",
        help="""Verbosity level.""",
        required=False,
        choices=[0, 1, 2, 3],
        default=2,
        type=int,
        nargs=1,
    )
    parser.add_argument(
        "--task",
        help="""
        Tasks of the input data.
        """,
        required=False,
        type=str,
        nargs="+",
    )
    parser.add_argument(
        "--space",
        help="""
        Space of the input data.
        """,
        required=False,
        type=str,
        nargs="+",
    )
    parser.add_argument(
        "--jobs",
        help="""Number of jobs: passed to datalad to speed up getting files.""",
        required=False,
        default=6,
        type=int,
        nargs=1,
    )
    parser.add_argument(
        "--dry_run",
        help="""
        When set to ``true`` this will generate and save the SPM batches,
        but not actually run them.
        """,
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--bids_filter_file",
        help="""
        Fullpath to a JSON file describing custom BIDS input filters.
        """,
        required=False,
        type=str,
        nargs=1,
    )
    # parser.add_argument(
    #     "--skip_validation",
    #     help="""
    #     To skip BIDS dataset and BIDS stats model validation.
    #     """,
    #     action="store_true",
    #     default=False,
    # )

    return parser
