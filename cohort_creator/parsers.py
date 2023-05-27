"""General parser for the cohort_creator package."""
from __future__ import annotations

import argparse
from typing import IO

import rich

from ._version import __version__


class _MuhParser(argparse.ArgumentParser):
    def _print_message(self, message: str, file: IO[str] | None = None) -> None:
        rich.print(message, file=file)


def common_parser() -> _MuhParser:
    parser = _MuhParser(
        description="Creates a cohort by grabbing specific subjects from opennneuro datasets.",
        epilog="""
        For a more readable version of this help section,
        see the online doc https://cohort-creator.readthedocs.io/en/latest/
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
        help="""
        Path to TSV file containing the list of datasets to install.
        """,
        nargs=1,
    )
    parser.add_argument(
        "participants_listing",
        help="""
        Path to TSV file containing the list of participants to get.
        """,
        nargs=1,
    )
    parser.add_argument(
        "output_dir",
        help="""
        Fullpath to the directory where the output files will be stored.
        """,
        nargs=1,
    )
    parser.add_argument(
        "--action",
        help="""
        Action to perform.
        """,
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
        help="""
        Dataset to install and get data from.
        """,
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
        help="""
        Verbosity level.
        """,
        required=False,
        choices=[0, 1, 2, 3],
        default=2,
        type=int,
        nargs=1,
    )
    parser.add_argument(
        "--datatypes",
        help="""
        Datatype to get.
        """,
        choices=[
            "anat",
            "func",
        ],
        required=False,
        default=["anat"],
        type=str,
        nargs="+",
    )
    parser.add_argument(
        "--space",
        help="""
        Space of the input data. Only applies when dataset_types requested includes fmriprep.
        """,
        required=False,
        default="MNI152NLin2009cAsym",
        type=str,
        nargs=1,
    )
    parser.add_argument(
        "--jobs",
        help="""
        Number of jobs: passed to datalad to speed up getting files.
        """,
        required=False,
        default=6,
        type=int,
        nargs=1,
    )
    parser.add_argument(
        "--dry_run",
        help="""
        Foo Bar
        """,
        action="store_true",
        default=False,
    )
    # parser.add_argument(
    #     "--bids_filter_file",
    #     help="""
    #     Foo Bar
    #     """,
    #     required=False,
    #     type=str,
    #     nargs=1,
    # )
    # parser.add_argument(
    #     "--skip_validation",
    #     help="""
    #     To skip BIDS dataset and BIDS stats model validation.
    #     """,
    #     action="store_true",
    #     default=False,
    # )

    return parser
