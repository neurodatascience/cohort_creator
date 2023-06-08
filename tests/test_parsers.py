from __future__ import annotations

from pathlib import Path

from cohort_creator._parsers import global_parser


def test_parser_install():
    parser = global_parser()
    args = parser.parse_args(
        ["install", "-p", str(Path()), "-o", str(Path()), "--dataset_types", "raw"]
    )
    print(args)


def test_parser_get():
    parser = global_parser()
    args = parser.parse_args(
        [
            "get",
            "-p",
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
