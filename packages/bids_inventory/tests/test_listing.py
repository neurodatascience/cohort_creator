from __future__ import annotations

import numpy as np

from bids_inventory.listing import (
    _convert_duration,
    _load_known_datasets,
    _openneuro_listing,
    is_known_dataset,
    save_known_datasets,
)


def test_is_known_dataset():
    assert is_known_dataset("ds000001")
    assert not is_known_dataset("foo")


def test_convert_duration_per_task():
    """Runs of one task must not leak into the other tasks of the same datatype."""
    duration = {"func": {"a": [(180, 2.0), (180, 2.0)], "b": [[237, 2.0]]}}
    expected = {"func": {"a": [360.0, 360.0], "b": [474.0]}}
    assert _convert_duration(duration) == expected
    # converting an already converted value must not change it
    assert _convert_duration(expected) == expected


def test_convert_duration_unknown():
    """Runs with an unknown duration are dropped and tasks without runs are None."""
    duration = {"func": {"a": [(0, np.nan), [180, None], None, 0, 360.0], "b": []}}
    assert _convert_duration(duration) == {"func": {"a": [360.0], "b": None}}


def test_save_known_datasets_round_trip(tmp_path):
    """Loading and saving a listing must not change it."""
    output_file = tmp_path / "openneuro.jsonl"
    save_known_datasets(_load_known_datasets(_openneuro_listing()), output_file)
    assert output_file.read_text() == _openneuro_listing().read_text()


def test_skipped_datasets_not_in_listing():
    """Datasets in the skip list have a reason and are not in the listing."""
    from bids_inventory.listing import known_datasets_df, skipped_datasets

    skipped = skipped_datasets()
    assert skipped
    assert all(reason for reason in skipped.values())
    assert not set(skipped) & set(known_datasets_df()["name"])
