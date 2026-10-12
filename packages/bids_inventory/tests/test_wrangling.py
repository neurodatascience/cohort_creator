from __future__ import annotations

from bids_inventory.listing import known_datasets_df
from cohort_creator.data.utils import (
    filter_data,
    wrangle_data,
)


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


def test_wrangle_data_has_derivatives():
    """Only datasets with a derivative URL should be flagged as having it."""
    df = known_datasets_df()
    wrangled = wrangle_data(df)
    for der in ["fmriprep", "freesurfer", "mriqc"]:
        assert wrangled[f"has_{der}"].sum() == df[der].notna().sum()
        assert wrangled[f"has_{der}"].sum() < len(wrangled)
