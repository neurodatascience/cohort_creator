"""Tools for basic figures about the known datasets."""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from matplotlib import figure
from plotly.subplots import make_subplots

from cohort_creator._utils import KNOWN_DATATYPES

LABELS = {
    "nb_subjects": "number of participants",
    "nb_sessions": "number of sessions",
    "mean_size": "data per participants (bytes)",
    "nb_tasks": "number of tasks",
    "nb_datatypes": "number of datatypes",
}


def filter_data(df: pd.Dataframe, config: Any = None) -> pd.DataFrame:
    ALL_TRUE = df["name"].apply(lambda x: bool(x))

    config = _check_config(config)

    mask_openneuro = ALL_TRUE
    if config["is_openneuro"] is not None:
        mask_openneuro = df["is_openneuro"] == config["is_openneuro"]

    # better filtering should make sure
    # that the one of the requested datatypes has the task of interest
    mask_task = ALL_TRUE
    if config["task"] != "":
        mask_task = df["tasks"].apply(lambda x: config["task"] in "".join(x).lower())

    mask_physio = ALL_TRUE
    if config["physio"] is not None:
        mask_physio = df["has_physio"] == config["physio"]

    mask_fmriprep = ALL_TRUE
    if config["fmriprep"] is not None:
        mask_fmriprep = df["fmriprep"] == config["fmriprep"]

    mask_mriqc = ALL_TRUE
    if config["mriqc"] is not None:
        mask_mriqc = df["mriqc"] == config["mriqc"]

    mask_datatypes = df["datatypes"].apply(
        lambda x: len(set(x).intersection(config["datatypes"])) > 0
    )

    all_filters = pd.concat(
        (mask_openneuro, mask_task, mask_fmriprep, mask_mriqc, mask_physio, mask_datatypes), axis=1
    ).all(axis=1)

    return df[all_filters]


def _check_config(config: Any) -> dict[str, bool | str | list[str]]:
    DEFAULT_CONFIG: dict[str, bool | str | list[str] | None] = {
        "is_openneuro": None,
        "fmriprep": None,
        "mriqc": None,
        "physio": None,
        "task": "",
        "datatypes": KNOWN_DATATYPES,
    }
    if not config:
        config = DEFAULT_CONFIG

    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value

    if isinstance(config["datatypes"], bool):
        config["datatypes"] = KNOWN_DATATYPES
    if isinstance(config["datatypes"], str):
        config["datatypes"] = [config["datatypes"]]

    return config


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
    order = []
    for i in count.items():
        order.append(i[0])

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
