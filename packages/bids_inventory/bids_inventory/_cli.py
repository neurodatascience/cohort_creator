"""Command line interface for bids_inventory."""

import logging
import os
import sys
from argparse import ArgumentParser, HelpFormatter
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

from rich_argparse import RichHelpFormatter

from bids_inventory._version import __version__
from bids_inventory.logger import add_log_files, bi_logger

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

    remove_parser = subparsers.add_parser(
        "remove",
        help="""Remove datasets from the listing,
for example so that the next 'bids_inventory update' indexes them again.""",
        formatter_class=parser.formatter_class,
    )
    remove_parser.add_argument(
        "datasets",
        nargs="+",
        help="Names of the datasets to remove, for example: ds000001 ds000002.",
    )
    remove_parser.add_argument(
        "--source",
        help="Which listing to remove them from.",
        choices=["openneuro", "non-openneuro"],
        default="openneuro",
    )
    _add_verbosity(remove_parser)

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
    update_parser.add_argument(
        "--jobs",
        help="Number of new datasets to install, and of NIfTI headers to read, in parallel.",
        required=False,
        default=4,
        type=int,
    )
    update_parser.add_argument(
        "--source",
        help="""
        Which listing to update: datasets on OpenNeuro,
        or other datasets (ABIDE, ABIDE 2, ADHD-200, CoRR, CNeuroMod)
        installed in the folder set by 'local_paths.non_openneuro' in the configuration.
        """,
        choices=["openneuro", "non-openneuro"],
        default="openneuro",
    )
    update_parser.add_argument(
        "--reindex",
        help="""
        Index again all the datasets, not only those missing from the listing,
        for example to fill new fields.
        Can be resumed: if interrupted, run the same command again.
        """,
        action="store_true",
    )
    update_parser.add_argument(
        "--log-dir",
        help="""
        Folder where to save the warnings and the errors of the update,
        in 2 separate files.
        """,
        required=False,
        default=Path("logs"),
        type=Path,
    )
    update_parser.add_argument(
        "--config",
        help="""
        YAML file with local settings (paths to datasets, GitHub token file...).
        See bids_inventory/data/config.yml for the available settings.
        Can also be set with the BIDS_INVENTORY_CONFIG environment variable.
        """,
        required=False,
        type=Path,
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


@contextmanager
def _check_extra(extra: str) -> Iterator[None]:
    """Exit with an explanation if the optional dependencies of a command are missing."""
    try:
        yield
    except ImportError as e:
        bi_log.error(
            f"The '{extra}' command needs optional dependencies ({e.name} is missing).\n"
            f"Install them with: pip install 'bids-inventory[{extra}]'"
        )
        sys.exit(1)


def cli(argv: Sequence[str] = sys.argv) -> None:
    """Entry point."""
    parser = global_parser(formatter_class=RichHelpFormatter)
    args = parser.parse_args(argv[1:])

    set_verbosity(args.verbosity)

    if args.command == "browse":
        with _check_extra("browse"):
            from bids_inventory._browse import browse

        browse(debug=args.debug)

    elif args.command == "remove":
        from bids_inventory.listing import (
            _non_openneuro_listing,
            _openneuro_listing,
            remove_datasets,
        )

        listing = _openneuro_listing() if args.source == "openneuro" else _non_openneuro_listing()
        removed = remove_datasets(args.datasets, listing)
        bi_log.info(f"Removed {len(removed)} datasets from {listing}: {' '.join(removed)}")
        if not_found := sorted(set(args.datasets) - set(removed)):
            bi_log.warning(f"Not in the listing: {' '.join(not_found)}")

    elif args.command == "update":
        with _check_extra("update"):
            from bids_inventory._update import CONFIG_ENV_VAR, update

        if args.jobs < 1:
            bi_log.error(f"--jobs must be at least 1, got {args.jobs}")
            sys.exit(1)

        if args.config is not None:
            if not args.config.is_file():
                bi_log.error(f"Config file not found: {args.config}")
                sys.exit(1)
            os.environ[CONFIG_ENV_VAR] = str(args.config.resolve())

        warnings_log, errors_log = add_log_files(args.log_dir)
        try:
            update(debug=args.debug, jobs=args.jobs, reindex=args.reindex, source=args.source)
        finally:
            for log_file in [warnings_log, errors_log]:
                if log_file.exists():
                    bi_log.info(f"See {log_file}")
