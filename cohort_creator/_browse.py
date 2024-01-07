"""Dash app to visualize studies."""
from __future__ import annotations

from typing import Any
from typing import Hashable

import pandas as pd
from dash import callback
from dash import Dash
from dash import dash_table
from dash import dcc
from dash import html
from dash import Input
from dash import Output

from cohort_creator.data.utils import filter_data
from cohort_creator.data.utils import known_datasets_df
from cohort_creator.data.utils import KNOWN_DATATYPES
from cohort_creator.data.utils import save_dataset_listing
from cohort_creator.data.utils import wrangle_data

# import plotly.express as px
# from matplotlib import figure
# from cohort_creator._plotting import datatypes_histogram
# from cohort_creator._plotting import scatter_subject_vs

df = wrangle_data(known_datasets_df())


app = Dash(__name__)

app.layout = html.Div(
    [
        html.H1(children="BIDS datasets", style={"textAlign": "center"}),
        html.H2(children="datatypes", style={"textAlign": "left"}),
        dcc.Checklist(options=KNOWN_DATATYPES, value=KNOWN_DATATYPES, id="datatypes"),
        html.H2(children="task", style={"textAlign": "left"}),
        dcc.Input(value="", type="text", id="task"),
        html.Div(
            [
                html.Div(
                    [
                        html.H2(children="openneuro", style={"textAlign": "left"}),
                        dcc.Markdown(children="""Keep datasets from openneuro"""),
                        dcc.RadioItems(
                            options=["true", "false", "both"],
                            value="both",
                            id="openneuro",
                            inline=True,
                        ),
                    ],
                ),
                html.Div(
                    [
                        html.H2(children="fmriprep", style={"textAlign": "left"}),
                        dcc.Markdown(children="""Keep datasets with fmriprep data"""),
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
                        dcc.Markdown(children="""Keep datasets with mriqc data"""),
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
                        dcc.Markdown(children="""Keep datasets with physiological data"""),
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
                        dcc.Markdown(children="""Keep only datasets with particpants.tsv."""),
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
        dash_table.DataTable(page_size=15, id="table"),
        # dcc.Graph(id="nb-subjects-histogram-content"),
        # dcc.Graph(id="subject-vs-session-scatter-content"),
        # dcc.Graph(id="datatype-histogram-content"),
    ]
)


@callback(
    Output(component_id="table", component_property="data"),
    Input(component_id="datatypes", component_property="value"),
    Input(component_id="task", component_property="value"),
    Input(component_id="openneuro", component_property="value"),
    Input(component_id="frmiprep", component_property="value"),
    Input(component_id="mriqc", component_property="value"),
    Input(component_id="physio", component_property="value"),
    Input(component_id="participants", component_property="value"),
)
def update_table(
    datatypes: list[str] = KNOWN_DATATYPES,
    task: str = "",
    openneuro: None | str = None,
    fmriprep: None | str = None,
    mriqc: None | str = None,
    physio: None | str = None,
    participants: None | str = None,
) -> list[dict[Hashable, Any]]:
    filtered_df = filter_data(
        df,
        config={
            "datatypes": datatypes,
            "task": task,
            "is_openneuro": openneuro,
            "fmriprep": fmriprep,
            "mriqc": mriqc,
            "physio": physio,
            "participants": participants,
        },
    )
    save_dataset_listing(filtered_df)
    return table_to_show(filtered_df).to_dict("records")


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


# @callback(Output("nb-subjects-histogram-content", "figure"), Input("datatype-radio-item", "value"))
# def update_nb_subjects_histogram(value: int) -> figure:
#     return px.histogram(
#         df,
#         x="nb_subjects",
#         color="is_openneuro",
#         labels={
#             "nb_subjects": "number of participants",
#         },
#         nbins=300,
#     )


# @callback(
#     Output("subject-vs-session-scatter-content", "figure"), Input("datatype-radio-item", "value")
# )
# def update_subject_vs_session_scatter(value: int) -> figure:
#     return scatter_subject_vs(df, y="nb_sessions", size=None, color="source", title=None)


# @callback(Output("datatype-histogram-content", "figure"), Input("datatype-radio-item", "value"))
# def update_datatype_histogram(value: int) -> figure:
#     return datatypes_histogram(df)


def browse() -> None:
    app.run(debug=True)


if __name__ == "__main__":
    browse()
