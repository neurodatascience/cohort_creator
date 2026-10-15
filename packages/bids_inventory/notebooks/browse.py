"""BIDS datasets dashboard, as a marimo notebook.

The same dashboard as ``bids_inventory browse``:

    marimo run packages/bids_inventory/notebooks/browse.py    # as an app
    marimo edit packages/bids_inventory/notebooks/browse.py   # to edit it

Needs: pip install './packages/bids_inventory[browse]' marimo
"""

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="full", app_title="BIDS inventory")


@app.cell
def _():
    import contextlib
    import tempfile
    from pathlib import Path

    import marimo as mo

    from bids_inventory._plotting import (
        datatypes_histogram,
        histogram_tasks,
        plot_dataset_size_vs_time,
        scatter_subject_vs,
    )
    from bids_inventory._version import version
    from bids_inventory.listing import KNOWN_DATATYPES, known_datasets_df
    from bids_inventory.wrangling import filter_data, save_dataset_listing, wrangle_data

    return (
        KNOWN_DATATYPES,
        Path,
        contextlib,
        datatypes_histogram,
        filter_data,
        histogram_tasks,
        known_datasets_df,
        mo,
        plot_dataset_size_vs_time,
        save_dataset_listing,
        scatter_subject_vs,
        tempfile,
        version,
        wrangle_data,
    )


@app.cell
def _(known_datasets_df, wrangle_data):
    df = wrangle_data(known_datasets_df())
    SOURCES = sorted(df["source"].unique().tolist())
    return SOURCES, df


@app.cell
def _(mo):
    mo.md("""
    <h1 style="text-align: center">BIDS inventory: BIDS datasets dashboard</h1>
    """)
    return


@app.cell
def _(KNOWN_DATATYPES, SOURCES, mo):
    def checklist(options: list[str]) -> mo.ui.array:
        """Checkboxes, all checked, like a dash Checklist."""
        return mo.ui.array([mo.ui.checkbox(label=x, value=True) for x in options])

    def true_false_both() -> mo.ui.radio:
        return mo.ui.radio(options=["true", "false", "both"], value="both", inline=True)

    datatypes = checklist(KNOWN_DATATYPES)
    datatypes_and_or = mo.ui.radio(options=["AND", "OR"], value="OR", inline=True)
    task = mo.ui.text(value="")
    sources = checklist(SOURCES)
    sources_and_or = mo.ui.radio(options=["AND", "OR"], value="OR", inline=True)
    fmriprep = true_false_both()
    mriqc = true_false_both()
    physio = true_false_both()
    participants = true_false_both()
    return (
        datatypes,
        datatypes_and_or,
        fmriprep,
        mriqc,
        participants,
        physio,
        sources,
        sources_and_or,
        task,
    )


@app.cell
def _(
    datatypes,
    datatypes_and_or,
    fmriprep,
    mo,
    mriqc,
    participants,
    physio,
    sources,
    sources_and_or,
    task,
):
    def section(title: str, description: str | None, *elements: object) -> mo.Html:
        return mo.vstack(
            [mo.md(f"## {title}"), *([mo.md(description)] if description else []), *elements]
        )

    mo.vstack(
        [
            section(
                "datatypes",
                "Keep datasets for specific datatypes",
                mo.hstack(
                    [mo.vstack(list(datatypes)), datatypes_and_or],
                    justify="start",
                    align="start",
                ),
            ),
            section("task", None, task),
            section(
                "sources",
                "Keep datasets from...",
                mo.hstack(
                    [mo.vstack(list(sources)), sources_and_or], justify="start", align="start"
                ),
            ),
            mo.hstack(
                [
                    section("fmriprep", "Keep datasets with fmriprep data", fmriprep),
                    section("mriqc", "Keep datasets with mriqc data", mriqc),
                    section("physio", "Keep datasets with physiological data", physio),
                    section(
                        "participants", "Keep only datasets with participants.tsv.", participants
                    ),
                ],
                justify="space-between",
            ),
        ]
    )
    return


@app.cell
def _(
    KNOWN_DATATYPES,
    SOURCES,
    datatypes,
    datatypes_and_or,
    df,
    filter_data,
    fmriprep,
    mriqc,
    participants,
    physio,
    sources,
    sources_and_or,
    task,
):
    filtered_df = filter_data(
        df,
        config={
            "datatypes": [x for x, keep in zip(KNOWN_DATATYPES, datatypes.value) if keep],
            "datatypes_and_or": datatypes_and_or.value,
            "sources": [x for x, keep in zip(SOURCES, sources.value) if keep],
            "sources_and_or": sources_and_or.value,
            "task": task.value,
            "fmriprep": fmriprep.value,
            "mriqc": mriqc.value,
            "physio": physio.value,
            "participants": participants.value,
        },
    )
    return (filtered_df,)


@app.cell
def _(Path, contextlib, filtered_df, mo, save_dataset_listing, tempfile):
    def table_to_show(dataframe):
        sub_df = dataframe[["name", "nb_subjects", "nb_sessions", "datatypes", "tasks"]].copy()
        # convert list to string
        sub_df["datatypes"] = sub_df["datatypes"].apply(lambda x: ", ".join(x))
        sub_df["tasks"] = sub_df["tasks"].apply(lambda x: ", ".join(x))
        return sub_df

    def dataset_listing() -> bytes:
        """Return the datasets_results.tsv that 'bids_inventory browse' saves."""
        with tempfile.TemporaryDirectory() as tmp_dir, contextlib.chdir(tmp_dir):
            save_dataset_listing(filtered_df.copy())
            return (Path(tmp_dir) / "datasets_results.tsv").read_bytes()

    mo.vstack(
        [
            mo.md("---"),
            mo.ui.table(
                table_to_show(filtered_df),
                page_size=15,
                selection=None,
                show_column_summaries=False,
            ),
            mo.download(
                data=dataset_listing,
                filename="datasets_results.tsv",
                label=f"Download the listing of the {len(filtered_df)} datasets",
            ),
        ]
    )
    return


@app.cell
def _(datatypes_histogram, filtered_df, mo):
    mo.vstack([mo.md("---"), datatypes_histogram(filtered_df)])
    return


@app.cell
def _(mo):
    subject_vs = mo.ui.radio(
        options=["number of tasks", "mean size per subject", "mean duration per subject"],
        value="number of tasks",
        inline=True,
    )
    return (subject_vs,)


@app.cell
def _(filtered_df, mo, scatter_subject_vs, subject_vs):
    y_columns = {
        "number of tasks": "nb_tasks",
        "mean size per subject": "mean_size",
        "mean duration per subject": "total_duration",
    }
    mo.vstack(
        [
            mo.md("---"),
            scatter_subject_vs(
                filtered_df,
                y=y_columns[subject_vs.value],
                size=None,
                color="source",
                title=f"{subject_vs.value} VS number of participants",
            ),
            mo.hstack([subject_vs], justify="center"),
        ]
    )
    return


@app.cell
def _(filtered_df, histogram_tasks, mo):
    mo.vstack([mo.md("---"), histogram_tasks(filtered_df)])
    return


@app.cell
def _(filtered_df, mo, plot_dataset_size_vs_time):
    mo.vstack([mo.md("---"), plot_dataset_size_vs_time(filtered_df)])
    return


@app.cell
def _(mo, version):
    mo.md(f"""
    bids_inventory version: {version}

    [Github repo](https://github.com/neurodatascience/cohort_creator.git)

    Dashboard maintained by the [origami lab](https://neurodatascience.github.io/)

    [Report a BUG](https://github.com/neurodatascience/cohort_creator/issues/new?assignees=&labels=bug&projects=&template=bug_report.yml&title=%5BBUG%5D+)
    """)
    return


if __name__ == "__main__":
    app.run()
