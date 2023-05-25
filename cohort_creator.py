import logging
from pathlib import Path

import pandas as pd
from datalad import api
from rich import print
from rich.logging import RichHandler

LOG_LEVEL = "WARNING"

NB_JOBS = 6

SPACE = "MNI152NLin2009cAsym"
DATA_TYPE = "anat"
SUFFIX = "T1w"
EXT = "nii.gz"
DATASET_TYPES = ["raw", "fmriprep"]


def cc_logger(log_level: str = "INFO"):
    FORMAT = "%(message)s"

    logging.basicConfig(
        level=log_level,
        format=FORMAT,
        datefmt="[%X]",
        handlers=[RichHandler()],
    )

    return logging.getLogger("cohort_creator")


def main():
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


def install_datasets(datasets: pd.DataFrame, openneuro: pd.DataFrame, sourcedata: Path):
    print("\nInstalling datasets")

    for dataset_ in datasets["DatasetName"]:
        mask = openneuro.name == dataset_

        print(f"\n {dataset_}")

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
                print(f"  cloning {dataset_type} data at: {data_pth}")
                if uri := dataset_df[dataset_type].values[0]:
                    api.install(path=data_pth, source=uri)

        # if "raw" in DATASET_TYPES:

        #     if dataset_path(sourcedata, dataset_).exists():
        #         print(f"  raw data already present at {dataset_path(sourcedata, dataset_)}")
        #     else:
        #         print(f"  cloning raw data at: {dataset_path(sourcedata, dataset_)}")
        #         raw_uri = dataset_df.raw.values[0]
        #         api.install(path=dataset_path(sourcedata, dataset_), source=raw_uri)

        # if "fmriprep" in DATASET_TYPES:
        #     if frmirprep_uri := dataset_df.fmriprep.values[0]:
        #         if dataset_path(sourcedata, dataset_, derivative="fmriprep").exists():
        #             print(
        #                 "  fmriprep data already present at "
        #                 f"{dataset_path(sourcedata, dataset_, derivative='fmriprep')}"
        #             )
        #         else:
        #             print(
        #                 f"  cloning fmriprep data at: "
        #                 f"{dataset_path(sourcedata, dataset_, derivative='fmriprep')}"
        #             )
        #             api.install(
        #                 path=dataset_path(sourcedata, dataset_, derivative="fmriprep"),
        #                 source=frmirprep_uri,
        #             )


def get_data(datasets: pd.DataFrame, sourcedata: Path, participants: pd.DataFrame):
    for dataset_ in datasets["DatasetName"]:
        mask = participants["DatasetName"] == dataset_

        participants_df = participants[mask]
        participants_ids = participants_df["SubjectID"].tolist()

        print(f"  getting data participants: {participants_ids}")

        if "raw" in DATASET_TYPES:
            print(f"\n{dataset_}")

            dl_dataset = api.Dataset(dataset_path(sourcedata, dataset_))

            for participant in participants_ids:
                files = (dataset_path(sourcedata, dataset_) / participant / DATA_TYPE).glob(
                    f"*_{SUFFIX}.{EXT}"
                )
                if not files:
                    print(f"  no files found for participant: {participant}")
                    continue
                print(f"  getting data for participant: {participant}")
                dl_dataset.get(path=files, jobs=NB_JOBS)

        if "fmriprep" in DATASET_TYPES:
            print(f"\n{dataset_}-fmriprep")

            dl_dataset = api.Dataset(dataset_path(sourcedata, dataset_, derivative="fmriprep"))

            print(f"  getting data participants: {participants_ids}")

            for participant in participants_ids:
                files = (
                    dataset_path(sourcedata, dataset_, derivative="fmriprep")
                    / participant
                    / DATA_TYPE
                ).glob(f"*{SPACE}*_{SUFFIX}.{EXT}")
                files = [
                    f.relative_to(dataset_path(sourcedata, dataset_, derivative="fmriprep"))
                    for f in files
                ]
                if not files:
                    print(f"  no files found for participant: {participant}")
                    continue
                print(
                    f"  getting data for participant: {participant}\n   {[str(f) for f in files]}"
                )
                dl_dataset.get(path=files, jobs=NB_JOBS)


def dataset_path(sourcedata: Path, dataset_: str, derivative: str | None = None):
    if derivative is None:
        return sourcedata / dataset_
    name = f"{dataset_}-{derivative}"
    return (sourcedata / dataset_).with_name(name)


if __name__ == "__main__":
    main()
