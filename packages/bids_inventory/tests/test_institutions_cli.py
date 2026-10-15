"""Tests of `bids_inventory institutions`, without network access."""

import json

import pandas as pd
import pytest

# needs the 'institutions' extra
pytest.importorskip("geopy")
pytest.importorskip("rapidfuzz")

from bids_inventory import _cli, _institutions_update, institutions  # noqa: E402
from bids_inventory._cli import cli  # noqa: E402
from bids_inventory.institutions import UNLOCATED, new_institution  # noqa: E402

GENEVA = {
    "address": "Campus Biotech, Chemin des Mines 9, Genève, Suisse",
    "city": "Genève",
    "country": "Suisse",
    "latitude": 46.2,
    "longitude": 6.1,
}


@pytest.fixture
def institutions_file(tmp_path, monkeypatch):
    """Return an institutions.json with one located institution, with a small inventory."""
    institutions_json = tmp_path / "institutions.json"
    geneva = new_institution(GENEVA)
    institutions_json.write_text(json.dumps({"Campus Biotech, Geneva": geneva}))
    monkeypatch.setattr(institutions, "INSTITUTIONS_FILE", institutions_json)

    inventory = pd.DataFrame(
        {
            "institutions": [
                ["Campus Biotech, Geneva"],
                ["Fondation Campus Biotech, Geneve, CH"],
                ["Nowhere Institute, Atlantis"],
                ["Somewhere else"],
            ],
            "nb_subjects": [10, 20, 30, 40],
        }
    )
    monkeypatch.setattr("bids_inventory.load_inventory", lambda: inventory)
    return institutions_json


class FakeLocation:
    def __init__(self, location):
        self.address = location["address"]
        self.latitude, self.longitude = location["latitude"], location["longitude"]
        self.raw = {"address": {"city": location["city"], "country": location["country"]}}


def test_update(institutions_file, monkeypatch):
    locations = {
        # same address as an institution already in the file
        "Fondation Campus Biotech, Geneve, CH": FakeLocation(GENEVA),
        "Somewhere else": FakeLocation({**GENEVA, "address": "Elsewhere", "city": "Bern"}),
    }
    calls = []

    def fake_get_location(geocode, address):
        calls.append(address)
        return locations.get(address)

    monkeypatch.setattr(_institutions_update, "_get_location", fake_get_location)

    cli(["bids_inventory", "institutions", "update"])

    saved = json.loads(institutions_file.read_text())
    assert saved["Campus Biotech, Geneva"]["AlternativeNames"] == [
        "Fondation Campus Biotech, Geneve, CH"
    ]
    assert saved["Somewhere else"]["City"] == "Bern"
    assert saved[UNLOCATED]["AlternativeNames"] == ["Nowhere Institute, Atlantis"]

    # running it again does not geocode anything
    calls.clear()
    cli(["bids_inventory", "institutions", "update"])
    assert calls == []


def test_update_can_resume(institutions_file, monkeypatch):
    calls = []

    def stop_after_one(geocode, address):
        if calls:
            raise KeyboardInterrupt
        calls.append(address)
        return None

    monkeypatch.setattr(_institutions_update, "_get_location", stop_after_one)
    with pytest.raises(KeyboardInterrupt):
        cli(["bids_inventory", "institutions", "update"])

    # the first address was saved before the interruption
    saved = json.loads(institutions_file.read_text())
    assert len(saved[UNLOCATED]["AlternativeNames"]) == 1


def test_suggest_and_apply_matches(institutions_file, tmp_path, monkeypatch):
    institutions_json = json.loads(institutions_file.read_text())
    unlocated = new_institution()
    unlocated["AlternativeNames"] = ["Campus Biotech Geneva"]
    institutions_json[UNLOCATED] = unlocated
    institutions_file.write_text(json.dumps(institutions_json))
    matches_file = tmp_path / "matches.tsv"

    cli(["bids_inventory", "institutions", "suggest", "--output", str(matches_file)])

    matches = pd.read_csv(matches_file, sep="\t", dtype=str, keep_default_na=False)
    pair = {"Campus Biotech, Geneva", "Campus Biotech Geneva"}
    assert any({r.institution_1, r.institution_2} == pair for r in matches.itertuples())

    matches["accept"] = "y"
    matches.to_csv(matches_file, sep="\t", index=False)
    cli(["bids_inventory", "institutions", "apply-matches", "--matches", str(matches_file)])

    saved = json.loads(institutions_file.read_text())
    assert "Campus Biotech Geneva" in saved["Campus Biotech, Geneva"]["AlternativeNames"]
    assert UNLOCATED not in saved


def test_apply_matches_missing_file(institutions_file, tmp_path):
    with pytest.raises(SystemExit):
        cli(["bids_inventory", "institutions", "apply-matches", "--matches", str(tmp_path / "x")])
    assert _cli  # the CLI module is importable without the extra
