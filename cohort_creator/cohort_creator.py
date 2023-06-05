"""Install a set of datalad datasets from openneuro and get the data for a set of participants.

Then copy the data to a new directory structure to create a "cohort".

"""
from __future__ import annotations

import itertools
import shutil
from pathlib import Path

import pandas as pd
from datalad import api
from datalad.support.exceptions import (
    IncompleteResultsError,
)

from cohort_creator._utils import _is_dataset_in_openneuro
from cohort_creator._utils import add_study_tsv
from cohort_creator._utils import copy_top_files
from cohort_creator._utils import create_ds_description
from cohort_creator._utils import dataset_path
from cohort_creator._utils import filter_excluded_participants
from cohort_creator._utils import get_dataset_url
from cohort_creator._utils import get_participant_ids
from cohort_creator._utils import get_sessions
from cohort_creator._utils import is_subject_in_dataset
from cohort_creator._utils import list_all_files
from cohort_creator._utils import no_files_found_msg
from cohort_creator._utils import return_target_pth
from cohort_creator.bagelify import _new_bagel
from cohort_creator.bagelify import bagelify
from cohort_creator.logger import cc_logger


cc_log = cc_logger()


def install_datasets(datasets: list[str], sourcedata: Path, dataset_types: list[str]) -> None:
    """Will install several datalad datasets from openneuro.

    Parameters
    ----------
    datasets : list[str]
        List of dataset names.

        Example: ``["ds000001", "ds000002"]``

    sourcedata : Path
        Path where the datasets will be installed.

    dataset_types : list[str]
        Can contain any of: ``"raw"``, ``"fmriprep"``, ``"mriqc"``.

    """
    cc_log.info("Installing datasets")
    for dataset_ in datasets:
        cc_log.info(f" {dataset_}")
        _install(dataset_name=dataset_, dataset_types=dataset_types, output_path=sourcedata)


def _install(dataset_name: str, dataset_types: list[str], output_path: Path) -> None:
    if not _is_dataset_in_openneuro(dataset_name):
        cc_log.warning(f"  {dataset_name} not found in openneuro")
        return None

    for dataset_type_ in dataset_types:
        if not get_dataset_url(dataset_name, dataset_type_):
            cc_log.debug(f"      no {dataset_type_} for {dataset_name}")
            continue

        derivative = None if dataset_type_ == "raw" else dataset_type_
        data_pth = dataset_path(output_path, dataset_name, derivative=derivative)

        if data_pth.exists():
            cc_log.debug(f"  {dataset_type_} data already present at {data_pth}")
        else:
            cc_log.info(f"    installing {dataset_type_} data at: {data_pth}")
            if uri := get_dataset_url(dataset_name, dataset_type_):
                api.install(path=data_pth, source=uri)


def get_data(
    datasets: pd.DataFrame,
    sourcedata: Path,
    participants: pd.DataFrame,
    dataset_types: list[str],
    datatypes: list[str],
    space: str,
    jobs: int,
) -> None:
    """Get the data for specified participants / datatypes / space \
    from preinstalled datalad datasets / dataset_types.

    Parameters
    ----------
    datasets : pd.DataFrame

    sourcedata : Path

    participants : pd.DataFrame

    dataset_types : list[str]
        Can contain any of: ``"raw"``, ``"fmriprep"``, ``"mriqc"``.

    datatypes : list[str]
        Can contain any of: ``"anat'``, ``"func"``

    space : str
        Space of the data to get (only applies when dataset_types requested includes fmriprep).

    jobs : int
        Number of jobs to use for parallelization during datalad get operation.

    """
    cc_log.info("Getting data")

    if isinstance(datatypes, str):
        datatypes = [datatypes]

    for dataset_ in datasets["DatasetName"]:
        cc_log.info(f" {dataset_}")

        participants_ids = get_participant_ids(participants, dataset_)
        if not participants_ids:
            cc_log.warning(f"  no participants in dataset {dataset_}")
            continue

        cc_log.info(f"  getting data for: {participants_ids}")

        for dataset_type_ in dataset_types:
            if not get_dataset_url(dataset_, dataset_type_):
                cc_log.debug(f"      no {dataset_type_} for {dataset_}")
                continue
            cc_log.info(f"  {dataset_type_}")

            derivative = None if dataset_type_ == "raw" else dataset_type_
            data_pth = dataset_path(sourcedata, dataset_, derivative=derivative)

            dl_dataset = api.Dataset(data_pth)

            for subject in participants_ids:
                if not is_subject_in_dataset(subject, data_pth):
                    cc_log.debug(f"  no participant {subject} in dataset {dataset_}")
                    continue
                sessions = get_sessions(participants, dataset_, subject)
                _get_data_this_subject(
                    subject=subject,
                    sessions=sessions,
                    datatypes=datatypes,
                    space=space,
                    dataset_type=dataset_type_,
                    data_pth=data_pth,
                    dl_dataset=dl_dataset,
                    jobs=jobs,
                )


def _get_data_this_subject(
    subject: str,
    sessions: list[str] | list[None],
    datatypes: list[str],
    space: str,
    dataset_type: str,
    data_pth: Path,
    dl_dataset: api.Dataset,
    jobs: int,
) -> None:
    for datatype_ in datatypes:
        files = list_all_files(
            data_pth=data_pth,
            dataset_type=dataset_type,
            subject=subject,
            sessions=sessions,
            datatype=datatype_,
            space=space,
        )
        if not files:
            cc_log.warning(no_files_found_msg(subject, datatype_))
            continue
        cc_log.debug(f"    {subject} - getting files:\n     {files}")
        try:
            dl_dataset.get(path=files, jobs=jobs)
        except IncompleteResultsError:
            cc_log.error(f"    {subject} - failed to get files:\n     {files}")


def construct_cohort(
    datasets: pd.DataFrame,
    output_dir: Path,
    sourcedata_dir: Path,
    participants: pd.DataFrame,
    dataset_types: list[str],
    datatypes: list[str],
    space: str,
) -> None:
    """Copy the data from sourcedata_dir to output_dir, to create a cohort.

    Parameters
    ----------
    datasets : pd.DataFrame

    output_dir : Path

    sourcedata_dir : Path

    participants : pd.DataFrame

    dataset_types : list[str]
        Can contain any of: ``"raw"``, ``"fmriprep"``, ``"mriqc"``.

    datatypes : list[str]
        Can contain any of: ``"anat'``, ``"func"``

    space : str
        Space of the data to get (only applies when dataset_types requested includes fmriprep).

    """
    cc_log.info("Constructing cohort")

    create_ds_description(output_dir)

    with open(output_dir / "README.md", "w") as f:
        f.write("# README\n\n")

    for dataset_ in datasets["DatasetName"]:
        cc_log.info(f" {dataset_}")

        participants_ids = get_participant_ids(participants, dataset_)
        if not participants_ids:
            cc_log.warning(f"  no participants in dataset {dataset_}")
            continue

        cc_log.info(f"  creating cohort with: {participants_ids}")

        for dataset_type_ in dataset_types:
            if not get_dataset_url(dataset_, dataset_type_):
                cc_log.debug(f"      no {dataset_type_} for {dataset_}")
                continue
            cc_log.info(f"  {dataset_type_}")

            derivative = None if dataset_type_ == "raw" else dataset_type_
            src_pth = dataset_path(sourcedata_dir, dataset_, derivative=derivative)

            target_pth = return_target_pth(output_dir, dataset_type_, dataset_, src_pth)
            target_pth.mkdir(exist_ok=True, parents=True)

            copy_top_files(src_pth=src_pth, target_pth=target_pth, datatypes=datatypes)
            filter_excluded_participants(pth=target_pth, participants=participants_ids)

            for subject in participants_ids:
                if not is_subject_in_dataset(subject, src_pth):
                    cc_log.debug(f"  no participant {subject} in dataset {dataset_}")
                    continue
                sessions = get_sessions(participants, dataset_, subject)
                _copy_this_subject(
                    subject=subject,
                    sessions=sessions,
                    datatypes=datatypes,
                    dataset_type=dataset_type_,
                    space=space,
                    src_pth=src_pth,
                    target_pth=target_pth,
                )

    add_study_tsv(output_dir, datasets)

    _generate_bagel_for_cohort(
        output_dir=output_dir,
        sourcedata_dir=sourcedata_dir,
        datasets=datasets,
        dataset_types=dataset_types,
    )


def _copy_this_subject(
    subject: str,
    sessions: list[str] | list[None],
    datatypes: list[str],
    dataset_type: str,
    space: str,
    src_pth: Path,
    target_pth: Path,
) -> None:
    for datatype_ in datatypes:
        files = list_all_files(
            data_pth=src_pth,
            dataset_type=dataset_type,
            subject=subject,
            sessions=sessions,
            datatype=datatype_,
            space=space,
        )
        if not files:
            cc_log.warning(no_files_found_msg(subject, datatype_))
            continue

        cc_log.debug(f"    {subject} - copying files:\n     {files}")
        for f in files:
            sub_dirs = Path(f).parents
            (target_pth / sub_dirs[0]).mkdir(exist_ok=True, parents=True)
            if (target_pth / f).exists():
                cc_log.debug(f"      file '{f}' already present")
                continue
            try:
                shutil.copy(src=src_pth / f, dst=target_pth / f, follow_symlinks=True)
                # TODO deal with permission
            except FileNotFoundError:
                cc_log.error(f"      Could not find file '{f}'")


def _generate_bagel_for_cohort(
    output_dir: Path, sourcedata_dir: Path, datasets: pd.DataFrame, dataset_types: list[str]
) -> None:
    """Track what subjects have been processed by what pipeline."""
    cc_log.info(" creating bagel.csv file")
    bagel = _new_bagel()
    supported_dataset_types = ["fmriprep", "mriqc"]
    for dataset_type_, dataset_ in itertools.product(dataset_types, datasets["DatasetName"]):
        if dataset_type_ not in supported_dataset_types:
            continue
        cc_log.info(f"  {dataset_} - {dataset_type_}")

        raw_pth = return_target_pth(output_dir, "raw", dataset_)

        src_pth = dataset_path(sourcedata_dir, dataset_, derivative=dataset_type_)
        derivative_pth = return_target_pth(output_dir, dataset_type_, dataset_, src_pth)

        bagel = bagelify(bagel, raw_pth, derivative_pth)

    df = pd.DataFrame.from_dict(bagel)
    df.to_csv(output_dir / "bagel.csv", index=False)

    cc_log.info(f"Cohort created at {output_dir}")
    cc_log.info(
        f"""Check what subjects have derivatives ready
by uploading {output_dir / "bagel.csv"} to
https://dash.neurobagel.org/
"""
    )
