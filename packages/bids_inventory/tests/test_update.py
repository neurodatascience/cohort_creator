import math

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
    """ds001339 has uncompressed .nii files."""
    ds001339 = install_dataset("ds001339")
    sessions = list_sessions(ds001339)
    datatypes = list_datatypes(ds001339, sessions=sessions)
    tasks = list_tasks(ds001339, sessions=sessions)
    assert get_duration(ds001339, datatypes, tasks) == {"func": {"iaps": [(120, 2.0)] * 5}}


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


def test_get_duration_parallel(install_dataset):
    """Reading headers in parallel must give the same durations in the same order."""
    ds000002 = install_dataset("ds000002")
    sessions = list_sessions(ds000002)
    datatypes = list_datatypes(ds000002, sessions=sessions)
    tasks = list_tasks(ds000002, sessions=sessions)
    assert get_duration(ds000002, datatypes, tasks, jobs=4) == get_duration(
        ds000002, datatypes, tasks, jobs=1
    )


def test_get_duration_ds002041(install_dataset):
    ds002041 = install_dataset("ds002041")
    sessions = list_sessions(ds002041)
    datatypes = list_datatypes(ds002041, sessions=sessions)
    tasks = list_tasks(ds002041, sessions=sessions)
    get_duration(ds002041, datatypes, tasks)


def test_get_meeg_header_unreadable(tmp_path, caplog):
    """A malformed header should be skipped with a warning, not stop the update."""
    from datalad import api

    ds = api.create(tmp_path / "ds", result_renderer="disabled")
    eeg = ds.pathobj / "sub-01" / "eeg"
    eeg.mkdir(parents=True)
    header = eeg / "sub-01_task-rest_eeg.vhdr"
    header.write_bytes(b"\x00\x05\x16\x07\x00\x02Mac OS X")
    header.with_suffix(".vmrk").write_bytes(b"")
    ds.save(result_renderer="disabled")

    assert get_meeg_header(ds.pathobj, header) == (None, 0)
    assert "Could not read header of sub-01/eeg/sub-01_task-rest_eeg.vhdr" in caplog.text


def test_get_meeg_header_mne_warnings_are_logged(tmp_path, caplog, recwarn):
    """Warnings raised by MNE while reading a header are logged, not printed."""
    from datalad import api

    ds = api.create(tmp_path / "ds", result_renderer="disabled")
    eeg = ds.pathobj / "sub-01" / "eeg"
    eeg.mkdir(parents=True)
    header = eeg / "sub-01_task-rest_eeg.vhdr"
    header.write_text(
        "Brain Vision Data Exchange Header File Version 1.0\n"
        "[Common Infos]\n"
        "Codepage=UTF-8\n"
        "DataFile=sub-01_task-rest_eeg.eeg\n"
        "MarkerFile=sub-01_task-rest_eye_closed_eeg.vmrk\n"
        "DataFormat=BINARY\n"
        "DataOrientation=MULTIPLEXED\n"
        "NumberOfChannels=1\n"
        "SamplingInterval=1000\n"
        "[Binary Infos]\n"
        "BinaryFormat=INT_16\n"
        "[Channel Infos]\n"
        "Ch1=Fp1,,0.1,µV\n"
    )
    header.with_suffix(".vmrk").write_text("Brain Vision Data Exchange Marker File, Version 1.0\n")
    header.with_suffix(".eeg").write_bytes(b"\x00" * 20)
    ds.save(result_renderer="disabled")
    caplog.set_level("WARNING", logger="bids_inventory")

    info, n_samples = get_meeg_header(ds.pathobj, header)

    assert info["sfreq"] == 1000
    # 20 bytes of INT_16 data for 1 channel
    assert n_samples == 10
    assert "MarkerFile 'sub-01_task-rest_eye_closed_eeg.vmrk' not found" in caplog.text
    assert not [w for w in recwarn if "MarkerFile" in str(w.message)]


def test_install_missing_datasets_in_parallel(tmp_path, monkeypatch, capsys, caplog):
    from bids_inventory import _update

    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(
        _update,
        "list_openneuro_raw",
        lambda use_superdataset, reindex=False: {"ds000001", "ds000002", "ds999999"},
    )
    monkeypatch.setattr(_update, "config_path", lambda *keys: tmp_path)
    (tmp_path / "ds000002").mkdir()
    caplog.set_level("INFO", logger="bids_inventory")

    _update.install_missing_datasets(jobs=3)

    assert (tmp_path / "ds000001" / "dataset_description.json").exists()
    assert "installed: ds000001" in caplog.text
    assert "already present: ds000002" in caplog.text
    assert "not found: ds999999" in caplog.text
    # datalad output must not mess up the progress bar
    assert "install(ok)" not in capsys.readouterr().out


def test_list_datasets_in_dir_can_resume(tmp_path, monkeypatch):
    """An interrupted update keeps the datasets indexed so far and resumes after them."""
    from bids_inventory import _update
    from bids_inventory.listing import _load_known_datasets

    input_dir = tmp_path / "openneuro"
    for name in ["ds000001", "ds000002", "ds000003"]:
        (input_dir / name).mkdir(parents=True)
    output_file = tmp_path / "openneuro.jsonl"

    indexed = []

    def fake_get_info_dataset(dataset_pth, study_prefix, jobs=1):
        if dataset_pth.name == "ds000003" and "stop" in indexed:
            raise KeyboardInterrupt  # someone stops the update
        indexed.append(dataset_pth.name)
        dataset = _update.new_dataset(dataset_pth.name)
        return dataset

    monkeypatch.setattr(_update, "get_info_dataset", fake_get_info_dataset)
    monkeypatch.setattr(_update, "add_derivatives", lambda dataset, *args: dataset)
    monkeypatch.setattr(_update, "known_derivatives", lambda: [])
    monkeypatch.setattr(_update, "_check_dataset", lambda dataset_pth: True)
    monkeypatch.setattr(_update, "enable_S3_remote", lambda dataset_pth: None)
    monkeypatch.setattr(_update, "_get_file", lambda ds, filepath: None)

    # first run is interrupted while indexing ds000003
    indexed.append("stop")
    with pytest.raises(KeyboardInterrupt):
        _update.list_datasets_in_dir(
            _update.init_dataset(), input_dir, debug=False, output_file=output_file
        )
    assert _load_known_datasets(output_file)["name"].tolist() == ["ds000001", "ds000002"]

    # the restart only indexes what is missing
    indexed.clear()
    datasets = _load_known_datasets(output_file).to_dict(orient="list")
    _update.list_datasets_in_dir(datasets, input_dir, debug=False, output_file=output_file)
    assert indexed == ["ds000003"]
    assert _load_known_datasets(output_file)["name"].tolist() == [
        "ds000001",
        "ds000002",
        "ds000003",
    ]
    assert not output_file.with_name("openneuro.jsonl.tmp").exists()


def test_annexed_file_size(tmp_path):
    """The size of a file whose content is not downloaded is read from its annex key."""
    from bids_inventory._update import _annexed_file_size, _brainvision_n_samples

    present = tmp_path / "present.eeg"
    present.write_bytes(b"\x00" * 8)
    assert _annexed_file_size(present) == 8

    not_downloaded = tmp_path / "sub-01_task-rest_eeg.eeg"
    not_downloaded.symlink_to(
        "../.git/annex/objects/q5/pm/SHA256E-s3800016000--5c95f30c.eeg/SHA256E-s3800016000--5c95f30c.eeg"
    )
    assert _annexed_file_size(not_downloaded) == 3800016000
    # ds005486: 66 channels of IEEE_FLOAT_32
    assert _brainvision_n_samples(not_downloaded, "single", 66) == 14394000

    assert _annexed_file_size(tmp_path / "missing.eeg") is None
    assert _brainvision_n_samples(tmp_path / "missing.eeg", "single", 66) is None


@pytest.mark.parametrize(
    "description, expected",
    [
        (None, "n/a"),
        ({}, "n/a"),
        ({"GeneratedBy": [{"Name": "fMRIPrep", "Version": "21.0.1"}]}, "21.0.1"),
        # prefer the entry about the pipeline
        (
            {
                "GeneratedBy": [
                    {"Name": "Manual", "Version": "1"},
                    {"Name": "fMRIPrep", "Version": "23.2.0"},
                ]
            },
            "23.2.0",
        ),
        # BIDS < 1.4
        ({"PipelineDescription": {"Name": "fmriprep", "Version": "1.4.1"}}, "1.4.1"),
        ({"GeneratedBy": [{"Name": "fMRIPrep"}]}, "n/a"),
    ],
)
def test_pipeline_version(description, expected):
    from bids_inventory._update import pipeline_version

    assert pipeline_version(description, "fmriprep") == expected


def test_get_field_strength():
    from bids_inventory._update import get_field_strength

    sidecars = [
        {"MagneticFieldStrength": 3},
        {"MagneticFieldStrength": 3.0},
        {"MagneticFieldStrength": "7T"},
        {"MagneticFieldStrength": "n/a"},
        {"MagneticFieldStrength": 0},
        {"RepetitionTime": 2},
    ]
    assert get_field_strength(sidecars) == [3.0, 7.0]
    assert get_field_strength([]) == []


@pytest.mark.parametrize(
    "version, expected", [("1.8.0", "1.8.0"), ("v1.2.2", "1.2.2"), ("", "n/a")]
)
def test_get_bids_version(tmp_path, version, expected):
    import json

    from bids_inventory._update import get_bids_version

    (tmp_path / "dataset_description.json").write_text(json.dumps({"BIDSVersion": version}))
    assert get_bids_version(tmp_path) == expected
    assert get_bids_version(tmp_path / "missing") == "n/a"


def test_listing_to_dict_adds_new_columns():
    """Listings saved before new columns were added can still be updated."""
    import pandas as pd

    from bids_inventory._update import init_dataset, listing_to_dict

    datasets = listing_to_dict(pd.DataFrame({"name": ["ds000001", "ds000002"]}))
    assert set(datasets) == set(init_dataset())
    assert datasets["bids_version"] == ["n/a", "n/a"]


def test_list_datasets_in_dir_reindex_can_resume(tmp_path, monkeypatch):
    """Re-indexing replaces entries in place and can be resumed."""
    import pandas as pd

    from bids_inventory import _update
    from bids_inventory.listing import _load_known_datasets, save_known_datasets

    input_dir = tmp_path / "openneuro"
    for name in ["ds000001", "ds000002"]:
        (input_dir / name).mkdir(parents=True)
    output_file = tmp_path / "openneuro.jsonl"

    # listing indexed before a new field was added
    old = _update.init_dataset()
    for name in ["ds000001", "ds000002"]:
        _update._add_or_replace(old, _update.new_dataset(name))
    save_known_datasets(pd.DataFrame.from_dict(old), output_file)

    indexed = []

    def fake_get_info_dataset(dataset_pth, study_prefix, jobs=1):
        if dataset_pth.name == "ds000002" and "stop" in indexed:
            raise KeyboardInterrupt
        indexed.append(dataset_pth.name)
        dataset = _update.new_dataset(dataset_pth.name)
        dataset.bids_version = "1.10.0"
        return dataset

    monkeypatch.setattr(_update, "get_info_dataset", fake_get_info_dataset)
    monkeypatch.setattr(_update, "add_derivatives", lambda dataset, *args: dataset)
    monkeypatch.setattr(_update, "known_derivatives", lambda: [])
    monkeypatch.setattr(_update, "_check_dataset", lambda dataset_pth: True)
    monkeypatch.setattr(_update, "enable_S3_remote", lambda dataset_pth: None)
    monkeypatch.setattr(_update, "_get_file", lambda ds, filepath: None)

    def run():
        datasets = _update.listing_to_dict(_load_known_datasets(output_file))
        return _update.list_datasets_in_dir(
            datasets, input_dir, debug=False, output_file=output_file, reindex=True
        )

    # interrupted while re-indexing ds000002
    indexed.append("stop")
    with pytest.raises(KeyboardInterrupt):
        run()
    listing = _load_known_datasets(output_file).set_index("name")
    # the listing stays complete: ds000002 keeps its previous entry
    assert listing.index.tolist() == ["ds000001", "ds000002"]
    assert listing.loc["ds000001", "bids_version"] == "1.10.0"
    assert pd.isna(listing.loc["ds000002", "bids_version"])

    # the restart only re-indexes ds000002
    indexed.clear()
    run()
    assert indexed == ["ds000002"]
    listing = _load_known_datasets(output_file).set_index("name")
    assert listing["bids_version"].tolist() == ["1.10.0", "1.10.0"]
    assert _update._read_reindex_progress(_update.reindex_progress_file(output_file)) == {
        "ds000001",
        "ds000002",
    }


def test_skipped_datasets_are_not_indexed(tmp_path, monkeypatch):
    from bids_inventory import _update

    input_dir = tmp_path / "openneuro"
    for name in ["ds000001", "ds000002"]:
        (input_dir / name).mkdir(parents=True)

    indexed = []

    def fake_get_info_dataset(dataset_pth, study_prefix, jobs=1):
        indexed.append(dataset_pth.name)
        dataset = _update.new_dataset(dataset_pth.name)
        return dataset

    monkeypatch.setattr(_update, "get_info_dataset", fake_get_info_dataset)
    monkeypatch.setattr(_update, "add_derivatives", lambda dataset, *args: dataset)
    monkeypatch.setattr(_update, "known_derivatives", lambda: [])
    monkeypatch.setattr(_update, "_check_dataset", lambda dataset_pth: True)
    monkeypatch.setattr(_update, "enable_S3_remote", lambda dataset_pth: None)
    monkeypatch.setattr(_update, "_get_file", lambda ds, filepath: None)
    monkeypatch.setattr(_update, "skipped_datasets", lambda: {"ds000002": "deleted"})

    datasets = _update.list_datasets_in_dir(_update.init_dataset(), input_dir, debug=False)

    assert indexed == ["ds000001"]
    assert datasets["name"] == ["ds000001"]


def test_get_scan_duration_error_reason(tmp_path, caplog):
    """The error says why the header could not be read."""
    from datalad import api

    from bids_inventory._update import get_scan_duration

    ds = api.create(tmp_path / "ds", result_renderer="disabled")
    bold = ds.pathobj / "sub-01" / "func" / "sub-01_task-rest_bold.nii.gz"
    bold.parent.mkdir(parents=True)
    bold.write_bytes(b"not really a nifti file")
    ds.save(result_renderer="disabled")
    # the content is not available anywhere anymore
    ds.drop(bold, reckless="kill", result_renderer="disabled")

    n_volumes, repetition_time = get_scan_duration(ds.pathobj, bold)
    assert n_volumes == 0
    assert math.isnan(repetition_time)
    assert "Could not get duration for: sub-01/func/sub-01_task-rest_bold.nii.gz (" in caplog.text
    assert "Could not find a usable URL" in caplog.text


def test_get_scan_duration_retries_once(monkeypatch, tmp_path):
    from bids_inventory import _update

    calls = []

    def flaky(dataset_pth, filepath):
        calls.append(filepath)
        return (None, "temporary error") if len(calls) == 1 else ((180, 2.0), "")

    monkeypatch.setattr(_update, "_read_nifti_header", flaky)
    bold = tmp_path / "sub-01_task-rest_bold.nii.gz"
    assert _update.get_scan_duration(tmp_path, bold) == (180, 2.0)
    assert len(calls) == 2


@pytest.mark.parametrize(
    "stdout, stderr, expected",
    [
        (
            "",
            "[INFO] Attempting a clone\n"
            "[ERROR] could not create work tree dir: No space left on device\n"
            "[INFO] Completed clone attempts for Dataset(/data/ds000001)\n",
            "could not create work tree dir: No space left on device",
        ),
        (
            "install(error): /data/ds000001 (dataset) [Failed to clone from any source]\n",
            "[INFO] Completed clone attempts for Dataset(/data/ds000001)\n",
            "install(error): /data/ds000001 (dataset) [Failed to clone from any source]",
        ),
        (
            "",
            "[INFO] init: 1 failed\ngit-annex: fd:19: Data.ByteString.hGetLine: end of file\n",
            "git-annex: fd:19: Data.ByteString.hGetLine: end of file",
        ),
        ("", "", ""),
    ],
)
def test_error_reason(stdout, stderr, expected):
    """The reason of a failure is the error, not datalad's last progress message."""
    from bids_inventory._update import _error_reason

    assert _error_reason(stdout, stderr) == expected
