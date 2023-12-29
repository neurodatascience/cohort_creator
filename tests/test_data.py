from __future__ import annotations

from cohort_creator.data.utils import is_known_dataset
from cohort_creator.data.utils import known_datasets_df
from cohort_creator.data.utils import wrangle_data


def test_is_known_dataset():
    assert is_known_dataset("ds000001")
    assert not is_known_dataset("foo")


def test_wrangle_data():
    wrangle_data(known_datasets_df())
