"""Tools for basic figures about the known datasets."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
from matplotlib import Figure


def filter_data(df: pd.Dataframe, is_openneuro: None | bool = None) -> pd.DataFrame:
    if is_openneuro:
        mask = df["is_openneuro"] == True  # noqa
        return df[mask]
    else:
        return df


def scatter_subject_vs(
    df: pd.Dataframe,
    y: str,
    size: None | str = None,
    color: None | str = "is_openneuro",
    title: None | str = "BIDS open datasets",
) -> Figure:
    return px.scatter(
        df,
        x="nb_subjects",
        y=y,
        size=size,
        log_x=True,
        log_y=True,
        title=title,
        hover_name="name",
        marginal_x="box",
        marginal_y="box",
        labels={
            "nb_subjects": "number of participants",
            "nb_sessions": "number of sessions",
            "mean_size": "data per participants (bytes)",
            "nb_tasks": "number of tasks",
        },
        color=color,
    )
