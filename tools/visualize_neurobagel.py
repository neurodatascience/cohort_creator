"""Plot basic visualization of the content of the opendata neurobagel graph.

Only concerns openneuro for now.

Required inuput:
- participant-level-results.tsv for the whole neurobagel graph
  that can be obtained by running an empty query in
  https://query.neurobagel.org/
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from matplotlib import figure
from rich import print


def summary(df: pd.DataFrame) -> None:
    print(f"number participants: {len(df)}")
    print(
        f"number female: {sum(df['Sex'] == 'F')} ({sum(df['Sex'] == 'F') / len(df) * 100 :0.2f})"
    )
    print(f"Total missing Age value: {sum(df['missing_age'])}")
    print(f"Total missing Sex value: {sum(df['missing_sex'])}")


def wrangle(df: pd.DataFrame) -> pd.DataFrame:
    # remove protected
    mask = df["Age"] != "protected"
    df = df[mask]

    df = df.replace("http://purl.bioontology.org/ontology/SNOMEDCT/248153007", "M")
    df = df.replace("http://purl.bioontology.org/ontology/SNOMEDCT/248152002", "F")
    #  I for intersex
    df = df.replace("http://purl.bioontology.org/ontology/SNOMEDCT/32570681000036106", "I")
    df = df.replace(".*stardog.*", "", regex=True)

    df["Age"] = df["Age"].astype(float)

    # remove duplicates
    record_ID = df["DatasetID"] + df["SubjectID"]
    present = []
    mask = []
    for i in record_ID:
        if i in present:
            mask.append(False)
        else:
            mask.append(True)
            present.append(i)
    df = df[mask]

    df["dataset_name"] = df["SessionPath"].apply(lambda x: x.split("/")[1])

    df["missing_age"] = df["Age"].isnull()

    df["missing_sex"] = df["Sex"].isnull()

    return df


def plot_missing(df: pd.DataFrame, column: str) -> None:
    missing_df = df.groupby("dataset_name", as_index=False)[column].mean()
    missing_df[column] = missing_df[column] * 100
    missing_df = missing_df[missing_df[column] != 0]

    fig = bar_plot_per_dataset(df, column)
    fig.show()


def bar_plot_per_dataset(df: pd.DataFrame, column: str) -> figure:
    df = df.sort_values(by=column)
    return px.bar(
        df,
        x="dataset_name",
        y=column,
        labels={
            "dataset_name": "dataset",
            "missing_age": "percentage age value missing",
            "missing_sex": "percentage sex value missing",
            "F_to_M_ratio": "F / M ratio",
        },
    )


input_file = Path(__file__).parent / "participant-level-results.tsv"

df = pd.read_csv(input_file, sep="\t")

df = wrangle(df)

df.to_csv("tmp.tsv", sep="\t")

summary(df)

plot_missing(df, "missing_age")

plot_missing(df, "missing_sex")

sex_df = df[df.Sex.notna()]

summary(sex_df)

# plot F / M ratio for each dataset
sex_df = sex_df.groupby(["dataset_name"], as_index=False).agg(
    nb_subjects=pd.NamedAgg(column="SubjectID", aggfunc="count"),
    F_to_M_ratio=pd.NamedAgg(column="Sex", aggfunc=lambda x: sum(x == "F") / len(x)),
)

fig = bar_plot_per_dataset(sex_df, column="F_to_M_ratio")
fig.show()

# plot F / M ratio VS nb subjects for each dataset
fig = px.scatter(
    sex_df,
    x="nb_subjects",
    y="F_to_M_ratio",
    hover_name="dataset_name",
    labels={
        "dataset_name": "dataset",
        "nb_subjects": "nb subjects",
        "F_to_M_ratio": "F / M ratio",
    },
)

# fig.show()

df_with_age = df[df.Age.notna()]

summary(df_with_age)

nb_datasets = len(set(df["dataset_name"].to_list()))

fig = px.histogram(
    df_with_age.round(),
    x="Age",
    color="Sex",
    title=f"Age distribution ({nb_datasets} MRI datasets from openneuro)",
)

# fig.show()

fig = go.Figure()
fig.add_trace(go.Histogram(x=df[df["Sex"] == "F"].round()["Age"]))
fig.add_trace(go.Histogram(x=df[df["Sex"] == "M"].round()["Age"]))

# Overlay both histograms
fig.update_layout(barmode="overlay")
# Reduce opacity to see both histograms
fig.update_traces(opacity=0.75)

fig.show()
