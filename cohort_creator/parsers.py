"""General parser for the cohort_creator package."""
from __future__ import annotations

import argparse
from typing import IO

import rich

from ._version import __version__


class _MuhParser(argparse.ArgumentParser):
    def _print_message(self, message: str, file: IO[str] | None = None) -> None:
        rich.print(message, file=file)


def _base_parser() -> _MuhParser:
    parser = _MuhParser(
        prog="cohort_creator",
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
    return parser


def _add_common_arguments(parser: _MuhParser) -> _MuhParser:
    parser.add_argument(
        "-d",
        "--datasets_listing",
        help="""
        Path to TSV file containing the list of datasets to install.
        """,
        nargs=1,
    )
    parser.add_argument(
        "-p",
        "--participants_listing",
        help="""
        Path to TSV file containing the list of participants to get.
        """,
        nargs=1,
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        help="""
        Fullpath to the directory where the output files will be stored.
        """,
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
    # parser.add_argument(
    #     "--dry_run",
    #     help="""
    #     Foo Bar
    #     """,
    #     action="store_true",
    #     default=False,
    # )
    return parser


def common_parser() -> _MuhParser:
    parser = _base_parser()
    parser = _add_common_arguments(parser)
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


def _add_specialized_args(parser: _MuhParser) -> _MuhParser:
    """Add arguments for get and copy."""
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
    return parser


def global_parser() -> _MuhParser:
    parser = _base_parser()
    subparsers = parser.add_subparsers(
        dest="command",
        help="Choose a subcommand",
        required=True,
    )
    install_parser = subparsers.add_parser(
        "install",
        help="""
        Install several openneuro datasets.
        """,
    )
    install_parser = _add_common_arguments(install_parser)

    get_parser = subparsers.add_parser(
        "get",
        help="""
        Get specified data for a cohort of subjects.
        """,
    )
    get_parser = _add_common_arguments(get_parser)
    get_parser = _add_specialized_args(get_parser)
    get_parser.add_argument(
        "--jobs",
        help="""
        Number of jobs: passed to datalad to speed up getting files.
        """,
        required=False,
        default=6,
        type=int,
        nargs=1,
    )
    copy_parser = subparsers.add_parser(
        "copy",
        help="""
        Copy cohort of subjects into separate directory.
        """,
    )
    copy_parser = _add_common_arguments(copy_parser)
    copy_parser = _add_specialized_args(copy_parser)
    return parser
