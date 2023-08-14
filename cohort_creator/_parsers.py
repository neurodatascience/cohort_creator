"""General parser for the cohort_creator package."""
from __future__ import annotations

import argparse
from typing import IO

import rich

from ._version import __version__

DOC_URL = "https://cohort-creator.readthedocs.io/en/latest/"
FAQ_URL = f"{DOC_URL}faq.html"


class MuhParser(argparse.ArgumentParser):
    def _print_message(self, message: str, file: IO[str] | None = None) -> None:
        rich.print(message, file=file)


def base_parser() -> MuhParser:
    parser = MuhParser(
        prog="cohort_creator",
        description="Creates a cohort by grabbing specific subjects from opennneuro datasets.",
        epilog=f"""
        For a more readable version of this help section,
        see the `online doc <{DOC_URL}>`_.
        """,
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{__version__}",
    )
    return parser


def add_common_arguments(parser: MuhParser) -> MuhParser:
    parser.add_argument(
        "-d",
        "--dataset_listing",
        help="""
        Path to TSV file containing the list of datasets to get.
        """,
        required=True,
        nargs=1,
    )
    parser.add_argument(
        "-p",
        "--participant_listing",
        help="""
        Path to TSV file containing the list of participants to get.
        Optional. If not provided, all participants will be downloaded.
        """,
        default=None,
        required=False,
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
    return parser


def add_specialized_args(parser: MuhParser) -> MuhParser:
    """Add arguments for get and copy."""
    parser.add_argument(
        "--datatypes",
        help="""
        Datatype to get.
        """,
        choices=[
            "anat",
            "func",
            "fmap",
        ],
        required=False,
        default=["anat"],
        type=str,
        nargs="+",
    )
    parser.add_argument(
        "--space",
        help="""
        Space of the input data. Only applies when `dataset_types` requested includes `fmriprep`.
        """,
        required=False,
        default="MNI152NLin2009cAsym",
        type=str,
        nargs=1,
    )
    parser.add_argument(
        "--bids_filter_file",
        help=f"""
        Path to a JSON file describing custom BIDS input filters.
        For further details, please check out the `FAQ <{FAQ_URL}>`_.
        """,
        required=False,
        nargs=1,
    )
    return parser


def global_parser() -> MuhParser:
    parser = base_parser()
    subparsers = parser.add_subparsers(
        dest="command",
        help="Choose a subcommand",
        required=True,
    )

    install_parser = subparsers.add_parser(
        "install",
        help="""
        Install several openneuro datasets.

        Example:

        .. code-block:: bash

            cohort_creator install \\
                --dataset_listing inputs/dataset-results.tsv \\
                --participant_listing inputs/participant-results.tsv \\
                --output_dir outputs \\
                --dataset_types raw mriqc fmriprep \\
                --verbosity 3
        """,
    )
    install_parser = add_common_arguments(install_parser)
    install_parser.add_argument(
        "--generate_participant_listing",
        action="store_true",
        help="Skips rerunning mriqc on the subset of participants.",
    )

    get_parser = subparsers.add_parser(
        "get",
        help="""
        Get specified data for a cohort of subjects.

        Example:

        .. code-block:: bash

            cohort_creator get \\
                --dataset_listing inputs/dataset-results.tsv \\
                --participant_listing inputs/participant-results.tsv \\
                --output_dir outputs \\
                --dataset_types raw mriqc fmriprep \\
                --datatype anat func \\
                --space T1w MNI152NLin2009cAsym \\
                --jobs 6 \\
                --verbosity 3
        """,
    )
    get_parser = add_common_arguments(get_parser)
    get_parser = add_specialized_args(get_parser)
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

        Example:

        .. code-block:: bash

            cohort_creator copy \\
                --dataset_listing inputs/dataset-results.tsv \\
                --participant_listing inputs/participant-results.tsv \\
                --output_dir outputs \\
                --dataset_types raw mriqc fmriprep \\
                --datatype anat func \\
                --space T1w MNI152NLin2009cAsym \\
                --verbosity 3
        """,
    )
    copy_parser = add_common_arguments(copy_parser)
    copy_parser = add_specialized_args(copy_parser)
    copy_parser.add_argument(
        "--skip_group_mriqc",
        action="store_true",
        help="Skips rerunning mriqc on the subset of participants.",
    )

    all_parser = subparsers.add_parser(
        "all",
        help="""
        Install, get, and copy cohort of subjects.

        Example:

        .. code-block:: bash

            cohort_creator all \\
                --dataset_listing inputs/dataset-results.tsv \\
                --participant_listing inputs/participant-results.tsv \\
                --output_dir outputs \\
                --dataset_types raw mriqc fmriprep \\
                --datatype anat func \\
                --space T1w MNI152NLin2009cAsym \\
                --verbosity 3
        """,
    )
    all_parser = add_common_arguments(all_parser)
    all_parser = add_specialized_args(all_parser)
    all_parser.add_argument(
        "--jobs",
        help="""
        Number of jobs: passed to datalad to speed up getting files.
        """,
        required=False,
        default=6,
        type=int,
        nargs=1,
    )
    all_parser.add_argument(
        "--skip_group_mriqc",
        action="store_true",
        help="Skips rerunning mriqc on the subset of participants.",
    )
    return parser
