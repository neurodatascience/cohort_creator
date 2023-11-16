"""Create basic figures about the known datasets."""
from __future__ import annotations

from pathlib import Path

import plotly.express as px

from cohort_creator._utils import known_datasets_df
from cohort_creator._utils import KNOWN_MODALITIES
from cohort_creator._utils import wrangle_data
from cohort_creator.plotting import filter_data
from cohort_creator.plotting import scatter_subject_vs


def main() -> None:
    output_dir = Path(__file__).parent / "source" / "images"

    df = wrangle_data(known_datasets_df())
    df = filter_data(df, is_openneuro=None)

    fig = scatter_subject_vs(df, y="nb_sessions", size=None, color="source")
    fig.write_image(output_dir / "subject_vs_sessions.png", scale=2, width=1000)

    fig = scatter_subject_vs(df, y="nb_tasks", size=None, color="source")
    fig.write_image(output_dir / "subject_vs_tasks.png", scale=2, width=1000)

    fig = scatter_subject_vs(df, y="mean_size", size=None, color="source")
    fig.write_image(output_dir / "subject_vs_size.png", scale=2, width=1000)

    modalities_df = filter_data(df, is_openneuro=True)[KNOWN_MODALITIES].sum()
    fig = px.bar(
        modalities_df,
        labels={"index": "datatype", "value": "count"},
        hover_name=None,
        hover_data=None,
        title="datatype in opnneuro datasets",
    )
    fig.write_image(output_dir / "openeneuro_datatypes.png", scale=2, width=1000)


if __name__ == "__main__":
    main()
