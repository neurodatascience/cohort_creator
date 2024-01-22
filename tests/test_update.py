from __future__ import annotations

import numpy as np

from cohort_creator.data._update import count_meg_file_formats
from cohort_creator.data._update import count_stim_files
from cohort_creator.data._update import created_on
from cohort_creator.data._update import get_authors
from cohort_creator.data._update import get_dataset_size
from cohort_creator.data._update import get_duration
from cohort_creator.data._update import get_info_dataset
from cohort_creator.data._update import get_institutions
from cohort_creator.data._update import get_license
from cohort_creator.data._update import get_nb_subjects
from cohort_creator.data._update import get_references_and_links
from cohort_creator.data._update import has_participant_tsv
from cohort_creator.data._update import list_data_files
from cohort_creator.data._update import list_datatypes
from cohort_creator.data._update import list_participants_tsv_columns
from cohort_creator.data._update import list_sessions
from cohort_creator.data._update import list_tasks

# from cohort_creator.data._update import get_duration


def test_count_meg_file_formats(ds004276):
    assert count_meg_file_formats(ds004276) == {
        ".ds": 0,
        "": 0,
        ".fif": 19,
        ".con": 0,
        ".kdf": 0,
        ".raw.mhd": 0,
    }


def test_count_stim_files(ds004276):
    assert count_stim_files(ds004276) == 0


def test_created_on(ds004276):
    assert created_on(ds004276) == "Fri Sep 23 14:41:43 2022 +0000"


def test_list_data_files(ds004276):
    sessions = list_sessions(ds004276)
    assert len(list_data_files(ds004276, sessions=sessions)) == 93


def test_list_participants_tsv_columns(ds004276):
    assert list_participants_tsv_columns(ds004276 / "participants.tsv") == [
        "participant_id",
        "age",
        "sex",
        "hand",
    ]


def test_has_participant_tsv(ds004276):
    assert has_participant_tsv(ds004276) == (True, True, ["participant_id", "age", "sex", "hand"])


def test_has_participant_tsv_empty(ds001339):
    assert has_participant_tsv(ds001339) == (False, False, [])


def test_list_sessions(ds004276):
    assert list_sessions(ds004276) == ["20191007"]


def test_list_datatypes(ds004276):
    sessions = list_sessions(ds004276)
    assert list_datatypes(ds004276, sessions=sessions) == ["beh", "meg"]


def test_get_nb_subjects(ds004276):
    assert get_nb_subjects(ds004276) == 19


def test_list_tasks(ds004276):
    sessions = list_sessions(ds004276)
    assert list_tasks(ds004276, sessions=sessions) == ["noise", "words"]


def test_get_license(ds004276):
    assert get_license(ds004276) == "CC0"


def test_get_authors(ds004276):
    assert get_authors(ds004276) == [
        "Phoebe Gaston",
        "Christian Brodbeck",
        "Colin Phillips",
        "Ellen Lau",
    ]


def test_get_institutions(ds004276):
    assert get_institutions(ds004276) == []


def test_get_references_and_links_empty(ds004276):
    assert get_references_and_links(ds004276) == []


def test_get_references_and_links_non_empty(ds001339):
    assert get_references_and_links(ds001339) == [
        (
            "The social brain is highly sensitive "
            "to the mere presence of social information: "
            "An automated meta-analysis and an independent study"
        )
    ]


def test_get_dataset_size(install_dataset):
    ds004276 = install_dataset('ds004276')
    assert get_dataset_size(ds004276) == "11.6 GB"


def test_get_info_dataset_smoke(install_dataset):
    ds004276 = install_dataset('ds004276')
    get_info_dataset(ds004276, "")


def test_get_duration(install_dataset):
    ds001339 = install_dataset('ds001339')
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