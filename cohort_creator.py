"""Install a set of datalad datasets from openneuro and get the data for a set of participants.

Then copy the data to a new directory structure to create a "cohort".
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pandas as pd
from datalad import api
from rich import print
from rich.logging import RichHandler

LOG_LEVEL = "WARNING"

NB_JOBS = 6

SPACE = "MNI152NLin2009cAsym"
DATA_TYPE = "anat"
SUFFIX = ["T1w"]
EXT = "nii.gz"
DATASET_TYPES = ["raw", "fmriprep"]


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
    # cc_log = cc_logger()
    # cc_log.setLevel(LOG_LEVEL)
    # cc_log.propagate = False

    root_dir = Path(__file__).parent

    input_dir = root_dir / "inputs"

    ouput_dir = root_dir / "outputs"
    sourcedata = ouput_dir / "sourcedata"
    sourcedata.mkdir(exist_ok=True, parents=True)

    datasets = pd.read_csv(input_dir / "datasets.tsv", sep="\t")
    participants = pd.read_csv(input_dir / "participants.tsv", sep="\t")
    openneuro = pd.read_csv(input_dir / "openneuro_derivatives.tsv", sep="\t")

    install_datasets(datasets, openneuro, sourcedata)

    get_data(datasets, sourcedata, participants)

    construct_cohort(datasets, ouput_dir, sourcedata, participants)


def install_datasets(datasets: pd.DataFrame, openneuro: pd.DataFrame, sourcedata: Path) -> None:
    print("\nInstalling datasets")

    for dataset_ in datasets["DatasetName"]:
        print(f"\n {dataset_}")

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
    print("\nGetting data")

    for dataset_ in datasets["DatasetName"]:
        print(f"\n {dataset_}")

        participants_ids = get_participant_ids(participants, dataset_)
        if not participants_ids:
            print(f"  no participants in dataset {dataset_}")
            continue

        print(f"  getting data for: {participants_ids}")

        for dataset_type in DATASET_TYPES:
            print(f"   {dataset_type}")

            derivative = None if dataset_type == "raw" else dataset_type

            data_pth = dataset_path(sourcedata, dataset_, derivative=derivative)

            dl_dataset = api.Dataset(data_pth)

            for participant in participants_ids:
                for suffix in SUFFIX:
                    for ext in [EXT, "json"]:
                        glob_pattern = create_glob_pattern(dataset_type, suffix=suffix, ext=ext)
                        # TODO handle session level
                        files = list_files_for_participant(data_pth, participant, glob_pattern)
                        if not files:
                            print(f"    no files found for: {str(participant)}")
                            continue
                        print(f"    {str(participant)} - getting files:\n     {list(files)}")
                        dl_dataset.get(path=files, jobs=NB_JOBS)


def construct_cohort(
    datasets: pd.DataFrame, ouput_dir: Path, sourcedata: Path, participants: pd.DataFrame
) -> None:
    print("\nConstructing cohort")

    for dataset_ in datasets["DatasetName"]:
        print(f"\n {dataset_}")

        for dataset_type in DATASET_TYPES:
            print(f"   {dataset_type}")

            derivative = None if dataset_type == "raw" else dataset_type

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

            for participant in participants_ids:
                for suffix in SUFFIX:
                    for ext in [EXT, "json"]:
                        glob_pattern = create_glob_pattern(dataset_type, suffix=suffix, ext=ext)
                        files = list_files_for_participant(src_dir, participant, glob_pattern)
                        if not files:
                            print(f"    no files found for: {str(participant)}")
                            continue
                        print(f"    {str(participant)} - copying files:\n     {list(files)}")
                        for f in files:
                            sub_dirs = Path(f).parents
                            (target_dir / sub_dirs[0]).mkdir(exist_ok=True, parents=True)
                            if (target_dir / f).exists():
                                print(f"      file '{f}' already present")
                                continue
                            shutil.copy(src=src_dir / f, dst=target_dir / f, follow_symlinks=True)
                            # TODO deal with permission


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


def list_files_for_participant(data_pth: Path, participant: str, glob_pattern: str) -> list[str]:
    """Return a list of files for a participant with path relative to data_pth."""
    files = (data_pth / participant / DATA_TYPE).glob(glob_pattern)
    return [str(f.relative_to(data_pth)) for f in files]


def create_glob_pattern(dataset_type: str, suffix: str, ext: str) -> str:
    return f"*_{suffix}.{ext}" if dataset_type == "raw" else f"*{SPACE}*_{suffix}.{ext}"


if __name__ == "__main__":
    main()
