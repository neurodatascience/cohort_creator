"""Install a set of datalad datasets from openneuro and get the data for a set of participants.

Then copy the data to a new directory structure to create a "cohort".

"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pandas as pd
from datalad import api
from datalad.support.exceptions import (
    IncompleteResultsError,
)
from rich import print
from rich.logging import RichHandler

from utils import get_sessions

DATASET_LISTING_FILENAME = "datasets_with_mriqc.tsv"  # "datasets.tsv"
PARTICIPANT_LISTING_FILENAME = "participants_with_mriqc.tsv"  # "participants.tsv"

DATA_TYPES = ["anat"]
TASKS = ["*"]  # TODO: implement filtering by task
SUFFIX = ["T1w"]
EXT = "nii.gz"
DATASET_TYPES = ["raw", "mriqc"]  # raw, mriqc, fmriprep, freesurfer
SPACE = "MNI152NLin2009cAsym"  # for fmriprep only

LOG_LEVEL = "WARNING"

NB_JOBS = 6


def cc_logger(log_level: str = "INFO") -> logging.Logger:
    FORMAT = "%(message)s"

    logging.basicConfig(
        level=log_level,
        format=FORMAT,
        datefmt="[%X]",
        handlers=[RichHandler()],
    )

    return logging.getLogger("cohort_creator")


def main() -> None:
    cc_log = cc_logger()
    cc_log.setLevel(LOG_LEVEL)

    logging.getLogger("datalad").setLevel(logging.WARNING)

    root_dir = Path(__file__).parent

    input_dir = root_dir / "inputs"

    ouput_dir = root_dir / "outputs"
    sourcedata = ouput_dir / "sourcedata"
    sourcedata.mkdir(exist_ok=True, parents=True)

    datasets = pd.read_csv(input_dir / DATASET_LISTING_FILENAME, sep="\t")
    participants = pd.read_csv(input_dir / PARTICIPANT_LISTING_FILENAME, sep="\t")
    openneuro = pd.read_csv(input_dir / "openneuro_derivatives.tsv", sep="\t")

    install_datasets(datasets, openneuro, sourcedata)

    get_data(datasets, sourcedata, participants)

    construct_cohort(datasets, ouput_dir, sourcedata, participants)


def install_datasets(datasets: pd.DataFrame, openneuro: pd.DataFrame, sourcedata: Path) -> None:
    print_step_name("Installing datasets")

    for dataset_ in datasets["DatasetName"]:
        print_dataset_name(dataset_)

        mask = openneuro.name == dataset_
        if mask.sum() == 0:
            print(f"  {dataset_} not found in openneuro")
            continue
        dataset_df = openneuro[mask]

        for dataset_type in DATASET_TYPES:
            derivative = None if dataset_type == "raw" else dataset_type

            data_pth = dataset_path(sourcedata, dataset_, derivative=derivative)

            if data_pth.exists():
                print(f"  {dataset_type} data already present at {data_pth}")
            else:
                print(f"  installing {dataset_type} data at: {data_pth}")
                if uri := dataset_df[dataset_type].values[0]:
                    api.install(path=data_pth, source=uri)


def get_data(datasets: pd.DataFrame, sourcedata: Path, participants: pd.DataFrame) -> None:
    print_step_name("Getting data")

    for dataset_ in datasets["DatasetName"]:
        print_dataset_name(dataset_)

        participants_ids = get_participant_ids(participants, dataset_)
        if not participants_ids:
            print(f"  no participants in dataset {dataset_}")
            continue

        print(f"  getting data for: {participants_ids}")

        for dataset_type in DATASET_TYPES:
            print_dataset_type(dataset_type)

            derivative = None if dataset_type == "raw" else dataset_type

            extension_list = ["json"] if dataset_type == "mriqc" else [EXT, "json"]

            data_pth = dataset_path(sourcedata, dataset_, derivative=derivative)

            dl_dataset = api.Dataset(data_pth)

            for subject in participants_ids:
                sessions = get_sessions(participants, dataset_, subject)
                get_data_this_subject(
                    subject=subject,
                    sessions=sessions,
                    data_type_list=DATA_TYPES,
                    suffix_list=SUFFIX,
                    extension_list=extension_list,
                    dataset_type=dataset_type,
                    data_pth=data_pth,
                    dl_dataset=dl_dataset,
                )


def get_data_this_subject(
    subject: str,
    sessions: list[str | None],
    data_type_list: list[str],
    suffix_list: list[str],
    extension_list: list[str],
    dataset_type: str,
    data_pth: Path,
    dl_dataset: api.Dataset,
) -> None:
    for session_ in sessions:
        for data_type in data_type_list:
            for suffix in suffix_list:
                for ext in extension_list:
                    glob_pattern = create_glob_pattern(dataset_type, suffix=suffix, ext=ext)

                    # TODO handle session level
                    files = list_files_for_subject(
                        data_pth,
                        subject,
                        session=session_,
                        data_type=data_type,
                        glob_pattern=glob_pattern,
                    )
                    if not files:
                        print(
                            f"    no files found for: {subject} - {session_} - {data_type} - {suffix} - {ext}"
                        )
                        continue
                    print(f"    {subject} - getting files:\n     {files}")
                    try:
                        dl_dataset.get(path=files, jobs=NB_JOBS)
                    except IncompleteResultsError:
                        print(f"    {subject} - failed to get files:\n     {files}")


def construct_cohort(
    datasets: pd.DataFrame, ouput_dir: Path, sourcedata: Path, participants: pd.DataFrame
) -> None:
    print_step_name("Constructing cohort")

    for dataset_ in datasets["DatasetName"]:
        print_dataset_name(dataset_)

        for dataset_type in DATASET_TYPES:
            print_dataset_type(dataset_type)

            derivative = None if dataset_type == "raw" else dataset_type

            extension_list = ["json"] if dataset_type == "mriqc" else [EXT, "json"]

            src_dir = dataset_path(sourcedata, dataset_, derivative=derivative)
            target_dir = dataset_path(ouput_dir, dataset_, derivative=derivative)

            target_dir.mkdir(exist_ok=True, parents=True)

            shutil.copy(
                src=(src_dir / "dataset_description.json"), dst=target_dir, follow_symlinks=True
            )

            participants_ids = get_participant_ids(participants, dataset_)
            if not participants_ids:
                print(f"  no participants in dataset {dataset_}")
                continue

            for subject in participants_ids:
                sessions = get_sessions(participants, dataset_, subject)
                copy_this_subject(
                    subject=subject,
                    sessions=sessions,
                    data_type_list=DATA_TYPES,
                    suffix_list=SUFFIX,
                    extension_list=extension_list,
                    dataset_type=dataset_type,
                    src_dir=src_dir,
                    target_dir=target_dir,
                )


def copy_this_subject(
    subject: str,
    sessions: list[str | None],
    data_type_list: list[str],
    suffix_list: list[str],
    extension_list: list[str],
    dataset_type: str,
    src_dir: Path,
    target_dir: Path,
) -> None:
    for session_ in sessions:
        for data_type in data_type_list:
            for suffix in suffix_list:
                for ext in extension_list:
                    glob_pattern = create_glob_pattern(dataset_type, suffix=suffix, ext=ext)

                    files = list_files_for_subject(
                        data_pth=src_dir,
                        subject=subject,
                        session=session_,
                        data_type=data_type,
                        glob_pattern=glob_pattern,
                    )
                    if not files:
                        print(
                            f"    no files found for: {subject} - {session_} - {data_type} - {suffix} - {ext}"
                        )
                        continue

                    print(f"    {subject} - copying files:\n     {files}")
                    for f in files:
                        sub_dirs = Path(f).parents
                        (target_dir / sub_dirs[0]).mkdir(exist_ok=True, parents=True)
                        if (target_dir / f).exists():
                            print(f"      file '{f}' already present")
                            continue
                        try:
                            shutil.copy(src=src_dir / f, dst=target_dir / f, follow_symlinks=True)
                            # TODO deal with permission
                        except FileNotFoundError:
                            print(f"      Could not find file '{f}'")


def dataset_path(root: Path, dataset_: str, derivative: str | None = None) -> Path:
    if derivative is None:
        return root / dataset_
    name = f"{dataset_}-{derivative}"
    return (root / dataset_).with_name(name)


def get_participant_ids(participants: pd.DataFrame, dataset_name: str) -> list[str] | None:
    mask = participants["DatasetName"] == dataset_name
    if mask.sum() == 0:
        print(f"  no participants in dataset {dataset_name}")
        return None
    participants_df = participants[mask]
    return participants_df["SubjectID"].tolist()


def list_files_for_subject(
    data_pth: Path, subject: str, session: str | None, data_type: str, glob_pattern: str
) -> list[str]:
    """Return a list of files for a participant with path relative to data_pth."""
    if not session:
        files = (data_pth / subject / data_type).glob(glob_pattern)
    else:
        files = (data_pth / subject / f"ses-{session}" / data_type).glob(glob_pattern)
    return [str(f.relative_to(data_pth)) for f in files]


def create_glob_pattern(dataset_type: str, suffix: str, ext: str) -> str:
    return f"*_{suffix}.{ext}" if dataset_type in {"raw", "mriqc"} else f"*{SPACE}*_{suffix}.{ext}"


def print_step_name(name: str) -> None:
    print(f"\n[green] {name.upper()} [/green]")


def print_dataset_name(name: str) -> None:
    print(f"\n[blue]  {name.upper()} [/blue]")


def print_dataset_type(name: str) -> None:
    print(f"\n[yellow]   {name.upper()} [/yellow]")


if __name__ == "__main__":
    main()
