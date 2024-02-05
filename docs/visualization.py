"""Create basic figures about the known datasets."""

from __future__ import annotations

from pathlib import Path

import plotly.express as px

from cohort_creator._plotting import (
    LABELS,
    datatypes_histogram,
    histogram_tasks,
    plot_dataset_size_vs_time,
    scatter_subject_vs,
)
from cohort_creator.data.utils import (
    _count_extensions,
    filter_data,
    known_datasets_df,
    save_dataset_listing,
    wrangle_data,
)

# filter_config = {"is_openneuro": None, "task": "rest", "physio": True, "datatypes": ["func"]}
# filter_config = {"is_openneuro": None, "datatypes": ["meg"]}
filter_config = None


def main() -> None:
    output_dir = Path(__file__).parent / "source" / "images"

    df = wrangle_data(known_datasets_df())

    df = filter_data(df, config=filter_config)

    fig = plot_dataset_size_vs_time(df)
    fig.write_image(output_dir / "size_vs_time.png", scale=2, width=1000)

    fig = scatter_subject_vs(df, y="nb_sessions", size=None, color="source")
    fig.write_image(output_dir / "subject_vs_sessions.png", scale=2, width=1000)

    fig = scatter_subject_vs(df, y="nb_tasks", size=None, color="source")
    fig.write_image(output_dir / "subject_vs_tasks.png", scale=2, width=1000)

    fig = scatter_subject_vs(df, y="mean_size", size=None, color="source")
    fig.write_image(output_dir / "subject_vs_size.png", scale=2, width=1000)

    df_duration = df[df["total_duration"] > 0]
    fig = scatter_subject_vs(df_duration, y="total_duration", size=None, color="source", log_y=True)
    fig.write_image(output_dir / "subject_vs_total_duration.png", scale=2, width=1000)

    fig = scatter_subject_vs(
        filter_data(df, {"is_openneuro": True}), y="mean_size", size=None, color="has_mriqc"
    )
    fig.write_image(output_dir / "openneuro_subject_vs_mriqc.png", scale=2, width=1000)

    fig = scatter_subject_vs(
        filter_data(df, {"is_openneuro": True}), y="mean_size", size=None, color="has_fmriprep"
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

    datatypes_df = filter_data(df, {"is_openneuro": None})
    fig = datatypes_histogram(datatypes_df)
    fig.write_image(output_dir / "openeneuro_datatypes.png", scale=2, width=1000)

    fig = histogram_tasks(df)
    fig.write_image(output_dir / "tasks.png", scale=2, width=1000)

    count = _count_extensions(df, "eeg")
    fig = px.histogram(count, x="extension", y="count", title="EEG file formats")
    fig.update_yaxes(title_text=f"percentage of datasets (out of {len(df[df['eeg']])})")
    fig.write_image(output_dir / "eeg_file_formats.png", scale=2, width=1000)

    count = _count_extensions(df, "ieeg")
    fig = px.histogram(count, x="extension", y="count", title="iEEG file formats")
    fig.update_yaxes(title_text=f"percentage of datasets (out of {len(df[df['ieeg']])})")
    fig.write_image(output_dir / "ieeg_file_formats.png", scale=2, width=1000)

    count = _count_extensions(df, "meg")
    fig = px.histogram(count, x="extension", y="count", title="MEG file formats")
    fig.update_yaxes(title_text=f"percentage of datasets (out of {len(df[df['meg']])})")
    fig.write_image(output_dir / "meg_file_formats.png", scale=2, width=1000)

    save_dataset_listing(df)


if __name__ == "__main__":
    main()
