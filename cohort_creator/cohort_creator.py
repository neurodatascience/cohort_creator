"""Install a set of datalad datasets from openneuro and get the data for a set of participants.

Then copy the data to a new directory structure to create a "cohort".

"""
from __future__ import annotations

import itertools
import shutil
import subprocess
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
from cohort_creator._utils import create_tsv_participant_session_in_datasets
from cohort_creator._utils import dataset_path
from cohort_creator._utils import filter_excluded_participants
from cohort_creator._utils import get_dataset_url
from cohort_creator._utils import get_filters
from cohort_creator._utils import get_list_datasets_to_install
from cohort_creator._utils import get_participant_ids
from cohort_creator._utils import get_pipeline_version
from cohort_creator._utils import get_sessions
from cohort_creator._utils import is_subject_in_dataset
from cohort_creator._utils import list_all_files_with_filter
from cohort_creator._utils import list_participants_in_dataset
from cohort_creator._utils import list_sessions_in_participant
from cohort_creator._utils import no_files_found_msg
from cohort_creator._utils import return_target_pth
from cohort_creator._utils import sourcedata
from cohort_creator.bagelify import _new_bagel
from cohort_creator.bagelify import bagelify
from cohort_creator.logger import cc_logger


cc_log = cc_logger()


def superdataset(pth: Path) -> api.Dataset:
    return api.Dataset(pth)


def install_datasets(
    datasets: list[str],
    output_dir: Path,
    dataset_types: list[str],
    generate_participant_listing: bool = False,
) -> None:
    """Will install several datalad datasets from openneuro.

    Parameters
    ----------
    datasets : list[str]
        List of dataset names.

        Example: ``["ds000001", "ds000002"]``

    output_dir : Path
        Path where the datasets will be installed.

    dataset_types : list[str]
        Can contain any of: ``"raw"``, ``"fmriprep"``, ``"mriqc"``.

    generate_participant_listing : bool, default=False
        If True, will generate a participant listing for all datasets.

    """
    cc_log.info("Installing datasets")
    for dataset_ in datasets:
        cc_log.info(f" {dataset_}")
        _install(dataset_name=dataset_, dataset_types=dataset_types, output_dir=output_dir)

    if generate_participant_listing:
        dataset_paths = [dataset_path(sourcedata(output_dir), dataset_) for dataset_ in datasets]
        create_tsv_participant_session_in_datasets(
            dataset_paths=dataset_paths, output_dir=sourcedata(output_dir)
        )


def _install(dataset_name: str, dataset_types: list[str], output_dir: Path) -> None:
    if not _is_dataset_in_openneuro(dataset_name):
        cc_log.warning(f"  {dataset_name} not found in openneuro")
        return None

    for dataset_type_ in dataset_types:
        if not get_dataset_url(dataset_name, dataset_type_):
            cc_log.debug(f"      no {dataset_type_} for {dataset_name}")
            continue

        derivative = None if dataset_type_ == "raw" else dataset_type_
        data_pth = dataset_path(sourcedata(output_dir), dataset_name, derivative=derivative)

        if data_pth.exists():
            cc_log.debug(f"  {dataset_type_} data already present at {data_pth}")
        else:
            cc_log.info(f"    installing {dataset_type_} data at: {data_pth}")
            if uri := get_dataset_url(dataset_name, dataset_type_):
                print(output_dir)
                api.install(path=data_pth, source=uri, dataset=api.Dataset(output_dir))


def get_data(
    output_dir: Path,
    datasets: pd.DataFrame,
    participants: pd.DataFrame | None,
    dataset_types: list[str],
    datatypes: list[str],
    space: str,
    jobs: int,
    bids_filter: None | dict[str, dict[str, dict[str, str]]] = None,
) -> None:
    """Get the data for specified participants / datatypes / space \
    from preinstalled datalad datasets / dataset_types.

    Parameters
    ----------
    output_dir : Path

    datasets : pd.DataFrame

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

    dataset_names = get_list_datasets_to_install(
        dataset_listing=datasets, participant_listing=participants
    )

    for dataset_ in dataset_names:
        cc_log.info(f" {dataset_}")

        # if no participants_ids then we grab all the participants
        # from the raw dataset
        if participants is not None:
            participants_ids = get_participant_ids(
                datasets=datasets, participants=participants, dataset_name=dataset_
            )
            if not participants_ids:
                cc_log.warning(f"  no participants in dataset {dataset_}")
                continue
            cc_log.info(f"  getting data for: {participants_ids}")

        else:
            data_pth = dataset_path(sourcedata(output_dir), dataset_)
            participants_ids = list_participants_in_dataset(data_pth)
            cc_log.info(f"  getting data for all participants in dataset {dataset_}")

        for dataset_type_ in dataset_types:
            if not get_dataset_url(dataset_, dataset_type_):
                cc_log.debug(f"      no {dataset_type_} for {dataset_}")
                continue
            cc_log.info(f"  {dataset_type_}")

            derivative = None if dataset_type_ == "raw" else dataset_type_
            data_pth = dataset_path(sourcedata(output_dir), dataset_, derivative=derivative)

            dl_dataset = api.Dataset(data_pth)

            for subject in participants_ids:
                if not is_subject_in_dataset(subject, data_pth):
                    cc_log.debug(f"  no participant {subject} in dataset {dataset_}")
                    continue

                if participants is not None:
                    sessions = get_sessions(participants, dataset_, subject)
                else:
                    sessions = list_sessions_in_participant(data_pth / subject)

                _get_data_this_subject(
                    subject=subject,
                    sessions=sessions,
                    datatypes=datatypes,
                    space=space,
                    dataset_type=dataset_type_,
                    data_pth=data_pth,
                    dl_dataset=dl_dataset,
                    jobs=jobs,
                    bids_filter=bids_filter,
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
    bids_filter: None | dict[str, dict[str, dict[str, str]]] = None,
) -> None:
    for datatype_ in datatypes:
        filters = get_filters(
            dataset_type=dataset_type, datatype=datatype_, bids_filter=bids_filter
        )
        files = list_all_files_with_filter(
            data_pth=data_pth,
            dataset_type=dataset_type,
            filters=filters,
            subject=subject,
            sessions=sessions,
            datatype=datatype_,
            space=space,
        )
        if not files:
            cc_log.warning(no_files_found_msg(subject, datatype_, filters))
            continue
        cc_log.debug(f"    {subject} - getting files:\n     {files}")
        try:
            dl_dataset.get(path=files, jobs=jobs)
        except IncompleteResultsError:
            cc_log.error(f"    {subject} - failed to get files:\n     {files}")


def construct_cohort(
    output_dir: Path,
    datasets: pd.DataFrame,
    participants: pd.DataFrame | None,
    dataset_types: list[str],
    datatypes: list[str],
    space: str,
    bids_filter: None | dict[str, dict[str, dict[str, str]]] = None,
    skip_group_mriqc: bool = False,
) -> None:
    """Copy the data from sourcedata_dir to output_dir, to create a cohort.

    Parameters
    ----------
    output_dir : Path

    datasets : pd.DataFrame

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

    dataset_names = get_list_datasets_to_install(
        dataset_listing=datasets, participant_listing=participants
    )

    for dataset_ in dataset_names:
        cc_log.info(f" {dataset_}")

        # if no participants_ids then we grab all the participants
        # from the raw dataset
        if participants is not None:
            participants_ids = get_participant_ids(
                datasets=datasets, participants=participants, dataset_name=dataset_
            )
            if not participants_ids:
                cc_log.warning(f"  no participants in dataset {dataset_}")
                continue
            cc_log.info(f"  creating cohort with: {participants_ids}")
        else:
            data_pth = dataset_path(sourcedata(output_dir), dataset_)
            participants_ids = list_participants_in_dataset(data_pth)
            cc_log.info(f"  creating cohort with all participants in dataset {dataset_}")

        for dataset_type_ in dataset_types:
            if not get_dataset_url(dataset_, dataset_type_):
                cc_log.debug(f"      no {dataset_type_} for {dataset_}")
                continue
            cc_log.info(f"  {dataset_type_}")

            derivative = None if dataset_type_ == "raw" else dataset_type_
            src_pth = dataset_path(sourcedata(output_dir), dataset_, derivative=derivative)

            target_pth = return_target_pth(output_dir, dataset_type_, dataset_, src_pth)
            target_pth.mkdir(exist_ok=True, parents=True)

            copy_top_files(src_pth=src_pth, target_pth=target_pth, datatypes=datatypes)
            filter_excluded_participants(pth=target_pth, participants=participants_ids)

            for subject in participants_ids:
                if not is_subject_in_dataset(subject, src_pth):
                    cc_log.debug(f"  no participant {subject} in dataset {dataset_}")
                    continue

                if participants is not None:
                    sessions = get_sessions(participants, dataset_, subject)
                else:
                    sessions = list_sessions_in_participant(data_pth / subject)

                _copy_this_subject(
                    subject=subject,
                    sessions=sessions,
                    datatypes=datatypes,
                    dataset_type=dataset_type_,
                    space=space,
                    src_pth=src_pth,
                    target_pth=target_pth,
                    bids_filter=bids_filter,
                )

    add_study_tsv(output_dir, dataset_names)

    _generate_bagel_for_cohort(
        output_dir=output_dir,
        dataset_names=dataset_names,
        dataset_types=dataset_types,
    )

    if not skip_group_mriqc:
        _recreate_mriqc_group_reports(
            output_dir=output_dir, dataset_names=dataset_names, dataset_types=dataset_types
        )


def _copy_this_subject(
    subject: str,
    sessions: list[str] | list[None],
    datatypes: list[str],
    dataset_type: str,
    space: str,
    src_pth: Path,
    target_pth: Path,
    bids_filter: None | dict[str, dict[str, dict[str, str]]] = None,
) -> None:
    for datatype_ in datatypes:
        filters = get_filters(
            dataset_type=dataset_type, datatype=datatype_, bids_filter=bids_filter
        )
        files = list_all_files_with_filter(
            data_pth=src_pth,
            dataset_type=dataset_type,
            filters=filters,
            subject=subject,
            sessions=sessions,
            datatype=datatype_,
            space=space,
        )
        if not files:
            cc_log.warning(no_files_found_msg(subject, datatype_, filters))
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
    output_dir: Path, dataset_names: list[str], dataset_types: list[str]
) -> None:
    """Track what subjects have been processed by what pipeline."""
    cc_log.info(" creating bagel.csv file")
    bagel = _new_bagel()
    supported_dataset_types = ["fmriprep", "mriqc"]
    for dataset_type_, dataset_ in itertools.product(dataset_types, dataset_names):
        if dataset_type_ not in supported_dataset_types:
            continue
        cc_log.info(f"  {dataset_} - {dataset_type_}")

        raw_pth = return_target_pth(output_dir, "raw", dataset_)

        src_pth = dataset_path(sourcedata(output_dir), dataset_, derivative=dataset_type_)
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


def _recreate_mriqc_group_reports(
    output_dir: Path, dataset_names: list[str], dataset_types: list[str]
) -> None:
    """Recreate MRIQC group reports."""
    log_folder = output_dir / "logs"
    docker_log = log_folder / "docker.log"
    docker_log.parent.mkdir(exist_ok=True, parents=True)
    docker_log.touch(exist_ok=True)
    with open(docker_log, "w") as f:
        f.write("docker logs\n\n")

    cc_log.info("Recreating MRIQC group reports")
    if "mriqc" not in dataset_types:
        return None

    for dataset_ in dataset_names:
        cc_log.info(f" {dataset_}")

        target_pth = return_target_pth(output_dir=output_dir, dataset_type="raw", dataset=dataset_)
        mriqc_dirs = (target_pth / "derivatives").glob("mriqc-*")

        if not mriqc_dirs:
            continue

        for mriqc in mriqc_dirs:
            version = get_pipeline_version(mriqc)
            if not version:
                cc_log.debug(f" could not determine version of:\n  {mriqc}")
                continue
            cc_log.info(f"   mriqc-{version}")

            username = "poldracklab" if version.split(".")[0] == "0" else "nipreps"

            cmd = f"docker pull {username}/mriqc:{version}"
            cc_log.debug(f" {cmd}")
            with open(docker_log, "a") as output:
                result = subprocess.call(cmd, shell=True, stdout=output, stderr=output)
            if result != 0:
                cc_log.error(f"  failed to pull docker image: {username}/mriqc:{version}")
                continue

            cmd = f"docker run -t --rm \
                    -v {target_pth}:/bids_dir \
                    -v {mriqc}:/output_dir \
                        {username}/mriqc:{version} /bids_dir /output_dir group"
            cc_log.debug(f" {cmd}")
            with open(docker_log, "a") as output:
                result = subprocess.call(cmd, shell=True, stdout=output, stderr=output)
            if result != 0:
                cc_log.error(f"  failed to run docker image: {username}/mriqc:{version}")
                continue
