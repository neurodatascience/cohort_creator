"""Lists openeneuro derivatives datasets from the GitHub organization.

Saves the listing to a TSV file.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from utils import get_list_of_datasets
from utils import OPENNEURO_DERIVATIVES

datasets = get_list_of_datasets(gh_orga=OPENNEURO_DERIVATIVES)
df = pd.DataFrame({"name": datasets})
df.to_csv(Path(__file__).parent / f"{OPENNEURO_DERIVATIVES}.tsv", sep="\t", index=False)
