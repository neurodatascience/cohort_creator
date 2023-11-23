"""Dash app to visualize studies."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
from dash import callback
from dash import Dash
from dash import dash_table
from dash import dcc
from dash import html
from dash import Input
from dash import Output
from matplotlib import figure

from cohort_creator._utils import known_datasets_df
from cohort_creator._utils import KNOWN_DATATYPES
from cohort_creator._utils import wrangle_data
from cohort_creator.plotting import scatter_subject_vs

# from cohort_creator.plotting import filter_data

df = wrangle_data(known_datasets_df())


def table_to_show() -> pd.DataFrame:
    # convert list to string
    df["datatypes"] = df["datatypes"].apply(lambda x: ", ".join(x))
    df["tasks"] = df["tasks"].apply(lambda x: ", ".join(x))
    # reorder columns
    cols = [
        "name",
        "nb_subjects",
        "nb_sessions",
        "datatypes",
        "tasks",
    ]
    return df[cols].copy()


app = Dash(__name__)

app.layout = html.Div(
    [
        html.H1(children="BIDS datasets", style={"textAlign": "center"}),
        html.H2(children="datatype", style={"textAlign": "left"}),
        dcc.Checklist(options=KNOWN_DATATYPES, value=KNOWN_DATATYPES, id="datatype-radio-item"),
        html.H2(children="has participants.tsv", style={"textAlign": "left"}),
        dcc.RadioItems(
            options=["true", "false", "both"], value="both", id="participants-tsv-radio-item"
        ),
        html.H2(children="fmriprep", style={"textAlign": "left"}),
        dcc.RadioItems(options=["true", "false", "both"], value="both", id="frmiprep-radio-item"),
        html.H2(children="mriqc", style={"textAlign": "left"}),
        dcc.RadioItems(options=["true", "false", "both"], value="both", id="mriqc-radio-item"),
        dash_table.DataTable(data=table_to_show().to_dict("records"), page_size=10),
        dcc.Graph(id="nb-subjects-histogram-content"),
        dcc.Graph(id="subject-vs-session-scatter-content"),
    ]
)


@callback(Output("nb-subjects-histogram-content", "figure"), Input("datatype-radio-item", "value"))
def update_nb_subjects_histogram(value: int) -> figure:
    return px.histogram(
        df,
        x="nb_subjects",
        labels={
            "nb_subjects": "number of participants",
        },
    )


@callback(
    Output("subject-vs-session-scatter-content", "figure"), Input("datatype-radio-item", "value")
)
def update_subject_vs_session_scatter(value: int) -> figure:
    return scatter_subject_vs(df, y="nb_sessions", size=None, color="source", title=None)


@callback(Output("datatype-historgram-content", "figure"), Input("datatype-radio-item", "value"))
def update_datatype_histogram(value: int) -> figure:
    return px.histogram(
        df,
        x="datatypes",
        category_orders=dict(content=table_to_show()["datatypes"].unique().tolist()),
    )


if __name__ == "__main__":
    app.run(debug=True)
