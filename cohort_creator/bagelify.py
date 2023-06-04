"""Create bagel file to get an idea what participants have been processed by what pipeline."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bids import BIDSLayout

from cohort_creator._utils import get_anat_files
from cohort_creator._utils import get_func_files
from cohort_creator._utils import set_name
from cohort_creator._utils import set_version


def bagelify(
    bagel: dict[str, list[str | None]], raw_path: Path, derivative_path: Path
) -> dict[str, list[str | None]]:
    """Create bagel dict to get an idea what participants have been processed by what pipeline.

    Parameters
    ----------
    bagel :
        _description_

    raw_path :
        _description_

    derivative_path :
        _description_
    """
    raw_layout = BIDSLayout(raw_path, validate=False, derivatives=False)

    if derivative_path.exists():
        layout = BIDSLayout(derivative_path, validate=False, derivatives=False)
    else:
        layout = None

    dataset_id = Path(raw_layout.root).name.replace("study-", "")
    name = set_name(derivative_path)
    version = set_version(derivative_path)

    subjects = raw_layout.get_subjects()
    for sub in subjects:
        if sessions := raw_layout.get_sessions(subject=sub):
            for ses in sessions:
                new_record = _process_session(sub, ses=ses)
                new_record["pipeline_complete"] = record_status(layout, raw_layout, sub, ses)
                new_record["pipeline_version"] = version
                new_record["pipeline_name"] = name
                new_record["dataset_id"] = dataset_id

                for key in bagel:
                    bagel[key].append(new_record.get(key))

        else:
            new_record = _process_session(sub)
            new_record["pipeline_complete"] = record_status(layout, raw_layout, sub)
            new_record["pipeline_version"] = version
            new_record["pipeline_name"] = name
            new_record["dataset_id"] = dataset_id

            for key in bagel:
                bagel[key].append(new_record.get(key))

    return bagel


def record_status(
    layout: BIDSLayout | None, raw_layout: BIDSLayout, sub: str, ses: str | None = None
) -> str:
    """Return status of session depending on the number of files in the derivative folder.

    Really rudiementary:

    - SUCCESS: number of files in derivative folder >= number of files in raw folder
    - FAIL: number of files in derivative folder == 0
    - INCOMPLETE: number of files in derivative folder < number of files in raw folder
    - UNAVAILABLE: no derivative folder

    Parameters
    ----------
    layout :

    raw_layout :

    sub :
        Subject label. Example: `"01"`.

    ses :
        Session label. Example: `"preop"`.

    Returns
    -------
    str :
        Status of the sessions
    """
    # TODO
    # - check if a specific file has all its expected derivatives
    #   (including for different spaces)
    if layout is None:
        return "UNAVAILABLE"
    files = get_anat_files(layout, sub, ses)
    files.extend(get_func_files(layout, sub, ses))

    if len(files) == 0:
        return "FAIL"

    raw_files = get_anat_files(raw_layout, sub, ses, extension="nii(.gz)?")
    raw_files.extend(get_func_files(raw_layout, sub, ses, extension="nii(.gz)?"))
    return "SUCCESS" if len(files) >= len(raw_files) else "INCOMPLETE"


def _process_session(sub: str, ses: str | None = None) -> dict[str, str]:
    new_record = _record(sub=sub, ses=ses)
    return new_record


def _new_bagel() -> dict[str, list[str | None]]:
    return {
        "dataset_id": [],
        "bids_id": [],
        "participant_id": [],
        "session": [],
        "has_mri_data": [],
        "pipeline_name": [],
        "pipeline_version": [],
        "pipeline_starttime": [],
        "pipeline_complete": [],
    }


def _record(sub: str, ses: str | None) -> dict[str, str]:
    tmp = ses if ses is not None else "1"
    out = {
        "dataset_id": "",
        "bids_id": f"sub-{sub}",
        "participant_id": f"sub-{sub}",
        "session": tmp,
        "has_mri_data": "TRUE",
        "pipeline_name": "",
        "pipeline_version": "",
        "pipeline_starttime": str(datetime.now()),
        "pipeline_complete": "SUCCESS",
    }
    return out
