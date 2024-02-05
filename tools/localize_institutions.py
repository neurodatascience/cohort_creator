"""Plot institutions locations."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import pandas as pd
import plotly.express as px
from geopy.geocoders import Nominatim
from geopy.location import Location
from rich import print

from cohort_creator.data.utils import known_datasets_df, wrangle_data

DEBUG = False


def main() -> None:
    df = wrangle_data(known_datasets_df())

    _get_all_locations(df)

    locations = pd.read_csv(Path("locations.tsv"), sep="\t")

    fig = px.scatter_geo(
        locations,
        lat=locations.latitude,
        lon=locations.longitude,
        hover_name="address",
        projection="natural earth",
        size="count",
    )
    fig.show()


class INSTITUTION(TypedDict):
    name: None | str
    count: int
    address: None | str
    city: None | str
    country: None | str
    latitude: None | str
    longitude: None | str
    nb_subjects: int


def _get_all_locations(df: pd.DataFrame) -> None:
    institutions_list = []
    for row in df.itertuples():
        institutions_list.extend(iter(row.institutions))

    institutions: dict[str, INSTITUTION] = {
        i: {
            "name": None,
            "count": 0,
            "address": None,
            "city": None,
            "country": None,
            "latitude": None,
            "longitude": None,
            "nb_subjects": 0,
        }
        for i in sorted(list(set(institutions_list)))
    }
    for row in df.itertuples():
        for i in row.institutions:
            institutions[i]["count"] += 1
            institutions[i]["nb_subjects"] += row.nb_subjects
    print(institutions)

    # calling the Nominatim tool and create Nominatim class
    geolocator = Nominatim(user_agent="bids-institutions")

    i = 0
    for key in institutions:
        # entering the location name
        address = key.replace("_", " ").replace("/", " ")
        print(f"[blue]{address}")
        if location := _get_location(geolocator, address):
            i += 1
            print(f"    [green]{location.address}")
            print(f"    [green]{(location.latitude, location.longitude)}")
            institutions[key]["address"] = location.address
            institutions[key]["city"] = location.raw.get("address").get("city")
            institutions[key]["country"] = location.raw.get("address").get("country")
            institutions[key]["latitude"] = location.latitude
            institutions[key]["longitude"] = location.longitude
            if DEBUG and i > 3:
                break

    data: dict[str, list[str | int | None]] = {
        "name": [],
        "count": [],
        "address": [],
        "city": [],
        "country": [],
        "nb_subjects": [],
        "latitude": [],
        "longitude": [],
    }
    for key, value in institutions.items():
        data["name"].append(key)
        for k, v in data.items():
            if k != "name":
                v.append(value[k])
    df = pd.DataFrame(data)
    df = df.replace(r"^\s*$", "n/a", regex=True)
    df.to_csv("locations.tsv", index=False, sep="\t")


def _get_location(geolocator: Nominatim, address: str) -> None | Location:
    print(f"   {address}")
    location = None
    try:
        location = geolocator.geocode(address, addressdetails=True)
    except Exception:
        ...
    if location:
        return location
    if "," not in address:
        return None

    tokens = address.split(",")
    if len(address) > 1:
        tmp = " ".join(tokens[1:])
        if location := _get_location(geolocator, tmp) or _get_location(geolocator, tokens[0]):
            return location
    return None


if __name__ == "__main__":
    main()
