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
    raw_layout = BIDSLayout(raw_path, validate=False, derivatives=False)

    if derivative_path.exists():
        layout = BIDSLayout(derivative_path, validate=False, derivatives=False)
    else:
        layout = None

    name = set_name(derivative_path)
    version = set_version(derivative_path)

    subjects = raw_layout.get_subjects()
    for sub in subjects:
        if sessions := raw_layout.get_sessions(subject=sub):
            for ses in sessions:
                new_record = process_session(sub, ses=ses)
                new_record["pipeline_version"] = version
                new_record["pipeline_name"] = name
                new_record["pipeline_complete"] = session_status(layout, raw_layout, sub, ses)
                for key in bagel:
                    bagel[key].append(new_record.get(key))

        else:
            new_record = process_session(sub)
            new_record["pipeline_version"] = version
            new_record["pipeline_name"] = name
            new_record["pipeline_complete"] = session_status(layout, raw_layout, sub)
            for key in bagel:
                bagel[key].append(new_record.get(key))

    return bagel


def session_status(
    layout: BIDSLayout | None, raw_layout: BIDSLayout, sub: str, ses: str | None = None
) -> str:
    if layout is None:
        return "UNAVAILABLE"
    files = get_anat_files(layout, sub, ses)
    files.extend(get_func_files(layout, sub, ses))

    raw_files = get_anat_files(raw_layout, sub, ses, extension="nii(.gz)?")
    raw_files.extend(get_func_files(raw_layout, sub, ses, extension="nii(.gz)?"))
    if len(files) > len(raw_files):
        raise ValueError(
            "Cannot have more processed files than raw files "
            f"for sub-{sub} ses-{ses}."
            f"\nraw files: {raw_files}"
            f"\nprocessed files: {files}"
        )
    if len(files) == 0:
        return "FAIL"
    elif len(files) == len(raw_files):
        return "SUCCESS"
    return "INCOMPLETE"


def process_session(sub: str, ses: str | None = None) -> dict[str, str]:
    new_record = record(sub=sub, ses=ses)
    return new_record


def new_bagel() -> dict[str, list[str | None]]:
    return {
        "bids_id": [],
        "participant_id": [],
        "session": [],
        "has_mri_data": [],
        "pipeline_name": [],
        "pipeline_version": [],
        "pipeline_starttime": [],
        "pipeline_complete": [],
    }


def record(sub: str, ses: str | None) -> dict[str, str]:
    tmp = ses if ses is not None else "1"
    out = {
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
