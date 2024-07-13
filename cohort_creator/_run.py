import argparse
from pathlib import Path

from pandas import DataFrame

from cohort_creator.logger import cc_logger

cc_log = cc_logger()


def _get_participant_listing_from_args(args: argparse.Namespace) -> DataFrame | None:
    if args.participant_listing is None:
        return None
    from cohort_creator._utils import load_participant_listing

    participant_listing = Path(args.participant_listing[0]).resolve()
    return load_participant_listing(participant_listing=participant_listing)


def _execute_install(
    dataset_listing: DataFrame, args: argparse.Namespace, output_dir: Path
) -> None:
    from cohort_creator._utils import get_list_datasets_to_install
    from cohort_creator.main import install_datasets

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
    from cohort_creator._utils import get_bids_filter

    bids_filter_file = Path(args.bids_filter_file[0]).resolve()
    return get_bids_filter(bids_filter_file=bids_filter_file) if bids_filter_file.exists() else None


def create_yoda(output_dir: Path) -> None:
    from datalad import api

    if not output_dir.exists():
        api.create(path=output_dir, cfg_proc="yoda", result_renderer="disabled")
    if not (output_dir / ".datalad").exists():
        cc_log.info(f"Creating yoda dataset for output in: {output_dir}")
        api.create(path=output_dir, cfg_proc="yoda", force=True, result_renderer="disabled")
