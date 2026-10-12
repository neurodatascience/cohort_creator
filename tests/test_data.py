from __future__ import annotations

import numpy as np

from cohort_creator.data.utils import (
    _convert_duration,
    _load_known_datasets,
    _openneuro_listing,
    filter_data,
    is_known_dataset,
    known_datasets_df,
    save_known_datasets,
    wrangle_data,
)


def test_is_known_dataset():
    assert is_known_dataset("ds000001")
    assert not is_known_dataset("foo")


def test_wrangle_data():
    wrangle_data(known_datasets_df())


def test_filter_data():
    df = wrangle_data(known_datasets_df())
    fitlered_df = filter_data(df, config=None)

    assert len(df) == len(fitlered_df)


def test_filter_data_no_datasets():
    df = wrangle_data(known_datasets_df())
    fitlered_df = filter_data(df, config={"datatypes": ["foo"]})

    assert len(fitlered_df) == 0


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


def test_wrangle_data_has_derivatives():
    """Only datasets with a derivative URL should be flagged as having it."""
    df = known_datasets_df()
    wrangled = wrangle_data(df)
    for der in ["fmriprep", "freesurfer", "mriqc"]:
        assert wrangled[f"has_{der}"].sum() == df[der].notna().sum()
        assert wrangled[f"has_{der}"].sum() < len(wrangled)
