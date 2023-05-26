from __future__ import annotations

import pandas as pd


def get_sessions(participants: pd.DataFrame, dataset_: str, participant: str) -> list[str | None]:
    mask = (participants["DatasetName"] == dataset_) & (participants["SubjectID"] == participant)
    sessions = participants[mask].SessionID.values
    if sessions[0] == "[]":
        return [None]
    else:
        return sessions[0].replace("[", "").replace("]", "").replace("'", "").split(", ")
