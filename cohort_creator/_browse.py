"""Dash app to visualize studies."""

from __future__ import annotations

from typing import Any, Hashable

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, Input, Output, callback, dash_table, dcc, html
from matplotlib import figure

from cohort_creator._plotting import (
    datatypes_histogram,
    histogram_tasks,
    plot_dataset_size_vs_time,
    scatter_subject_vs,
)
from cohort_creator._version import version
from cohort_creator.data.utils import (
    KNOWN_DATATYPES,
    filter_data,
    known_datasets_df,
    save_dataset_listing,
    wrangle_data,
)

df = wrangle_data(known_datasets_df())

SOURCES = sorted(df["source"].unique().tolist())

app = Dash(__name__)

app.layout = html.Div(
    [
        html.H1(children="Cohort creator: BIDS datasets dashboard", style={"textAlign": "center"}),
        html.Div(
            [
                html.H2(children="datatypes", style={"textAlign": "left"}),
                dcc.Markdown(children="Keep datasets for specific datatypes"),
                html.Div(
                    [
                        dcc.Checklist(
                            options=KNOWN_DATATYPES, value=KNOWN_DATATYPES, id="datatypes"
                        ),
                        dcc.RadioItems(
                            options=["AND", "OR"],
                            value="OR",
                            id="datatypes-and-or",
                            inline=True,
                        ),
                    ],
                    style={
                        "display": "flex",
                        "flexDirection": "row",
                        "justify-content": "flex-start",
                    },
                ),
            ]
        ),
        html.Div(
            [
                html.H2(children="task", style={"textAlign": "left"}),
                dcc.Input(value="", type="text", id="task"),
            ]
        ),
        html.Div(
            [
                html.H2(children="sources", style={"textAlign": "left"}),
                dcc.Markdown(children="Keep datasets from..."),
                html.Div(
                    [
                        dcc.Checklist(
                            options=SOURCES,
                            value=SOURCES,
                            id="sources",
                        ),
                        dcc.RadioItems(
                            options=["AND", "OR"],
                            value="OR",
                            id="sources-and-or",
                            inline=True,
                        ),
                    ],
                    style={
                        "display": "flex",
                        "flexDirection": "row",
                        "justify-content": "flex-start",
                    },
                ),
            ],
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.H2(children="fmriprep", style={"textAlign": "left"}),
                        dcc.Markdown(children="Keep datasets with fmriprep data"),
                        dcc.RadioItems(
                            options=["true", "false", "both"],
                            value="both",
                            id="frmiprep",
                            inline=True,
                        ),
                    ],
                ),
                html.Div(
                    [
                        html.H2(children="mriqc", style={"textAlign": "left"}),
                        dcc.Markdown(children="Keep datasets with mriqc data"),
                        dcc.RadioItems(
                            options=["true", "false", "both"],
                            value="both",
                            id="mriqc",
                            inline=True,
                        ),
                    ],
                ),
                html.Div(
                    [
                        html.H2(children="physio", style={"textAlign": "left"}),
                        dcc.Markdown(children="Keep datasets with physiological data"),
                        dcc.RadioItems(
                            options=["true", "false", "both"],
                            value="both",
                            id="physio",
                            inline=True,
                        ),
                    ],
                ),
                html.Div(
                    [
                        html.H2(children="participants", style={"textAlign": "left"}),
                        dcc.Markdown(children="Keep only datasets with particpants.tsv."),
                        dcc.RadioItems(
                            options=["true", "false", "both"],
                            value="both",
                            id="participants",
                            inline=True,
                        ),
                    ],
                ),
            ],
            style={"display": "flex", "flexDirection": "row", "justify-content": "space-between"},
        ),
        html.Hr(),
        html.Div(
            [
                dash_table.DataTable(
                    page_size=15,
                    id="table",
                    style_cell={"textAlign": "left"},
                    sort_action="native",
                    style_data={
                        "whiteSpace": "normal",
                        "height": "auto",
                    },
                ),
                dbc.Alert(id="table-out"),
            ]
        ),
        html.Hr(),
        dcc.Graph(figure={}, id="datatype-histogram"),
        html.Hr(),
        dcc.Graph(figure={}, id="subject-vs-figure"),
        html.Div(
            [
                dcc.RadioItems(
                    options=[
                        "number of tasks",
                        "mean size per subject",
                        "mean duration per subject",
                    ],
                    value="number of tasks",
                    id="subject-vs",
                    inline=True,
                )
            ],
            style={"display": "flex", "flexDirection": "row", "justify-content": "center"},
        ),
        html.Hr(),
        dcc.Graph(figure={}, id="task-histogram"),
        html.Hr(),
        dcc.Graph(figure={}, id="time-vs"),
        html.Footer(
            [
                dcc.Markdown(children=f"cohort_creator version: {version}"),
                dcc.Markdown(
                    children="[Github repo](https://github.com/neurodatascience/cohort_creator.git)"
                ),
                dcc.Markdown(
                    children="Dashboard maintained by the [origami lab](https://neurodatascience.github.io/)"
                ),
                dcc.Markdown(
                    children="[Report a BUG](https://github.com/neurodatascience/cohort_creator/issues/new?assignees=&labels=bug&projects=&template=bug_report.yml&title=%5BBUG%5D+)"
                ),
            ]
        ),
    ]
)


@callback(
    Output(component_id="table", component_property="data"),
    Input(component_id="datatypes", component_property="value"),
    Input(component_id="datatypes-and-or", component_property="value"),
    Input(component_id="sources", component_property="value"),
    Input(component_id="sources-and-or", component_property="value"),
    Input(component_id="task", component_property="value"),
    Input(component_id="frmiprep", component_property="value"),
    Input(component_id="mriqc", component_property="value"),
    Input(component_id="physio", component_property="value"),
    Input(component_id="participants", component_property="value"),
)
def update_table(
    datatypes: list[str] = KNOWN_DATATYPES,
    datatypes_and_or: str = "OR",
    sources: list[str] = SOURCES,
    sources_and_or: str = "OR",
    task: str = "",
    fmriprep: None | str = None,
    mriqc: None | str = None,
    physio: None | str = None,
    participants: None | str = None,
) -> list[dict[Hashable, Any]]:
    filtered_df = filter_data(
        df,
        config={
            "datatypes": datatypes,
            "datatypes_and_or": datatypes_and_or,
            "sources": sources,
            "sources_and_or": sources_and_or,
            "task": task,
            "fmriprep": fmriprep,
            "mriqc": mriqc,
            "physio": physio,
            "participants": participants,
        },
    )
    save_dataset_listing(filtered_df)
    return table_to_show(filtered_df).to_dict("records")


# TODO add a way to display a link to the dataset to explore it on github / openneuro
# @callback(Output('table-out', 'children'), Input('table', 'active_cell'))
# def update_graphs(active_cell):
#     return str(active_cell) if active_cell else "Click the table"


def table_to_show(dataframe: pd.DataFrame) -> pd.DataFrame:
    # reorder columns
    cols = [
        "name",
        "nb_subjects",
        "nb_sessions",
        "datatypes",
        "tasks",
    ]
    sub_df = dataframe[cols]
    # convert list to string
    sub_df["datatypes"] = sub_df["datatypes"].apply(lambda x: ", ".join(x))
    sub_df["tasks"] = sub_df["tasks"].apply(lambda x: ", ".join(x))
    return sub_df


@callback(
    Output(component_id="datatype-histogram", component_property="figure"),
    Input(component_id="datatypes", component_property="value"),
    Input(component_id="datatypes-and-or", component_property="value"),
    Input(component_id="sources", component_property="value"),
    Input(component_id="sources-and-or", component_property="value"),
    Input(component_id="task", component_property="value"),
    Input(component_id="frmiprep", component_property="value"),
    Input(component_id="mriqc", component_property="value"),
    Input(component_id="physio", component_property="value"),
    Input(component_id="participants", component_property="value"),
)
def update_datatype_histogram(
    datatypes: list[str] = KNOWN_DATATYPES,
    datatypes_and_or: str = "OR",
    sources: list[str] = SOURCES,
    sources_and_or: str = "OR",
    task: str = "",
    fmriprep: None | str = None,
    mriqc: None | str = None,
    physio: None | str = None,
    participants: None | str = None,
) -> figure:
    filtered_df = filter_data(
        df,
        config={
            "datatypes": datatypes,
            "datatypes_and_or": datatypes_and_or,
            "sources": sources,
            "sources_and_or": sources_and_or,
            "task": task,
            "fmriprep": fmriprep,
            "mriqc": mriqc,
            "physio": physio,
            "participants": participants,
        },
    )
    return datatypes_histogram(filtered_df)


@callback(
    Output(component_id="subject-vs-figure", component_property="figure"),
    Input(component_id="datatypes", component_property="value"),
    Input(component_id="datatypes-and-or", component_property="value"),
    Input(component_id="sources", component_property="value"),
    Input(component_id="sources-and-or", component_property="value"),
    Input(component_id="task", component_property="value"),
    Input(component_id="frmiprep", component_property="value"),
    Input(component_id="mriqc", component_property="value"),
    Input(component_id="physio", component_property="value"),
    Input(component_id="participants", component_property="value"),
    Input(component_id="subject-vs", component_property="value"),
)
def update_subject_vs(
    datatypes: list[str] = KNOWN_DATATYPES,
    datatypes_and_or: str = "OR",
    sources: list[str] = SOURCES,
    sources_and_or: str = "OR",
    task: str = "",
    fmriprep: None | str = None,
    mriqc: None | str = None,
    physio: None | str = None,
    participants: None | str = None,
    subject_vs: str = "number of tasks",
) -> figure:
    filtered_df = filter_data(
        df,
        config={
            "datatypes": datatypes,
            "datatypes_and_or": datatypes_and_or,
            "sources": sources,
            "sources_and_or": sources_and_or,
            "task": task,
            "fmriprep": fmriprep,
            "mriqc": mriqc,
            "physio": physio,
            "participants": participants,
        },
    )
    if subject_vs == "number of tasks":
        y = "nb_tasks"
    elif subject_vs == "mean size per subject":
        y = "mean_size"
    elif subject_vs == "mean duration per subject":
        y = "total_duration"
    return scatter_subject_vs(
        filtered_df,
        y=y,
        size=None,
        color="source",
        title=f"{subject_vs} VS number of participants",
    )


@callback(
    Output(component_id="task-histogram", component_property="figure"),
    Input(component_id="datatypes", component_property="value"),
    Input(component_id="datatypes-and-or", component_property="value"),
    Input(component_id="sources", component_property="value"),
    Input(component_id="sources-and-or", component_property="value"),
    Input(component_id="task", component_property="value"),
    Input(component_id="frmiprep", component_property="value"),
    Input(component_id="mriqc", component_property="value"),
    Input(component_id="physio", component_property="value"),
    Input(component_id="participants", component_property="value"),
)
def update_task_histogram(
    datatypes: list[str] = KNOWN_DATATYPES,
    datatypes_and_or: str = "OR",
    sources: list[str] = SOURCES,
    sources_and_or: str = "OR",
    task: str = "",
    fmriprep: None | str = None,
    mriqc: None | str = None,
    physio: None | str = None,
    participants: None | str = None,
) -> figure:
    filtered_df = filter_data(
        df,
        config={
            "datatypes": datatypes,
            "datatypes_and_or": datatypes_and_or,
            "sources": sources,
            "sources_and_or": sources_and_or,
            "task": task,
            "fmriprep": fmriprep,
            "mriqc": mriqc,
            "physio": physio,
            "participants": participants,
        },
    )

    return histogram_tasks(filtered_df)


@callback(
    Output(component_id="time-vs", component_property="figure"),
    Input(component_id="datatypes", component_property="value"),
    Input(component_id="datatypes-and-or", component_property="value"),
    Input(component_id="sources", component_property="value"),
    Input(component_id="sources-and-or", component_property="value"),
    Input(component_id="task", component_property="value"),
    Input(component_id="frmiprep", component_property="value"),
    Input(component_id="mriqc", component_property="value"),
    Input(component_id="physio", component_property="value"),
    Input(component_id="participants", component_property="value"),
)
def update_time_vs(
    datatypes: list[str] = KNOWN_DATATYPES,
    datatypes_and_or: str = "OR",
    sources: list[str] = SOURCES,
    sources_and_or: str = "OR",
    task: str = "",
    fmriprep: None | str = None,
    mriqc: None | str = None,
    physio: None | str = None,
    participants: None | str = None,
) -> figure:
    filtered_df = filter_data(
        df,
        config={
            "datatypes": datatypes,
            "datatypes_and_or": datatypes_and_or,
            "sources": sources,
            "sources_and_or": sources_and_or,
            "task": task,
            "fmriprep": fmriprep,
            "mriqc": mriqc,
            "physio": physio,
            "participants": participants,
        },
    )
    return plot_dataset_size_vs_time(filtered_df)


def browse(debug: bool = True) -> None:
    app.run(debug=debug)


if __name__ == "__main__":
    browse()
