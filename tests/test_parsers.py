from __future__ import annotations

from pathlib import Path

from cohort_creator._parsers import global_parser


def test_parser_for_get_data():
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
        ]
    )
    print(args)
