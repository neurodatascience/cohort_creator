"""Show how to select a subset of datasets."""
from __future__ import annotations

from cohort_creator.data.utils import filter_data
from cohort_creator.data.utils import known_datasets_df
from cohort_creator.data.utils import save_dataset_listing
from cohort_creator.data.utils import wrangle_data

filter_config = {"task": "back", "datatypes": ["func"]}
df = wrangle_data(known_datasets_df())
df = filter_data(df, config=filter_config)
save_dataset_listing(df)
