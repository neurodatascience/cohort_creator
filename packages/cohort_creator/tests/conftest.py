from __future__ import annotations

from pathlib import Path

import pytest


def root_dir():
    return Path(__file__).parent.parent


def path_test_data():
    return Path(__file__).parent / "data"


@pytest.fixture
def bids_examples():
    return path_test_data() / "bids-examples"
