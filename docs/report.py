"""Print a small report about the datasets that got covered."""
from __future__ import annotations

from io import TextIOWrapper
from pathlib import Path

import pandas as pd
from rich import print

from cohort_creator._utils import known_datasets_df
from cohort_creator._utils import wrangle_data


OUTPUT_FILE = Path(__file__).parent / "source" / "accessible_datasets.md"


def main() -> None:
    with open(OUTPUT_FILE, "w") as f:
        print("# Accessible datasets\n\n", file=f)
        print("## BIDS datasets\n", file=f)

        datasets = known_datasets_df()
        datasets = wrangle_data(datasets)

        # tasks = []
        # for row in datasets.iterrows():
        #     tasks.extend(row[1]["tasks"])
        # tasks = sorted(list(set(tasks)))
        # print(tasks)

        # institutions = []
        # for row in datasets.iterrows():
        #     institutions.extend(row[1]["institutions"])
        # institutions = sorted(list(set(institutions)))
        # print(institutions)

        print(
            f"Number of datasets: {len(datasets)} with {datasets.nb_subjects.sum()} subjects",
            file=f,
        )
        print(f"Total amount of data: {int(datasets['size'].sum() / 10**12)} TB", file=f)

        print("\n\n## openneuro datasets\n", file=f)

        datasets = datasets[datasets["is_openneuro"]].copy()

        print_results(datasets, file=f)


def print_results(datasets: pd.Dataframe, file: TextIOWrapper) -> None:
    print(
        f"Number of datasets: {len(datasets)} with {datasets.nb_subjects.sum()} subjects",
        file=file,
    )
    print(f"Total amount of data: {int(datasets['size'].sum() / 10**12)} TB", file=file)
    print(
        f"With participants.tsv: {datasets['useful_participants_tsv'].sum() / len(datasets) * 100:.0f} %\n",
        file=file,
    )

    datasets = has_mri(datasets)
    print(f"- {datasets['has_mri'].sum()} datasets with MRI data", file=file)
    for der in [
        "fmriprep",
        "freesurfer",
        "mriqc",
    ]:
        data_with_der = datasets[datasets[der]]
        print(
            f" - with {der}: {len(data_with_der)} ({data_with_der.nb_subjects.sum()} subjects)",
            file=file,
        )


def has_mri(datasets: pd.Dataframe) -> pd.Dataframe:
    new_col = []
    for _, row in datasets.iterrows():
        value = {"anat", "func", "dwi", "fmap", "perf"}.intersection(set(row["datatypes"]))
        if value:
            new_col.append(True)
        else:
            new_col.append(False)
    datasets["has_mri"] = new_col
    return datasets


if __name__ == "__main__":
    main()
