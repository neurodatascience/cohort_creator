import json

import pytest

from bids_inventory.listing import _data_dir

# needs the 'update' extra
pytest.importorskip("pydantic")

from pydantic import ValidationError  # noqa: E402

from bids_inventory.models import BidsDataset, columns_description  # noqa: E402


def test_columns_description_is_up_to_date():
    """columns_description.json is generated from the model."""
    with open(_data_dir() / "columns_description.json") as f:
        on_disk = json.load(f)
    assert on_disk == columns_description(), (
        "columns_description.json is out of date: "
        "regenerate it with 'python -m bids_inventory.models'"
    )


def test_all_fields_are_described():
    for name, column in columns_description()["Columns"].items():
        assert column["Description"], name
        assert column["Format"], name


def test_assignment_is_validated():
    dataset = BidsDataset(name="ds000001")
    dataset.nb_subjects = 16
    with pytest.raises(ValidationError):
        dataset.nb_subjects = "sixteen"
    with pytest.raises(ValidationError):
        dataset.not_a_field = 1


def test_new_dataset_has_all_fields():
    """A dataset with only a name can be added to the listing."""
    dataset = BidsDataset(name="ds000001").model_dump()
    assert list(dataset) == list(BidsDataset.model_fields)
    assert dataset["fmriprep"] is None
    assert dataset["tasks"] == []


def test_duration():
    dataset = BidsDataset(
        name="ds000001",
        duration={"func": {"rest": [(180, 2.0)]}, "pet": [(0, float("nan"))]},
    )
    assert dataset.duration["func"]["rest"] == [(180, 2.0)]
