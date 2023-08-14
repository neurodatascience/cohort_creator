from __future__ import annotations

from pathlib import Path

from cohort_creator._parsers import global_parser


def test_parser_install():
    parser = global_parser()
    args = parser.parse_args(
        [
            "install",
            "-d",
            str(Path()),
            "-p",
            str(Path()),
            "-o",
            str(Path()),
            "--dataset_types",
            "raw",
            "--generate_participant_listing",
        ]
    )
    print(args)


def test_parser_install_list_datasets():
    parser = global_parser()
    args = parser.parse_args(
        [
            "install",
            "-d",
            "ds000001",
            "ds000002",
            "-p",
            str(Path()),
            "-o",
            str(Path()),
            "--dataset_types",
            "raw",
            "--generate_participant_listing",
        ]
    )
    print(args)


def test_parser_install_no_participant():
    parser = global_parser()
    args = parser.parse_args(
        ["install", "-d", str(Path()), "-o", str(Path()), "--dataset_types", "raw"]
    )
    print(args)


def test_parser_get():
    parser = global_parser()
    args = parser.parse_args(
        [
            "get",
            "-d",
            str(Path()),
            "-o",
            str(Path()),
            "--dataset_types",
            "raw",
            "--bids_filter_file",
            str(Path().cwd() / "foo.json"),
        ]
    )
    print(args)
