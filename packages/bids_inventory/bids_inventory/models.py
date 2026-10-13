"""Data model of a dataset in the inventory.

``bids_inventory/data/columns_description.json`` is generated from this model:
after changing the model, regenerate it with::

    python -m bids_inventory.models
"""

import json
import types
from pathlib import Path
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field

# (number of samples, duration of a sample in seconds) of each run
RUNS_DURATION = list[tuple[int, float]]

NOT_BIDS_VALIDATED = "Does not check if the name of files are BIDS valid."
FIRST_PARTICIPANT = "Based on data from the first participant only."


def _field(description: str, assumptions: str = "", **kwargs: Any) -> Any:
    return Field(description=description, json_schema_extra={"assumptions": assumptions}, **kwargs)


def _derivative_link(pipeline: str) -> Any:
    return _field(
        f"Link to the {pipeline} dataset in the derivatives folder of the dataset "
        "or on OpenNeuroDerivatives. null if it does not exist.",
        default=None,
    )


def _derivative_version(pipeline: str, name: str) -> Any:
    return _field(
        f"Version of {name} that generated the '{pipeline}' derivative dataset, "
        "from 'GeneratedBy' (or 'PipelineDescription') in its dataset_description.json. "
        "null if there is no such derivative dataset or if the version is not recorded.",
        default=None,
    )


class BidsDataset(BaseModel):
    """Information about a BIDS dataset: one entry of the inventory.

    The order of the fields is the order of the columns of the listing.
    Missing values are ``None`` (saved as ``null`` in the listing).
    """

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    name: str = _field("Name of the dataset.", "OpenNeuro datasets start with 'ds'.")
    created_on: str | None = _field(
        "Date of the first commit of the datalad dataset, "
        "for example 'Thu May 18 14:34:38 2023 +0000'.",
        "The dataset may have been created or acquired long before "
        "it was turned into a datalad dataset.",
        default=None,
    )
    nb_subjects: int | None = _field(
        "Number of 'sub-*' folders in the dataset.",
        "Folders containing only non valid BIDS files will still be counted.",
        default=None,
    )
    has_participant_tsv: bool | None = _field(
        "Whether the dataset has a 'participants.tsv' file.", default=None
    )
    has_participant_json: bool | None = _field(
        "Whether the dataset has a 'participants.json' file.", default=None
    )
    participant_columns: list[str] = _field(
        "Name of each column in the participants.tsv.", default=[]
    )
    nb_sessions_tsv: int | None = _field(
        "Total number of '*sessions.tsv' files in the dataset.", default=None
    )
    nb_scans_tsv: int | None = _field(
        "Total number of '*scans.tsv' files in the dataset.", default=None
    )
    nb_physio_files: int | None = _field(
        "Total number of '*physio.tsv.gz' files in the dataset.",
        NOT_BIDS_VALIDATED,
        default=None,
    )
    nb_stim_files: int | None = _field(
        "Total number of '*stim.tsv.gz' files in the dataset.",
        NOT_BIDS_VALIDATED,
        default=None,
    )
    has_phenotype_dir: bool | None = _field(
        "Whether the dataset has a 'phenotype' folder.", default=None
    )
    has_stimuli_dir: bool | None = _field(
        "Whether the dataset has a 'stimuli' folder.", default=None
    )
    eeg_file_formats: dict[str, int] | None = _field(
        "Total number of EEG files of each BIDS supported file format.",
        NOT_BIDS_VALIDATED,
        default=None,
    )
    ieeg_file_formats: dict[str, int] | None = _field(
        "Total number of iEEG files of each BIDS supported file format.",
        NOT_BIDS_VALIDATED,
        default=None,
    )
    meg_file_formats: dict[str, int] | None = _field(
        "Total number of MEG files of each BIDS supported file format.",
        NOT_BIDS_VALIDATED,
        default=None,
    )
    nb_meeg_channels: list[int] = _field(
        "Number of EEG, iEEG or MEG channels. Read from the header where possible.",
        FIRST_PARTICIPANT,
        default=[],
    )
    datatypes: list[str] = _field(
        "List of BIDS supported datatypes found in the dataset.",
        "A datatype will be listed even if it occurs only in a single subject.",
        default=[],
    )
    sessions: list[str] = _field(
        "List of the session names.",
        "A session name will be listed even if it occurs only once for a single subject. "
        "The session will be listed even if it contains no valid BIDS file.",
        default=[],
    )
    tasks: list[str] = _field(
        "List of the task names present in the dataset as they appear in filenames.",
        "A task name will be listed even if it occurs only once for a single subject. "
        "The task will be listed even if it comes from a BIDS invalid filename.",
        default=[],
    )
    size: str | None = _field(
        "Size of the whole dataset as reported by 'datalad status --annex all'.",
        "This includes all BIDS invalid files "
        "and the content of the derivatives and sourcedata folders. "
        "So likely to be an overestimation.",
        default=None,
    )
    license: str | None = _field("Name of the license of the dataset.", default=None)
    authors: list[str] = _field(
        "List of the authors as reported in the dataset_description.json.", default=[]
    )
    institutions: list[str] = _field(
        "List of the unique institutions found "
        "in the InstitutionName and InstitutionAddress of the JSON sidecars.",
        "Based on the JSON sidecars in the root folder and of the first participant only.",
        default=[],
    )
    field_strength: list[float] = _field(
        "List of the unique MagneticFieldStrength (in Tesla) found in the JSON sidecars.",
        "Based on the JSON sidecars in the root folder and of the first participant only.",
        default=[],
    )
    bids_version: str | None = _field(
        "BIDSVersion in the dataset_description.json of the dataset.", default=None
    )
    duration: dict[str, RUNS_DURATION | dict[str, RUNS_DURATION]] | None = _field(
        "Duration of each run, as (number of samples, duration of a sample in seconds): "
        "the number of volumes and the repetition time for fMRI and PET, "
        "the number of samples and 1 / sampling frequency for EEG and iEEG. "
        "Listed by datatype and where possible split further by task. "
        "(0, NaN) if the duration of a run could not be read.",
        "Based on data from the first participant only: "
        "assumes that all participants followed the same protocol.",
        default=None,
    )
    references_and_links: list[str] = _field(
        "List of the ReferencesAndLinks of the dataset_description.json.", default=[]
    )
    raw: str | None = _field("Link to the raw dataset.", default=None)
    fmriprep: str | None = _derivative_link("fMRIPrep")
    freesurfer: str | None = _derivative_link("FreeSurfer")
    mriqc: str | None = _derivative_link("MRIQC")
    fmriprep_version: str | None = _derivative_version("fmriprep", "fMRIPrep")
    freesurfer_version: str | None = _derivative_version("freesurfer", "FreeSurfer")
    mriqc_version: str | None = _derivative_version("mriqc", "MRIQC")


def _format(annotation: Any) -> str:
    """Render a type annotation as in the code, without the 'None' of optional fields."""
    if get_origin(annotation) in (Union, types.UnionType):
        return " | ".join(_format(x) for x in get_args(annotation) if x is not type(None))
    if get_origin(annotation) is not None:
        args = ", ".join(_format(x) for x in get_args(annotation))
        return f"{get_origin(annotation).__name__}[{args}]"
    return getattr(annotation, "__name__", str(annotation))


def columns_description() -> dict[str, Any]:
    """Describe the columns of the listing, as in columns_description.json."""
    columns = {}
    for name, field in BidsDataset.model_fields.items():
        extra = field.json_schema_extra
        assumptions = extra.get("assumptions", "") if isinstance(extra, dict) else ""
        columns[name] = {
            "Description": field.description or "",
            "Format": _format(field.annotation),
            "Assumptions": assumptions,
        }
    return {
        "Description": (
            "Describes the columns of the listing of BIDS datasets. "
            "The Format of each column is described as python type. "
            "Missing values are null. "
            "The content of the .bidsignore file is not taken into account. "
            "Generated from bids_inventory.models.BidsDataset."
        ),
        "Columns": columns,
    }


def write_columns_description(output_file: Path) -> None:
    with open(output_file, "w") as f:
        json.dump(columns_description(), f, indent=4, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    from bids_inventory.listing import _data_dir

    write_columns_description(_data_dir() / "columns_description.json")
