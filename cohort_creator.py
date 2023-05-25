import logging
from pathlib import Path

import pandas as pd
from datalad import api
from rich import print
from rich.logging import RichHandler

LOG_LEVEL = "WARNING"


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
    openneuro = pd.read_csv(input_dir / "openneuro_derivatives.tsv", sep="\t")

    install_datasets(datasets, openneuro, sourcedata)


def install_datasets(
    datasets: pd.DataFrame, openneuro: pd.DataFrame, sourcedata: Path
):
    for dataset_ in datasets["DatasetName"]:
        mask = openneuro.name == dataset_

        if mask.sum() == 0:
            print(f"{dataset_} not found in openneuro")
            continue

        dataset_df = openneuro[mask]
        print(f"\n{dataset_}")

        if (sourcedata / dataset_).exists():
            print(f" raw data already present at {sourcedata / dataset_}")
        else:
            print(f" Cloning raw data at: {sourcedata / dataset_}")
            raw_uri = dataset_df.raw.values[0]
            api.install(path=sourcedata / dataset_, source=raw_uri)

        if frmirprep_uri := dataset_df.fmriprep.values[0]:
            if (sourcedata / f"{dataset_}-fmriprep").exists():
                print(
                    f" fmriprep data already present at {sourcedata / dataset_}"
                )
            else:
                print(
                    f" Cloning raw data at: {sourcedata / dataset_}-fmriprep"
                )
                api.install(
                    path=sourcedata / f"{dataset_}-fmriprep",
                    source=frmirprep_uri,
                )


if __name__ == "__main__":
    main()
