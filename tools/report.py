"""Print a small report about the datasets that got covered."""
from __future__ import annotations

import pandas as pd
from rich import print

from cohort_creator._utils import listify
from cohort_creator._utils import openneuro_df


def main() -> None:
    print("**OpenNeuro datasets:**\n")
    datasets = openneuro_df()
    datasets.fillna(False, inplace=True)
    print_results(datasets)


def print_results(datasets: pd.Dataframe) -> None:
    print(
        f"Number of datasets: {len(datasets)} with {datasets.nb_subjects.sum()} subjects including:"
    )
    datasets = has_mri(datasets)
    print(f"- {datasets['has_mri'].sum()} datasets with MRI data")
    mask = datasets.has_mri
    data_with_mri = datasets[mask]
    print(f" - with participants.tsv: {data_with_mri.has_participant_tsv.sum()} ")
    print(f" - with phenotype directory: {data_with_mri.has_phenotype_dir.sum()}")
    for der in [
        "fmriprep",
        "freesurfer",
        "mriqc",
    ]:
        mask = datasets[der] != False  # noqa
        data_with_der = datasets[mask]
        print(f" - with {der}: {(mask).sum()} ({data_with_der.nb_subjects.sum()} subjects)")
        print(f"   - with participants.tsv: {data_with_der.has_participant_tsv.sum()}")
        print(f"   - with phenotype directory: {data_with_der.has_phenotype_dir.sum()}")


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
