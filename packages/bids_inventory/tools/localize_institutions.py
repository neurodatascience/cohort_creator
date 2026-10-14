"""Plot institutions locations.

Geocodes the institutions found in the inventory with Nominatim (OpenStreetMap)
and saves them to locations.tsv.
Institutions already in locations.tsv are not geocoded again:
delete the file to geocode all of them again.

Usage: python localize_institutions.py
(needs geopy: pip install geopy)
"""

import re
from pathlib import Path

import pandas as pd
import plotly.express as px
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from geopy.location import Location
from rich import print

from bids_inventory import load_inventory

LOCATIONS_FILE = Path(__file__).parent / "locations.tsv"
FIGURE_FILE = Path(__file__).parent / "locations.html"

COLUMNS = ["name", "count", "address", "city", "country", "nb_subjects", "latitude", "longitude"]

# values that are not part of an address
PLACEHOLDERS = re.compile(
    r"^(n/?a|none|null|unknown|anon(ymous|ymized)?|value was not specified|not specified|-)$",
    re.IGNORECASE,
)
# address templates that were not filled in, for example "Street StreetNo, City, ZIP"
TEMPLATE_WORDS = re.compile(
    r"^((street|streetno|street ?number|city|district|state|zip|zip ?code|postal ?code)\s*)+$",
    re.IGNORECASE,
)

# only geocode a few institutions, for testing
DEBUG = False


def main() -> None:
    locations = get_all_locations(load_inventory())
    locations.to_csv(LOCATIONS_FILE, index=False, sep="\t")
    print(f"Saved to {LOCATIONS_FILE}")

    located = locations.dropna(subset=["latitude", "longitude"])
    fig = px.scatter_geo(
        located,
        lat="latitude",
        lon="longitude",
        hover_name="address",
        projection="natural earth",
        size="count",
    )
    fig.write_html(FIGURE_FILE)
    print(f"Saved to {FIGURE_FILE}")
    fig.show()


def count_institutions(df: pd.DataFrame) -> pd.DataFrame:
    """Count the datasets and subjects of each institution of the inventory."""
    counts: dict[str, dict[str, int]] = {}
    for row in df.itertuples():
        for institution in row.institutions or []:
            if not isinstance(institution, str) or not clean_address(institution):
                continue
            counts.setdefault(institution, {"count": 0, "nb_subjects": 0})
            counts[institution]["count"] += 1
            if pd.notna(row.nb_subjects):
                counts[institution]["nb_subjects"] += int(row.nb_subjects)
    return pd.DataFrame(
        [{"name": name, **values} for name, values in sorted(counts.items())],
        columns=["name", "count", "nb_subjects"],
    )


def clean_address(institution: str) -> str:
    """Turn an institution string into an address to geocode.

    Removes the placeholders that some datasets use ("n/a", "Anon"...).
    """
    tokens = [x.strip() for x in institution.split(",")]
    tokens = [x for x in tokens if x and not PLACEHOLDERS.match(x) and not TEMPLATE_WORDS.match(x)]
    return ", ".join(x.replace("_", " ").replace("/", " ") for x in tokens)


def get_all_locations(df: pd.DataFrame) -> pd.DataFrame:
    """Geocode the institutions of the inventory, reusing those in locations.tsv."""
    institutions = count_institutions(df)

    known = pd.DataFrame(columns=COLUMNS)
    if LOCATIONS_FILE.exists():
        known = pd.read_csv(LOCATIONS_FILE, sep="\t")
    known = known.drop_duplicates("name").set_index("name")

    to_geocode = [x for x in institutions["name"] if x not in known.index]
    print(f"{len(institutions)} institutions, {len(to_geocode)} not geocoded yet")
    if DEBUG:
        to_geocode = to_geocode[:3]

    geolocator = Nominatim(user_agent="bids-inventory-institutions", timeout=10)
    # Nominatim usage policy: at most 1 request per second
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, max_retries=2)

    new = {}
    for name in to_geocode:
        address = clean_address(name)
        print(f"[blue]{address}")
        location = _get_location(geocode, address)
        if location is None:
            print("    [red]not found")
            new[name] = {}
            continue
        print(f"    [green]{location.address}")
        details = location.raw.get("address", {})
        new[name] = {
            "address": location.address,
            "city": details.get("city") or details.get("town") or details.get("village"),
            "country": details.get("country"),
            "latitude": location.latitude,
            "longitude": location.longitude,
        }

    rows = []
    for institution in institutions.itertuples():
        if institution.name in new:
            location = new[institution.name]
        elif institution.name in known.index:
            location = known.loc[institution.name].to_dict()
        else:  # not geocoded in debug mode
            location = {}
        rows.append(
            {
                "name": institution.name,
                "count": institution.count,
                "address": location.get("address"),
                "city": location.get("city"),
                "country": location.get("country"),
                "nb_subjects": institution.nb_subjects,
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
            }
        )
    return pd.DataFrame(rows, columns=COLUMNS)


def _get_location(geocode: RateLimiter, address: str) -> None | Location:
    """Geocode an address, then parts of it if it is not found."""
    if not address:
        return None
    try:
        if location := geocode(address, addressdetails=True):
            return location
    except Exception as e:
        print(f"    [red]{e!r}")
    tokens = [x.strip() for x in address.split(",")]
    if len(tokens) > 1:
        # try without the first part (often a department), then only with it
        return _get_location(geocode, ", ".join(tokens[1:])) or _get_location(geocode, tokens[0])
    return None


if __name__ == "__main__":
    main()
