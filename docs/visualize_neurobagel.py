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
    print(f"number datasets: {nb_datasets(df)}")
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


def plot_missing(df: pd.DataFrame, column: str) -> figure:
    missing_df = df.groupby("dataset_name", as_index=False)[column].mean()
    missing_df[column] = missing_df[column] * 100
    missing_df = missing_df[missing_df[column] != 0]
    missing_df = missing_df.sort_values(by=[column])

    fig = bar_plot_per_dataset(missing_df, column)
    return fig


def nb_datasets(df: pd.DataFrame) -> int:
    return len(set(df["dataset_name"].to_list()))


def bar_plot_per_dataset(df: pd.DataFrame, column: str) -> figure:
    return px.bar(
        df,
        x="dataset_name",
        y=column,
        labels={
            "dataset_name": "dataset",
            "missing_age": "percentage age value missing",
            "missing_sex": "percentage sex value missing",
            "F_to_M_ratio": "Female to Male ratio",
        },
        title=f"{column} for each dataset",
    )


def main() -> None:
    output_dir = Path(__file__).parent / "source" / "images" / "neurobagel"

    input_file = Path(__file__).parent / "participant-level-results.tsv"

    df = pd.read_csv(input_file, sep="\t")

    df = wrangle(df)

    summary(df)

    fig = plot_missing(df, "missing_age")
    fig.write_image(output_dir / "missing_age.png", scale=2, width=1000)

    plot_missing(df, "missing_sex")
    fig.write_image(output_dir / "missing_sex.png", scale=2, width=1000)

    sex_df = df[df.Sex.notna()]
    print("\nAfter removing missing sex values")
    summary(sex_df)

    # plot F / M ratio for each dataset
    sex_df = sex_df.groupby(["dataset_name"], as_index=False).agg(
        nb_subjects=pd.NamedAgg(column="SubjectID", aggfunc="count"),
        F_to_M_ratio=pd.NamedAgg(column="Sex", aggfunc=lambda x: sum(x == "F") / len(x)),
    )
    sex_df = sex_df.sort_values(by=["F_to_M_ratio"])

    fig = bar_plot_per_dataset(sex_df, column="F_to_M_ratio")
    fig.write_image(output_dir / "sex_ratio.png", scale=2, width=1000)

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
        title="sex ratio VS number of subjects for each dataset",
    )
    fig.write_image(output_dir / "subject_vs_sex_ratio.png", scale=2, width=1000)

    df_with_age = df[df.Age.notna()]
    print("\nAfter removing missing age values")
    summary(df_with_age)

    df_with_age_and_sex = df_with_age[df.Sex.notna()]
    print("\nAfter removing missing sex and age values")
    summary(df_with_age_and_sex)

    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=df_with_age_and_sex[df_with_age_and_sex["Sex"] == "F"].round()["Age"],
            name="Female",
        ),
    )
    fig.add_trace(
        go.Histogram(
            x=df_with_age_and_sex[df_with_age_and_sex["Sex"] == "M"].round()["Age"], name="Male"
        ),
    )
    fig.update_layout(
        barmode="overlay",
        title=f"Age distribution ({nb_datasets(df_with_age_and_sex)} MRI datasets from openneuro)",
        xaxis_title=dict(text="Age (years)"),
        yaxis_title=dict(text="count"),
    )
    fig.update_traces(opacity=0.8)
    fig.write_image(output_dir / "age_distribution.png", scale=2, width=1000)


if __name__ == "__main__":
    main()
