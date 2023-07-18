"""Convert tsv to csv for rendering in docs."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

files = ["dataset-results.tsv", "participant-results.tsv"]

target_dir = Path(__file__).parent / "source" / "data"

for f in files:
    input_file = target_dir / f
    df = pd.read_csv(input_file, sep="\t")
    df.to_csv(input_file.with_suffix(".csv"), index=False)
