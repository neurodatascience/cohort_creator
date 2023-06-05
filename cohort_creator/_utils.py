"""General utility functions for the cohort creator."""
from __future__ import annotations

import functools
import itertools
import json
import shutil
from pathlib import Path
from typing import Any

import pandas as pd
from bids import BIDSLayout
from bids.layout import BIDSFile

from .logger import cc_logger
from cohort_creator._version import __version__

cc_log = cc_logger()


def filter_excluded_participants(pth: Path, participants: list[str]) -> None:
    """Remove subjects from participants.tsv that were not included in the cohort."""
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


def check_tsv_content(tsv_file: Path) -> pd.DataFrame:
    df = pd.read_csv(tsv_file, sep="\t")
    if "DatasetName" not in df.columns:
        raise ValueError(f"Column 'DatasetName' not found in {tsv_file}")
    return df


def check_participant_listing(participants_listing: pd.DataFrame) -> None:
    for col in ["SessionID", "SubjectID"]:
        if "SubjectID" not in participants_listing.columns:
            raise ValueError(f"Column '{col}' not found in participants listing data.")


def get_participant_ids(participants: pd.DataFrame, dataset_name: str) -> list[str] | None:
    mask = participants["DatasetName"] == dataset_name
    if mask.sum() == 0:
        cc_log.warning(f"  no participants in dataset {dataset_name}")
        return None
    participants_df = participants[mask]
    return sorted(participants_df["SubjectID"].tolist())


def get_pipeline_version(pth: Path | None = None) -> None | str:
    """Get the version of the pipeline that was used to create the dataset."""
    if pth is None:
        return None
    dataset_description = pth / "dataset_description.json"
    if not dataset_description.exists():
        return None
    with open(dataset_description) as f:
        data = json.load(f)
    return data.get("GeneratedBy")[0].get("Version")


def get_pipeline_name(pth: Path) -> None | str:
    """Get the name of the pipeline that was used to create the dataset."""
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


def get_extensions(dataset_type: str, suffix: str) -> list[str]:
    if dataset_type == "mriqc":
        return ["json"]
    return ["tsv", "json"] if suffix == "events" else ["nii.gz", "nii", "json"]


def get_suffixes(datatype: str) -> list[str]:
    if datatype == "func":
        return ["events", "bold"]
    elif datatype == "anat":
        return ["T1w"]
    return ["*"]


def no_files_found_msg(
    subject: str,
    datatype: str,
) -> str:
    return f"""    no files found for:
     - subject: {subject}
     - datatype: {datatype}"""


def openneuro_listing_tsv() -> Path:
    root_dir = Path(__file__).parent
    data_dir = root_dir / "data"
    return data_dir / "openneuro.tsv"


@functools.lru_cache(maxsize=1)
def openneuro_df() -> pd.DataFrame:
    return pd.read_csv(openneuro_listing_tsv(), sep="\t")


def list_all_files(
    data_pth: Path,
    dataset_type: str,
    subject: str,
    sessions: list[str] | list[None],
    datatype: str,
    space: str,
) -> list[str]:
    """List all data files of a datatype for all sessions of a subject in a dataset."""
    files: list[str] = []
    for session_, suffix in itertools.product(sessions, get_suffixes(datatype)):
        if not session_:
            datatype_pth = data_pth / subject / datatype
        else:
            datatype_pth = data_pth / subject / f"ses-{session_}" / datatype
        if not datatype_pth.exists():
            cc_log.warning(f"Path '{datatype_pth}' does not exist")
            continue

        for ext in get_extensions(dataset_type, suffix):
            glob_pattern = create_glob_pattern(dataset_type, suffix=suffix, ext=ext, space=space)
            tmp = datatype_pth.glob(glob_pattern)
            files.extend([str(f.relative_to(data_pth)) for f in tmp])

    return files


def create_glob_pattern(dataset_type: str, suffix: str, ext: str, space: str | None = None) -> str:
    return (
        f"*_{suffix}.{ext}"
        if dataset_type in {"raw", "mriqc"}
        else f"*{space}*preproc*_{suffix}.{ext}"
    )


def dataset_path(root: Path, dataset_: str, derivative: str | None = None) -> Path:
    if derivative is None:
        return root / dataset_
    name = f"{dataset_}-{derivative}"
    return (root / dataset_).with_name(name)


def get_sessions(
    participants: pd.DataFrame, dataset_: str, participant: str
) -> list[str] | list[None]:
    mask = (participants["DatasetName"] == dataset_) & (participants["SubjectID"] == participant)
    sessions = participants[mask].SessionID.values
    return listify(sessions[0])


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


def add_study_tsv(output_dir: Path, datasets: pd.DataFrame) -> None:
    """Create a study.tsv file."""
    cc_log.info(" creating study.tsv file")
    studies: dict[str, list[Any]] = {
        "study_ID": [],
        "mean_age": [],
        "ratio_female": [],
        "InstitutionName": [],
        "InstitutionAddress": [],
    }

    for dataset_ in datasets["DatasetName"]:
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
    output_dir: Path, dataset_type_: str, dataset_: str, src_pth: Path | None = None
) -> Path:
    study_ID = f"study-{dataset_}"
    folder_name = study_ID
    if dataset_type_ == "raw":
        return dataset_path(output_dir, study_ID)
    folder_name = dataset_type_
    if version := get_pipeline_version(src_pth):
        folder_name = f"{dataset_type_}-{version}"
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
