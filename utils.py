from __future__ import annotations

from pathlib import Path

import pandas as pd


def output_dir() -> Path:
    return Path(__file__).parent / "inputs"


def get_sessions(participants: pd.DataFrame, dataset_: str, participant: str) -> list[str | None]:
    mask = (participants["DatasetName"] == dataset_) & (participants["SubjectID"] == participant)
    sessions = participants[mask].SessionID.values
    if sessions[0] == "[]":
        return [None]
    else:
        return sessions[0].replace("[", "").replace("]", "").replace("'", "").split(", ")
