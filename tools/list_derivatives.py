"""Lists openeneuro derivatives datasets from GitHub organization."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from utils import get_list_of_datasets

datasets = get_list_of_datasets(gh_orga="OpenNeuroDerivatives")
datasets = [x for x in datasets if x.startswith("ds")]
df = pd.DataFrame({"name": datasets})
df.to_csv(Path(__file__).parent / "OpenNeuroDerivatives.tsv", sep="\t", index=False)
