"""Print a small report about the datasets that got covered."""
from __future__ import annotations

import pandas as pd
from rich import print

from cohort_creator._utils import known_datasets_df
from cohort_creator._utils import listify
from cohort_creator._utils import wrangle_data


def main() -> None:
    print("**BIDS datasets:**\n")
    datasets = known_datasets_df()
    datasets = wrangle_data(datasets)

    print_results(datasets)

    datasets.to_csv("tmp.tsv", sep="\t")


def print_results(datasets: pd.Dataframe) -> None:
    print(f"Number of datasets: {len(datasets)} with {datasets.nb_subjects.sum()} subjects")
    print(f"Total of data: {int(datasets['size'].sum() / 10**12)} TB")
    print(datasets["has_phenotype_dir"].value_counts())
    print(f" - with phenotype directory: {datasets['has_phenotype_dir'].count()}")
    # print(f" - with participants.tsv: {sum(datasets['useful_participants_tsv']) / len(datasets) * 100} %")

    print(datasets["institutions"].value_counts())

    datasets = has_mri(datasets)
    print(f"- {datasets['has_mri'].sum()} datasets with MRI data")
    mask = datasets.has_mri
    for der in [
        "fmriprep",
        "freesurfer",
        "mriqc",
    ]:
        mask = datasets[der] != False  # noqa
        data_with_der = datasets[mask]
        print(f" - with {der}: {(mask).sum()} ({data_with_der.nb_subjects.sum()} subjects)")


def has_mri(datasets: pd.Dataframe) -> pd.Dataframe:
    new_col = []
    for _, row in datasets.iterrows():
        value = {"anat", "func", "dwi", "fmap", "perf"}.intersection(
            set(listify(row["modalities"]))
        )
        if value:
            new_col.append(True)
        else:
            new_col.append(False)
    datasets["has_mri"] = new_col
    return datasets


if __name__ == "__main__":
    main()
