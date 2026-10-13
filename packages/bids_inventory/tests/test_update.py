from __future__ import annotations

import numpy as np
import pytest

# needs the 'update' extra
pytest.importorskip("datalad")
pytest.importorskip("mne")

from bids_inventory._update import (  # noqa: E402
    count_meg_file_formats,
    count_stim_files,
    created_on,
    get_authors,
    get_dataset_size,
    get_duration,
    get_info_dataset,
    get_institutions,
    get_license,
    get_meeg_header,
    get_nb_subjects,
    get_references_and_links,
    has_participant_tsv,
    list_data_files,
    list_datatypes,
    list_participants_tsv_columns,
    list_sessions,
    list_tasks,
)

# from bids_inventory._update import get_duration


def test_count_meg_file_formats(install_dataset):
    ds004276 = install_dataset("ds004276")
    assert count_meg_file_formats(ds004276) == {
        ".ds": 0,
        "": 0,
        ".fif": 19,
        ".con": 0,
        ".kdf": 0,
        ".raw.mhd": 0,
    }


def test_count_stim_files(install_dataset):
    ds004276 = install_dataset("ds004276")
    assert count_stim_files(ds004276) == 0


def test_created_on(install_dataset):
    ds004276 = install_dataset("ds004276")
    assert created_on(ds004276) == "Fri Sep 23 14:41:43 2022 +0000"


def test_list_data_files(install_dataset):
    ds004276 = install_dataset("ds004276")
    sessions = list_sessions(ds004276)
    assert len(list_data_files(ds004276, sessions=sessions)) == 93


def test_list_participants_tsv_columns(install_dataset):
    ds004276 = install_dataset("ds004276")
    assert list_participants_tsv_columns(ds004276 / "participants.tsv") == [
        "participant_id",
        "age",
        "sex",
        "hand",
    ]


def test_has_participant_tsv(install_dataset):
    ds004276 = install_dataset("ds004276")
    assert has_participant_tsv(ds004276) == (True, True, ["participant_id", "age", "sex", "hand"])


def test_has_participant_tsv_empty(install_dataset):
    ds001339 = install_dataset("ds001339")
    assert has_participant_tsv(ds001339) == (False, False, [])


def test_list_sessions(install_dataset):
    ds004276 = install_dataset("ds004276")
    assert list_sessions(ds004276) == ["20191007"]


def test_list_datatypes(install_dataset):
    ds004276 = install_dataset("ds004276")
    sessions = list_sessions(ds004276)
    assert list_datatypes(ds004276, sessions=sessions) == ["beh", "meg"]


def test_get_nb_subjects(install_dataset):
    ds004276 = install_dataset("ds004276")
    assert get_nb_subjects(ds004276) == 19


def test_list_tasks(install_dataset):
    ds004276 = install_dataset("ds004276")
    sessions = list_sessions(ds004276)
    assert list_tasks(ds004276, sessions=sessions) == ["noise", "words"]


def test_get_license(install_dataset):
    ds004276 = install_dataset("ds004276")
    assert get_license(ds004276) == "CC0"


def test_get_authors(install_dataset):
    ds004276 = install_dataset("ds004276")
    assert get_authors(ds004276) == [
        "Phoebe Gaston",
        "Christian Brodbeck",
        "Colin Phillips",
        "Ellen Lau",
    ]


def test_get_institutions(install_dataset):
    ds004276 = install_dataset("ds004276")
    assert get_institutions(ds004276) == []


def test_get_references_and_links_empty(install_dataset):
    ds004276 = install_dataset("ds004276")
    assert get_references_and_links(ds004276) == []


def test_get_references_and_links_non_empty(install_dataset):
    ds001339 = install_dataset("ds001339")
    assert get_references_and_links(ds001339) == [
        (
            "The social brain is highly sensitive "
            "to the mere presence of social information: "
            "An automated meta-analysis and an independent study"
        )
    ]


def test_get_dataset_size(install_dataset):
    ds004276 = install_dataset("ds004276")
    assert get_dataset_size(ds004276) == "11.6 GB"


def test_get_info_dataset_smoke(install_dataset):
    ds004276 = install_dataset("ds004276")
    get_info_dataset(ds004276, "")


def test_get_duration(install_dataset):
    ds001339 = install_dataset("ds001339")
    sessions = list_sessions(ds001339)
    datatypes = list_datatypes(ds001339, sessions=sessions)
    tasks = list_tasks(ds001339, sessions=sessions)
    assert get_duration(ds001339, datatypes, tasks) == {
        "func": {"iaps": [(0, np.nan), (0, np.nan), (0, np.nan), (0, np.nan), (0, np.nan)]}
    }


def test_get_duration_ds000002(install_dataset):
    ds000002 = install_dataset("ds000002")
    sessions = list_sessions(ds000002)
    datatypes = list_datatypes(ds000002, sessions=sessions)
    tasks = list_tasks(ds000002, sessions=sessions)
    durations = get_duration(ds000002, datatypes, tasks)
    assert list(durations["func"].keys()) == [
        "deterministicclassification",
        "mixedeventrelatedprobe",
        "probabilisticclassification",
    ]
    assert durations == {
        "func": {
            "deterministicclassification": [(180, 2.0), (180, 2.0)],
            "mixedeventrelatedprobe": [(237, 2.0), (237, 2.0)],
            "probabilisticclassification": [(180, 2.0), (180, 2.0)],
        }
    }


def test_get_duration_ds002041(install_dataset):
    ds002041 = install_dataset("ds002041")
    sessions = list_sessions(ds002041)
    datatypes = list_datatypes(ds002041, sessions=sessions)
    tasks = list_tasks(ds002041, sessions=sessions)
    get_duration(ds002041, datatypes, tasks)


def test_get_meeg_header_unreadable(tmp_path):
    """A malformed header should be skipped with a warning, not stop the update."""
    from datalad import api

    ds = api.create(tmp_path / "ds", result_renderer="disabled")
    eeg = ds.pathobj / "sub-01" / "eeg"
    eeg.mkdir(parents=True)
    header = eeg / "sub-01_task-rest_eeg.vhdr"
    header.write_bytes(b"\x00\x05\x16\x07\x00\x02Mac OS X")
    header.with_suffix(".vmrk").write_bytes(b"")
    ds.save(result_renderer="disabled")

    with pytest.warns(UserWarning, match="Could not read header"):
        assert get_meeg_header(ds.pathobj, header) == (None, 0)
