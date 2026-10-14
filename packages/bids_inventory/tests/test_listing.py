import numpy as np

from bids_inventory.listing import (
    _convert_duration,
    _load_known_datasets,
    _openneuro_listing,
    is_known_dataset,
    save_known_datasets,
)


def test_is_known_dataset():
    assert is_known_dataset("ds000001")
    assert not is_known_dataset("foo")


def test_convert_duration_per_task():
    """Runs of one task must not leak into the other tasks of the same datatype."""
    duration = {"func": {"a": [(180, 2.0), (180, 2.0)], "b": [[237, 2.0]]}}
    expected = {"func": {"a": [360.0, 360.0], "b": [474.0]}}
    assert _convert_duration(duration) == expected
    # converting an already converted value must not change it
    assert _convert_duration(expected) == expected


def test_convert_duration_unknown():
    """Runs with an unknown duration are dropped and tasks without runs are None."""
    duration = {"func": {"a": [(0, np.nan), [180, None], None, 0, 360.0], "b": []}}
    assert _convert_duration(duration) == {"func": {"a": [360.0], "b": None}}


def test_save_known_datasets_round_trip(tmp_path):
    """Loading and saving a listing must not change it."""
    output_file = tmp_path / "openneuro.jsonl"
    save_known_datasets(_load_known_datasets(_openneuro_listing()), output_file)
    assert output_file.read_text() == _openneuro_listing().read_text()


def test_skipped_datasets_not_in_listing():
    """Datasets in the skip list have a reason and are not in the listing."""
    from bids_inventory.listing import known_datasets_df, skipped_datasets

    skipped = skipped_datasets()
    assert skipped
    assert all(reason for reason in skipped.values())
    assert not set(skipped) & set(known_datasets_df()["name"])


def test_sizes_are_sizes():
    """The size of each dataset is a size, for example '2.2 GB', or missing."""
    from bids_inventory.listing import known_datasets_df

    sizes = known_datasets_df()["size"].dropna()
    not_sizes = sizes[~sizes.astype(str).str.fullmatch(r"[0-9.]+ ?[KMGTP]?B")]
    assert not_sizes.empty, not_sizes.tolist()[:10]


def _write_listing(path, names):
    path.write_text("".join(f'{{"name": "{x}", "size": "1.0 GB"}}\n' for x in names))


def test_remove_datasets(tmp_path):
    from bids_inventory.listing import remove_datasets

    listing = tmp_path / "openneuro.jsonl"
    _write_listing(listing, ["ds000001", "ds000002", "ds000003"])
    reindexed = tmp_path / "openneuro.jsonl.reindexed"
    reindexed.write_text("ds000001\nds000002\n")

    assert remove_datasets(["ds000002", "ds999999"], listing) == ["ds000002"]

    # the other entries are kept as they are
    assert listing.read_text() == (
        '{"name": "ds000001", "size": "1.0 GB"}\n{"name": "ds000003", "size": "1.0 GB"}\n'
    )
    # a re-index in progress indexes them again
    assert reindexed.read_text() == "ds000001\n"


def test_cli_remove(tmp_path, monkeypatch, caplog):
    from bids_inventory import listing as listing_module
    from bids_inventory._cli import cli

    listing = tmp_path / "openneuro.jsonl"
    _write_listing(listing, ["ds000001", "ds000002"])
    monkeypatch.setattr(listing_module, "_openneuro_listing", lambda: listing)

    cli(["bids_inventory", "remove", "ds000001", "ds999999"])

    assert listing.read_text() == '{"name": "ds000002", "size": "1.0 GB"}\n'
    assert "Removed 1 datasets" in caplog.text
    assert "Not in the listing: ds999999" in caplog.text
