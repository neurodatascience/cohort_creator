from bids_inventory._utils import glob_files


def test_glob_files_ignores_macos_metadata(tmp_path):
    """MacOS AppleDouble files (._*) must not be mistaken for data files."""
    eeg = tmp_path / "sub-01" / "eeg"
    eeg.mkdir(parents=True)
    (eeg / "sub-01_task-rest_eeg.vhdr").touch()
    (eeg / "._sub-01_task-rest_eeg.vhdr").touch()
    (tmp_path / "._sub-02" / "eeg").mkdir(parents=True)
    (tmp_path / "._sub-02" / "eeg" / "sub-02_task-rest_eeg.vhdr").touch()

    files = glob_files(tmp_path, "sub-*/**/eeg/*_eeg.vhdr") + glob_files(tmp_path, "*/eeg/*.vhdr")

    assert {x.name for x in files} == {"sub-01_task-rest_eeg.vhdr"}
