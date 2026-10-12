"""Keep an inventory of publicly available BIDS datasets."""

from __future__ import annotations

import pandas as pd

from bids_inventory.listing import known_datasets_df
from bids_inventory.wrangling import filter_data, wrangle_data

__all__ = ["filter_data", "known_datasets_df", "load_inventory", "wrangle_data"]


def load_inventory() -> pd.DataFrame:
    """Return the listing of known BIDS datasets with extra summary columns.

    Returns
    -------
    pd.DataFrame
        One row per dataset.
        See :func:`bids_inventory.wrangling.wrangle_data`
        for the description of the extra columns.

    Examples
    --------
    >>> from bids_inventory import filter_data, load_inventory
    >>> df = load_inventory()
    >>> eeg_datasets = filter_data(df, config={"datatypes": ["eeg"]})
    """
    return wrangle_data(known_datasets_df())
