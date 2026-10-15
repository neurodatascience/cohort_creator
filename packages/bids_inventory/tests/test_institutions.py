import pandas as pd
import pytest

from bids_inventory.institutions import (
    UNLOCATED,
    clean_address,
    count_institutions,
    institutions_locations,
    load_institutions,
    new_institution,
)


@pytest.fixture
def institutions():
    geneva = new_institution(
        {"address": "Campus Biotech", "city": "Geneva", "latitude": 46.2, "longitude": 6.1}
    )
    geneva["AlternativeNames"] = ["BBL_-_University_of_Geneva"]
    unlocated = new_institution()
    unlocated["AlternativeNames"] = ["Somewhere"]
    return {"BBL - University of Geneva": geneva, UNLOCATED: unlocated}


def test_count_institutions():
    df = pd.DataFrame(
        {
            "institutions": [["BBL_-_University_of_Geneva"], ["n/a", None], ["Somewhere"], []],
            "nb_subjects": [10, 5, 3, 1],
        }
    )
    counts = count_institutions(df)
    # placeholders and missing names are not counted
    assert counts["name"].tolist() == ["BBL_-_University_of_Geneva", "Somewhere"]
    assert counts["nb_subjects"].tolist() == [10, 3]


def test_institutions_locations(institutions):
    counts = pd.DataFrame(
        {
            "name": ["BBL - University of Geneva", "BBL_-_University_of_Geneva", "Somewhere"],
            "count": [1, 2, 4],
            "nb_subjects": [10, 20, 40],
        }
    )
    locations = institutions_locations(institutions, counts).set_index("name")

    # alternative names are counted with their institution
    assert locations.loc["BBL - University of Geneva", "count"] == 3
    assert locations.loc["BBL - University of Geneva", "nb_subjects"] == 30
    assert locations.loc["BBL - University of Geneva", "latitude"] == 46.2
    assert pd.isna(locations.loc[UNLOCATED, "latitude"])


def test_institutions_json():
    """The packaged institutions.json has the expected format."""
    institutions = load_institutions()
    fields = {"AlternativeNames", "Address", "City", "Country", "Latitude", "Longitude"}
    assert all(set(x) == fields for x in institutions.values())
    for institution in institutions.values():
        for coordinate in ["Latitude", "Longitude"]:
            assert institution[coordinate] is None or isinstance(institution[coordinate], float)


def test_clean_address():
    assert clean_address("Anon, Anon") == ""
    assert clean_address("SKKU, Street StreetNo,City/40058d/,District,KR,ZIP") == "SKKU, KR"


def test_institutions_map(institutions):
    pytest.importorskip("plotly")
    from bids_inventory._plotting import institutions_map

    counts = pd.DataFrame(
        {
            "name": ["BBL_-_University_of_Geneva", "Somewhere"],
            "count": [2, 4],
            "nb_subjects": [1, 1],
        }
    )
    fig = institutions_map(institutions_locations(institutions, counts))
    # only the located institutions are plotted
    assert list(fig.data[0].lat) == [46.2]
