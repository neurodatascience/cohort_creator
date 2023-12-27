"""Create basic figures about the known datasets."""
from __future__ import annotations

from pathlib import Path

import plotly.express as px

from cohort_creator._utils import known_datasets_df
from cohort_creator._utils import KNOWN_DATATYPES
from cohort_creator._utils import wrangle_data
from cohort_creator.plotting import filter_data
from cohort_creator.plotting import histogram_tasks
from cohort_creator.plotting import LABELS
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

    fig = scatter_subject_vs(
        filter_data(df, is_openneuro=True), y="mean_size", size=None, color="mriqc"
    )
    fig.write_image(output_dir / "openneuro_subject_vs_mriqc.png", scale=2, width=1000)

    fig = scatter_subject_vs(
        filter_data(df, is_openneuro=True), y="mean_size", size=None, color="fmriprep"
    )
    fig.write_image(output_dir / "openneuro_subject_vs_fmriprep.png", scale=2, width=1000)

    nb_datatypes_df = (
        df[["source", "nb_datatypes"]].groupby(["source", "nb_datatypes"])["nb_datatypes"].count()
    )
    nb_datatypes_df = nb_datatypes_df.reset_index(level=[0])
    nb_datatypes_df["count"] = nb_datatypes_df["nb_datatypes"]
    nb_datatypes_df["nb_datatypes"] = nb_datatypes_df.index
    fig = px.bar(
        nb_datatypes_df,
        x="nb_datatypes",
        y="count",
        hover_name=None,
        hover_data=None,
        title="number of datatypes in BIDS datasets",
        color="source",
        labels=LABELS,
    )
    fig.write_image(output_dir / "datatypes.png", scale=2, width=1000)

    datatypes_df = filter_data(df, is_openneuro=True)[KNOWN_DATATYPES].sum()
    fig = px.bar(
        datatypes_df,
        labels={"index": "datatype", "value": "count"},
        hover_name=None,
        hover_data=None,
        title="datatypes in openneuro datasets",
    )
    fig.write_image(output_dir / "openeneuro_datatypes.png", scale=2, width=1000)

    fig = histogram_tasks(df)
    fig.write_image(output_dir / "tasks.png", scale=2, width=1000)


if __name__ == "__main__":
    main()
