from __future__ import annotations

from cohort_creator.data.utils import (
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
