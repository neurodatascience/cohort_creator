"""Command line interface for bids_inventory."""

from __future__ import annotations

import logging
import sys
from argparse import ArgumentParser, HelpFormatter
from collections.abc import Sequence

from rich_argparse import RichHelpFormatter

from bids_inventory._version import __version__
from bids_inventory.logger import bi_logger

bi_log = bi_logger()


def global_parser(formatter_class: type[HelpFormatter] = HelpFormatter) -> ArgumentParser:
    parser = ArgumentParser(
        prog="bids_inventory",
        description="Keep an inventory of publicly available BIDS datasets.",
        formatter_class=formatter_class,
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{__version__}",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        help="Choose a subcommand",
        required=True,
    )

    browse_parser = subparsers.add_parser(
        "browse",
        help="""Launch a dash app in the browser
to browse, visualize and filter the listing of known datasets.
It will also create a datasets_results.tsv with the filtered list of datasets.""",
        formatter_class=parser.formatter_class,
    )
    browse_parser.add_argument(
        "--debug",
        action="store_true",
        help="Runs the Dash app in debug mode.",
    )
    _add_verbosity(browse_parser)

    update_parser = subparsers.add_parser(
        "update",
        help="Update listing of known BIDS datasets.",
        formatter_class=parser.formatter_class,
    )
    update_parser.add_argument(
        "--debug",
        action="store_true",
        help="Only runs the update for a few subset of datasets.",
    )
    _add_verbosity(update_parser)

    return parser


def _add_verbosity(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--verbosity",
        help="""
        Verbosity level.
        """,
        required=False,
        choices=[0, 1, 2, 3],
        default=2,
        type=int,
    )


def set_verbosity(verbosity: int) -> None:
    levels = {0: "ERROR", 1: "WARNING", 2: "INFO", 3: "DEBUG"}
    bi_log.setLevel(levels[verbosity])

    if verbosity < 3:
        logging.getLogger("datalad").setLevel(logging.WARNING)
        logging.getLogger("datalad.gitrepo").setLevel(logging.ERROR)


def cli(argv: Sequence[str] = sys.argv) -> None:
    """Entry point."""
    parser = global_parser(formatter_class=RichHelpFormatter)
    args = parser.parse_args(argv[1:])

    set_verbosity(args.verbosity)

    if args.command == "browse":
        from bids_inventory._browse import browse

        browse(debug=args.debug)

    elif args.command == "update":
        from bids_inventory._update import update

        update(debug=args.debug)
