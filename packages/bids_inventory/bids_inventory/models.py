"""Data model of a dataset in the inventory.

The meaning of each field is described in ``bids_inventory/data/columns_description.json``.
"""

from pydantic import BaseModel, ConfigDict

# (number of samples, duration of a sample in seconds) of each run
RUNS_DURATION = list[tuple[int, float]]


class BidsDataset(BaseModel):
    """Information about a BIDS dataset: one entry of the inventory.

    The order of the fields is the order of the columns of the listing.
    Missing values are ``None`` (saved as ``null`` in the listing).
    """

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    name: str
    created_on: str | None = None
    nb_subjects: int | None = None
    has_participant_tsv: bool | None = None
    has_participant_json: bool | None = None
    participant_columns: list[str] = []
    nb_sessions_tsv: int | None = None
    nb_scans_tsv: int | None = None
    nb_physio_files: int | None = None
    nb_stim_files: int | None = None
    has_phenotype_dir: bool | None = None
    has_stimuli_dir: bool | None = None
    eeg_file_formats: dict[str, int] | None = None
    ieeg_file_formats: dict[str, int] | None = None
    meg_file_formats: dict[str, int] | None = None
    nb_meeg_channels: list[int] = []
    datatypes: list[str] = []
    sessions: list[str] = []
    tasks: list[str] = []
    size: str | None = None
    license: str | None = None
    authors: list[str] = []
    institutions: list[str] = []
    field_strength: list[float] = []
    bids_version: str | None = None
    # by datatype, and by task where possible
    duration: dict[str, RUNS_DURATION | dict[str, RUNS_DURATION]] | None = None
    references_and_links: list[str] = []
    raw: str | None = None
    fmriprep: str | None = None
    freesurfer: str | None = None
    mriqc: str | None = None
    fmriprep_version: str | None = None
    freesurfer_version: str | None = None
    mriqc_version: str | None = None
