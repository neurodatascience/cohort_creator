"""Test bagel related module."""
from __future__ import annotations

from cohort_creator.bagelify import _new_bagel
from cohort_creator.bagelify import bagelify


def test_bagelify(bids_examples):
    bagel = _new_bagel()
    bagel = bagelify(
        bagel=bagel,
        raw_path=bids_examples / "ds001",
        derivative_path=bids_examples / "ds000001-fmriprep",
    )

    assert len(bagel["bids_id"]) == 16
    assert set(bagel["dataset_id"]) == {"ds001"}
    assert set(bagel["pipeline_name"]) == {"fMRIPrep"}
    assert set(bagel["has_mri_data"]) == {"TRUE"}
    assert set(bagel["pipeline_version"]) == {"20.2.0rc0"}
    assert set(bagel["session"]) == {"1"}
    assert set(bagel["pipeline_complete"]) == {"FAIL", "SUCCESS"}


def test_bagelify_unavailable(bids_examples):
    bagel = _new_bagel()
    bagel = bagelify(
        bagel=bagel, raw_path=bids_examples / "asl001", derivative_path=bids_examples / "foo"
    )

    assert len(bagel["bids_id"]) == 1
    assert set(bagel["dataset_id"]) == {"asl001"}
    assert set(bagel["pipeline_name"]) == {"foo"}
    assert set(bagel["has_mri_data"]) == {"TRUE"}
    assert set(bagel["pipeline_version"]) == {"UNKNOWN"}
    assert set(bagel["session"]) == {"1"}
    assert set(bagel["pipeline_complete"]) == {"UNAVAILABLE"}
