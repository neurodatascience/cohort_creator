from __future__ import annotations

from cohort_creator.data.utils import (
    _convert_duration,
    filter_data,
    is_known_dataset,
    known_datasets_df,
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
    duration = "{'func': {'a': [(180, 2.0), (180, 2.0)], 'b': [(237, 2.0)]}}"
    expected = {"func": {"a": [360.0, 360.0], "b": [474.0]}}
    assert _convert_duration(duration) == expected
    # converting an already converted value must not change it
    assert _convert_duration(str(expected)) == expected


def test_convert_duration_numpy_repr():
    assert _convert_duration("{'func': {'a': [np.float64(360.0)]}}") == {"func": {"a": [360.0]}}
