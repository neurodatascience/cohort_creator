from __future__ import annotations

from pathlib import Path

import pytest
from datalad import api


def root_dir():
    return Path(__file__).parent.parent


def path_test_data():
    return Path(__file__).parent / "data"


@pytest.fixture
def bids_examples():
    return path_test_data() / "bids-examples"


# pin dataset versions so that upstream updates do not change test results
DATASET_VERSIONS = {
    "ds000002": "00002",
    "ds001339": "00003",
    "ds002041": "1.2.1",
    "ds004276": "1.0.0",
}


@pytest.fixture
def install_dataset():
    def _install_dataset(dataset_name: str):
        output_path = Path(__file__).parent / "data" / "tmp" / dataset_name
        output_path.mkdir(exist_ok=True, parents=True)
        if not (output_path / "dataset_description.json").exists():
            api.install(
                path=output_path, source=f"https://github.com/OpenNeuroDatasets/{dataset_name}"
            )
        api.Dataset(output_path).repo.call_git(
            ["checkout", "--quiet", DATASET_VERSIONS[dataset_name]]
        )
        return output_path

    return _install_dataset
