"""Tools for basic figures about the known datasets."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from matplotlib import figure
from plotly.subplots import make_subplots

from cohort_creator.data.utils import KNOWN_DATATYPES

LABELS = {
    "nb_subjects": "number of participants",
    "nb_sessions": "number of sessions",
    "mean_size": "data per participants (bytes)",
    "nb_tasks": "number of tasks",
    "nb_datatypes": "number of datatypes",
}


def scatter_subject_vs(
    df: pd.Dataframe,
    y: str,
    size: None | str = None,
    color: None | str = "is_openneuro",
    title: None | str = "BIDS open datasets",
    log_x: bool = True,
    log_y: bool = True,
    marginal: None | str | bool = "box",
) -> figure:
    return px.scatter(
        df,
        x="nb_subjects",
        y=y,
        size=size,
        log_x=log_x,
        log_y=log_y,
        title=title,
        hover_name="name",
        marginal_x=marginal,
        marginal_y=marginal,
        labels=LABELS,
        color=color,
    )


def histogram_tasks(df: pd.Dataframe) -> figure:
    tasks = []
    for x in df.tasks:
        tasks.extend(x)

    new_df = pd.DataFrame({"tasks": tasks})

    count = new_df.tasks.value_counts()
    order = [i[0] for i in count.items()]
    return px.histogram(new_df, x="tasks", category_orders=dict(tasks=order))


def plot_against_time(df: pd.DataFrame, y: str | list[str], cumulative: bool) -> figure:
    df = df.sort_values(by=["created_on"])

    if isinstance(y, str):
        y = [y]

    if cumulative:
        tmp = []
        for col in y:
            cumsum = df[col].cumsum()
            col = f"cumsum_{col}"
            df[col] = cumsum
            tmp.append(col)
        y = tmp

    fig = px.line(df, x="created_on", y=y)

    return fig


def plot_dataset_size_vs_time(df: pd.DataFrame) -> figure:
    df = df.sort_values(by=["created_on"])

    y = []
    for col in ["size", "nb_subjects"]:
        cumsum = df[col].cumsum()
        col = f"cumsum_{col}"
        df[col] = cumsum
        y.append(col)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for col in y:
        secondary_y = False
        if col == "cumsum_nb_subjects":
            secondary_y = True

        fig.add_trace(
            go.Scatter(
                name=col.replace("cumsum_", ""), x=df["created_on"], y=df[col], mode="lines"
            ),
            secondary_y=secondary_y,
        )
    fig.update_layout(title="Continuous, variable value error bars", hovermode="x")
    fig.update_yaxes(title_text="cumulative data size", secondary_y=False, nticks=10)
    fig.update_yaxes(title_text="cumulative data size", secondary_y=False, nticks=10)
    fig.update_xaxes(title_text="time")

    return fig


def datatypes_histogram(df: pd.DataFrame) -> figure:
    datatypes_df = df[KNOWN_DATATYPES].sum()
    fig = px.bar(
        datatypes_df,
        labels={"index": "datatype", "value": "count"},
        hover_name=None,
        hover_data=None,
        title="datatypes in datasets",
    )
    return fig
