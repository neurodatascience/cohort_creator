"""General utility functions for the cohort creator."""
from __future__ import annotations

import functools
import itertools
import json
import shutil
from math import isnan
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from bids import BIDSLayout
from bids.layout import BIDSFile

from .logger import cc_logger
from cohort_creator._version import __version__

cc_log = cc_logger()


def create_tsv_participant_session_in_datasets(
    output_dir: Path, dataset_paths: list[Path]
) -> Path:
    (output_dir.parent / "code").mkdir(exist_ok=True, parents=True)
    content: dict[str, list[str]] = {
        "DatasetID": [],
        "SubjectID": [],
        "SessionID": [],
        "SessionPath": [],
    }

    for dataset in dataset_paths:
        layout = BIDSLayout(dataset)

        subjects = layout.get_subjects()
        for sub in sorted(subjects):
            sessions = layout.get_sessions(subject=sub) or ["n/a"]
            for ses in sorted(sessions):
                if ses != "n/a":
                    ses = f"ses-{ses}"

                content["DatasetID"].append(dataset.name)
                content["SubjectID"].append(f"sub-{sub}")
                content["SessionID"].append(ses)
                if ses != "n/a":
                    ses += "/"
                else:
                    ses = ""
                content["SessionPath"].append(f"{dataset.name}/sub-{sub}/{ses}")

    df = pd.DataFrame(content)
    output_file = output_dir.parent / "code" / "participants.tsv"
    df.to_csv(output_file, sep="\t", index=False)
    return output_file


def check_tsv_for_empty_header(tsv_file: Path) -> pd.DataFrame:
    """Check if tsv first line is empty and reload if so."""
    dataset_listing_df = pd.read_csv(tsv_file, sep="\t")
    if dataset_listing_df.columns[0] == "Unnamed: 0":
        dataset_listing_df = pd.read_csv(tsv_file, sep="\t", index_col=0)
    return dataset_listing_df


def load_dataset_listing(dataset_listing: list[str]) -> pd.DataFrame:
    """Load dataset listing from TSV file.

    Parameters
    ----------
    dataset_listing : :obj:`list` of :obj:`str`
                      list of strings of dataset IDs
                      or list of a the path to a dataset listing

    Returns
    -------
    :obj:`pandas.DataFrame`

    """
    if len(dataset_listing) > 1:
        return pd.DataFrame({"DatasetID": dataset_listing})

    elif len(dataset_listing) == 1:
        dataset = dataset_listing[0]
        if not Path(dataset).exists():
            return pd.DataFrame({"DatasetID": [dataset]})
        dataset_tsv = Path(dataset).resolve()
        return check_tsv_content(dataset_tsv)


def load_participant_listing(participant_listing: Path | str) -> pd.DataFrame:
    """Load participant listing from TSV file."""
    participant_listing_df = check_tsv_content(participant_listing)
    check_participant_listing(participant_listing_df)
    return participant_listing_df


def filter_excluded_participants(pth: Path, participants: list[str] | None) -> None:
    """Remove subjects from participants.tsv that were not included in the cohort."""
    if participants is None:
        return
    participants_tsv = pth / "participants.tsv"
    if not (participants_tsv).exists():
        return
    participants_df = pd.read_csv(participants_tsv, sep="\t")
    participants_df = participants_df[participants_df["participant_id"].isin(participants)]
    participants_df.to_csv(participants_tsv, sep="\t", index=False)


def copy_top_files(src_pth: Path, target_pth: Path, datatypes: list[str]) -> None:
    """Copy top files from BIDS src_pth to BIDS target_pth."""
    top_files = ["dataset_description.json", "participants.*", "README*"]
    if "func" in datatypes:
        top_files.extend(["*task-*_events.tsv", "*task-*_events.json", "*task-*_bold.json"])
    if "anat" in datatypes:
        top_files.append("*T1w.json")

    for top_file_ in top_files:
        for f in src_pth.glob(top_file_):
            if (target_pth / f.name).exists():
                cc_log.debug(f"      file '{(target_pth / f.name)}' already present")
                continue
            try:
                shutil.copy(src=f, dst=target_pth, follow_symlinks=True)
            except FileNotFoundError:
                cc_log.error(f"      Could not find file '{f}'")


def check_tsv_content(tsv_file: Path | str) -> pd.DataFrame:
    tsv_file = Path(tsv_file).resolve()
    if not tsv_file.exists():
        raise FileNotFoundError(f"Could not find dataset listing at '{tsv_file}'")
    df = check_tsv_for_empty_header(tsv_file)
    if "      DatasetID" in df.columns:
        cc_log.debug(f"Renaming column: '      DatasetID' -> 'DatasetID' in:\n{tsv_file}")
        df.rename(columns={"      DatasetID": "DatasetID"}, inplace=True)
    if "DatasetID" not in df.columns:
        raise ValueError(
            f"Column 'DatasetID' not found in {tsv_file}. Columns found: {df.columns}"
        )
    return df


def check_participant_listing(participant_listing: pd.DataFrame) -> None:
    for col in ["SubjectID", "SessionPath"]:
        if col not in participant_listing.columns:
            raise ValueError(
                f"Column '{col}' not found in participants listing data.\n"
                f"Columns found: {participant_listing.columns}."
            )


def get_participant_ids(
    datasets: pd.DataFrame, participants: pd.DataFrame, dataset_name: str
) -> list[str] | None:
    datasets_id = return_dataset_id(datasets, dataset_name)
    mask = participants["DatasetID"] == datasets_id
    if mask.sum() == 0:
        return None
    participants_df = participants[mask]
    return sorted(list(participants_df["SubjectID"].unique()))


def return_dataset_id(datasets: pd.DataFrame, dataset_name: str) -> str:
    dataset_uri = return_dataset_uri(dataset_name)
    mask = datasets["PortalURI"] == dataset_uri
    return datasets[mask]["DatasetID"].values[0]


def get_pipeline_version(pth: Path | None = None) -> None | str:
    """Try to get pipeline version from the dataset description."""
    if pth is None:
        return None
    dataset_description = pth / "dataset_description.json"
    if not dataset_description.exists():
        return None
    with open(dataset_description) as f:
        data = json.load(f)
    return data.get("GeneratedBy")[0].get("Version")


def get_pipeline_name(pth: Path) -> None | str:
    """Try to get the name of the pipeline from the dataset description."""
    dataset_description = pth / "dataset_description.json"
    if not dataset_description.exists():
        return None
    with open(dataset_description) as f:
        data = json.load(f)
    return data.get("GeneratedBy")[0].get("Name")


def _is_dataset_in_openneuro(dataset_name: str) -> bool:
    openneuro = openneuro_df()
    mask = openneuro.name == dataset_name
    return mask.sum() != 0


def get_dataset_url(dataset_name: str, dataset_type: str) -> bool:
    openneuro = openneuro_df()
    mask = openneuro.name == dataset_name
    url = openneuro[mask][dataset_type].values[0]
    return False if pd.isna(url) else url


def is_subject_in_dataset(subject: str, dataset_pth: Path) -> bool:
    return (dataset_pth / subject).exists()


def no_files_found_msg(
    subject: str,
    datatype: str,
    filters: dict[str, dict[str, str]],
) -> str:
    return f"""    no files found for:
     - subject: {subject}
     - datatype: {datatype}
     - filters: {filters}"""


def openneuro_listing_tsv() -> Path:
    root_dir = Path(__file__).parent
    data_dir = root_dir / "data"
    return data_dir / "openneuro.tsv"


@functools.lru_cache(maxsize=1)
def openneuro_df() -> pd.DataFrame:
    return pd.read_csv(openneuro_listing_tsv(), sep="\t")


def sourcedata(pth: Path) -> Path:
    return pth / "sourcedata"


def dataset_path(root: Path, dataset: str, derivative: str | None = None) -> Path:
    if derivative is None:
        return root / dataset
    name = f"{dataset}-{derivative}"
    return (root / dataset).with_name(name)


def get_sessions(
    participants: pd.DataFrame, dataset: str, participant: str
) -> list[str] | list[None]:
    mask = (participants["DatasetID"] == dataset) & (participants["SubjectID"] == participant)
    sessions = sorted(participants[mask].SessionID.values.tolist())
    for i, ses in enumerate(sessions):
        if isinstance(ses, float) and isnan(ses):
            sessions[i] = None
    return sessions


def list_sessions_in_participant(participant_pth: Path) -> list[str] | list[None]:
    if sessions := [
        x.name for x in participant_pth.iterdir() if x.is_dir() and x.name.startswith("ses-")
    ]:
        return sorted(sessions)
    else:
        return [None]


def listify(some_str: str) -> list[str] | list[None]:
    """Return a list from a string literal like `"['foo', 'bar']"`."""
    if some_str == "[]":
        return [None]
    else:
        return some_str.replace("[", "").replace("]", "").replace("'", "").split(", ")


def validate_dataset_types(dataset_types: list[str]) -> None:
    SUPPORTED_DATASET_TYPES = {"raw", "fmriprep", "mriqc"}
    for dataset_type in dataset_types:
        if dataset_type not in SUPPORTED_DATASET_TYPES:
            raise ValueError(
                f"Dataset type '{dataset_type}' is not supported.\n"
                f"Supported types are '{SUPPORTED_DATASET_TYPES}'"
            )


def add_study_tsv(output_dir: Path, datasets: list[str]) -> None:
    """Create a study.tsv file."""
    cc_log.info(" creating study.tsv file")
    studies: dict[str, list[Any]] = {
        "study_ID": [],
        "mean_age": [],
        "ratio_female": [],
        "InstitutionName": [],
        "InstitutionAddress": [],
    }

    for dataset_ in datasets:
        studies["study_ID"].append(dataset_)

        participants_tsv = dataset_path(output_dir, f"study-{dataset_}") / "participants.tsv"

        if not participants_tsv.exists():
            studies["mean_age"].append("n/a")
            studies["ratio_female"].append("n/a")
            studies["InstitutionName"].append("n/a")
            studies["InstitutionAddress"].append("n/a")
            continue

        partcipants = pd.read_csv(participants_tsv, sep="\t")

        if "age" in partcipants.columns:
            mean_age = partcipants["age"].mean()
            studies["mean_age"].append(mean_age)
        else:
            studies["mean_age"].append("n/a")

        if "sex" in partcipants.columns:
            ratio_female = partcipants["sex"].value_counts(normalize=True)["F"]
            studies["ratio_female"].append(ratio_female)
        else:
            studies["ratio_female"].append("n/a")

        institution_name, institution_address = get_institution(output_dir / f"study-{dataset_}")
        studies["InstitutionName"].append(institution_name)
        studies["InstitutionAddress"].append(institution_address)

    df = pd.DataFrame.from_dict(studies)
    df.to_csv(output_dir / "studies.tsv", sep="\t", index=False)

    studies_dict: dict[str, dict[str, str]] = {
        "study_ID": {
            "LongName": "ID of the Study",
            "Description": "string representing the name of the study",
        },
        "mean_age": {
            "LongName": "participants mean age",
            "Description": "mean of the age of all participants in the study",
        },
        "ratio_female": {"Description": "ratio of female participants in the study"},
        "InstitutionName": {"Description": "Institution(s) where this study was conducted."},
        "InstitutionAddress": {
            "Description": "Institution(s) address where this study was conducted."
        },
    }
    with open(output_dir / "studies.json", "w") as f:
        json.dump(studies_dict, f, indent=4)


def get_institution(dataset: Path) -> tuple[list[Any], list[Any]]:
    layout = BIDSLayout(dataset)
    files = layout.get(
        suffix="bold|T[12]{1}w", extension="json", regex_search=True, return_type="filename"
    )

    institution_name = []
    institution_address = []
    for f in files:
        with open(f) as json_file:
            data = json.load(json_file)
            institution_name.append(data.get("InstitutionName"))
            institution_address.append(data.get("InstitutionAddress"))
    institution_name = list(set(institution_name))
    institution_address = list(set(institution_address))
    return (institution_name, institution_address)


def create_ds_description(output_dir: Path) -> None:
    """Create a dataset_description.json file."""
    ds_desc: dict[str, Any] = {
        "BIDSVersion": "1.8.0",
        "License": None,
        "Name": None,
        "ReferencesAndLinks": [],
        "Authors": [
            "Foo",
            "Bar",
        ],
        "DatasetDOI": None,
        "DatasetType": "derivative",
        "GeneratedBy": [
            {
                "Name": "cohort_creator",
                "Version": __version__,
                "CodeURL": "https://github.com/neurodatascience/cohort_creator.git",
            }
        ],
        "HowToAcknowledge": (
            """Please refer to our repository:
                             "https://github.com/neurodatascience/cohort_creator.git."""
        ),
    }
    with open(output_dir / "dataset_description.json", "w") as f:
        json.dump(ds_desc, f, indent=4)


def return_target_pth(
    output_dir: Path, dataset_type: str, dataset: str, src_pth: Path | None = None
) -> Path:
    study_ID = f"study-{dataset}"
    folder_name = study_ID
    if dataset_type == "raw":
        return dataset_path(output_dir, study_ID)
    folder_name = dataset_type
    if version := get_pipeline_version(src_pth):
        folder_name = f"{dataset_type}-{version}"
    return output_dir / study_ID / "derivatives" / folder_name


def set_name(derivative_path: Path) -> str:
    if derivative_path.exists():
        name = get_pipeline_name(derivative_path) or "UNKNOWN"
    else:
        name = derivative_path.name.lower().split("-")[0]

    if name == "fmriprep":
        name = "fMRIPrep"
    elif name == "mriqc":
        name = "MRIQC"

    return name


def set_version(derivative_path: Path) -> str:
    if derivative_path.exists():
        return get_pipeline_version(derivative_path) or "UNKNOWN"
    elif derivative_path.name.lower().split("-")[0] == "fmriprep":
        return "21.0.1"
    elif derivative_path.name.lower().split("-")[0] == "mriqc":
        return "0.16.1"
    else:
        return "UNKNOWN"


def get_anat_files(
    layout: BIDSLayout, sub: str, ses: str | None = None, extension: str = "json"
) -> list[BIDSFile]:
    return get_files(layout=layout, sub=sub, suffix="^T[12]{1}w$", ses=ses, extension=extension)


def get_func_files(
    layout: BIDSLayout, sub: str, ses: str | None = None, extension: str = "json"
) -> list[BIDSFile]:
    return get_files(layout=layout, sub=sub, suffix="^bold$", ses=ses, extension=extension)


def get_files(
    layout: BIDSLayout, sub: str, suffix: str, ses: str | None = None, extension: str = "json"
) -> list[BIDSFile]:
    if ses is None:
        return layout.get(subject=sub, suffix=suffix, extension=extension, regex_search=True)
    return layout.get(
        subject=f"^{sub}$",
        session=f"^{ses}$",
        suffix=suffix,
        extension=extension,
        regex_search=True,
    )


def default_bids_filter_file() -> Path:
    return Path(__file__).parent / "data" / "bids_filter.json"


def get_bids_filter(bids_filter_file: Path | None = None) -> dict[str, dict[str, dict[str, str]]]:
    if bids_filter_file is None:
        bids_filter_file = default_bids_filter_file()

    if not bids_filter_file.exists():
        raise FileNotFoundError(f"Could not find bids filter file at '{bids_filter_file}'")

    with open(bids_filter_file) as f:
        filters = json.load(f)

    validate_bids_filter(filters=filters, bids_filter_file=bids_filter_file)

    return filters


def validate_bids_filter(
    filters: dict[str, dict[str, dict[str, str]]], bids_filter_file: Path
) -> None:
    REQUIRED_KEYS = {"datatype", "suffix", "ext"}
    for dataset_type, required_key in itertools.product(filters, REQUIRED_KEYS):
        if any(not isinstance(filters[dataset_type][x], dict) for x in filters[dataset_type]):
            raise TypeError(
                f"All values in '{dataset_type}' "
                f"in bids filter file at '{bids_filter_file}' "
                "must be JSON objects."
            )
        for suffix_group in filters[dataset_type]:
            if required_key not in filters[dataset_type][suffix_group]:
                raise ValueError(
                    f"Key '{required_key}' not found in '{dataset_type}[{suffix_group}]' "
                    f"in bids filter file at '{bids_filter_file}'"
                )


def get_filters(
    dataset_type: str,
    datatype: str,
    bids_filter: None | dict[str, dict[str, dict[str, str]]] = None,
) -> dict[str, dict[str, str]]:
    if bids_filter is None:
        bids_filter = get_bids_filter()
    return {
        x: bids_filter[dataset_type][x]
        for x in bids_filter[dataset_type]
        if bids_filter[dataset_type][x]["datatype"] == datatype
    }


def create_glob_pattern_from_filter(dataset_type: str, filter: dict[str, str]) -> str:
    # - task
    # - acquisition
    # - ceagent
    # - reconstruction
    # - direction
    # - run
    # - echo
    # - part
    # - space
    # - resolution
    # - density
    # - label
    # - description
    pattern = f"*{filter['ses']}*{filter['task']}*{filter['run']}"
    if dataset_type not in {"raw", "mriqc"}:
        pattern = f"*{pattern}*{filter['space']}*{filter['desc']}"
    pattern = f"{pattern}*_{filter['suffix']}.{filter['ext']}"
    while "**" in pattern:
        pattern = pattern.replace("**", "*")
    return pattern


def list_all_files_with_filter(
    data_pth: Path,
    dataset_type: str,
    filters: dict[str, dict[str, str]],
    subject: str,
    sessions: list[str] | list[None],
    datatype: str,
    space: str | None = None,
) -> list[str]:
    """List all data files of a datatype for all sessions of a subject in a dataset."""
    files: list[str] = []

    for session_ in sessions:
        # TODO
        # take care of data averaged across sessions for fmriprep anat
        if not session_ or session_ in [np.nan]:
            datatype_pth = data_pth / subject / datatype
        else:
            datatype_pth = data_pth / subject / session_ / datatype
        if not datatype_pth.exists():
            cc_log.warning(f"Path '{datatype_pth}' does not exist")
            continue

        for key in filters:
            filter_ = augment_filter(
                dataset_type=dataset_type,
                filters=filters,
                key=key,
                session=session_,
                space=space,
            )
            glob_pattern = create_glob_pattern_from_filter(
                dataset_type=dataset_type, filter=filter_
            )
            files.extend([str(f.relative_to(data_pth)) for f in datatype_pth.glob(glob_pattern)])
            if filter_.get("ext") != "json":
                tmp = filter_.copy()
                tmp["ext"] = "json"
                glob_pattern = create_glob_pattern_from_filter(
                    dataset_type=dataset_type, filter=tmp
                )
                files.extend(
                    [str(f.relative_to(data_pth)) for f in datatype_pth.glob(glob_pattern)]
                )

    return sorted(files)


def augment_filter(
    dataset_type: str,
    filters: dict[str, dict[str, str]],
    key: str,
    session: str | None = None,
    space: str | None = None,
) -> dict[str, str]:
    filter_ = filters[key]
    filter_["ses"] = session or "*"
    if "task" not in filter_:
        filter_["task"] = "*"
    if "run" not in filter_:
        filter_["run"] = "*"
    if dataset_type not in {"raw", "mriqc"}:
        filter_["space"] = "*" if key not in {"confounds"} and space else space or "*"
        if "desc" not in filter_:
            filter_["desc"] = "*"
    return filter_


def get_list_datasets_to_install(
    dataset_listing: pd.DataFrame,
    participant_listing: pd.DataFrame | None = None,
) -> list[str]:
    if participant_listing is None:
        return sorted(list(dataset_listing["DatasetID"]))

    datasets_nodes = return_datasets_nodes(participant_listing)
    list_datasets = []
    for dataset in datasets_nodes:
        dataset_uri = dataset_listing[dataset_listing["DatasetID"] == dataset]["PortalURI"].values[
            0
        ]
        list_datasets.append(Path(dataset_uri).stem)
    return sorted(list_datasets)


def return_datasets_nodes(participant_listing: pd.DataFrame) -> list[str]:
    return list(participant_listing["DatasetID"].unique())


def return_dataset_uri(dataset_name: str) -> str:
    return f"https://github.com/OpenNeuroDatasets-JSONLD/{dataset_name}.git"


def list_participants_in_dataset(data_pth: Path) -> list[str]:
    return [x.name for x in data_pth.iterdir() if x.is_dir() and x.name.startswith("sub-")]
