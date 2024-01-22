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


@pytest.fixture
def install_dataset():
    def _install_dataset(dataset_name: str):
        output_path = Path(__file__).parent / "data" / "tmp" / dataset_name
        output_path.mkdir(exist_ok=True, parents=True)
        if not (output_path / "dataset_description.json").exists():
            api.install(
                path=output_path, source=f"https://github.com/OpenNeuroDatasets/{dataset_name}"
            )
        return output_path

    return _install_dataset
