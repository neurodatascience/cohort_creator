"""Plot institutions locations.

Geocodes the institutions found in the inventory with Nominatim (OpenStreetMap)
and saves them to locations.tsv: one row per location,
with all the institution names found at this location in the ``names`` column
(as a JSON list).

Institutions already in locations.tsv are not geocoded again:
delete the file to geocode all of them again.

Usage: python localize_institutions.py
(needs geopy: pip install geopy)
"""

import json
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

COLUMNS = [
    "name",
    "count",
    "address",
    "city",
    "country",
    "nb_subjects",
    "latitude",
    "longitude",
    "names",
]
LOCATION_COLUMNS = ["address", "city", "country", "latitude", "longitude"]

# values that are not part of an address
PLACEHOLDERS = re.compile(
    r"^(n/?a|none|null|unknown|anon(ymous|ymized)?|value was not specified|not specified|-)$",
    re.IGNORECASE,
)
# words of the address template of some DICOM converters: "Street StreetNo,City,District,ZIP"
TEMPLATE_WORDS = {"street", "streetno", "city", "district", "zip"}
# scanner identifiers added to some addresses, for example "336C48"
SCANNER_ID = re.compile(r"^(?=.*[0-9])(?=.*[a-fA-F])[0-9a-fA-F]{6}$")

# only geocode a few institutions, for testing
DEBUG = False


def main() -> None:
    locations = get_all_locations(load_inventory())
    locations.to_csv(LOCATIONS_FILE, index=False, sep="\t", lineterminator="\n")
    print(f"Saved {len(locations)} locations to {LOCATIONS_FILE}")

    located = locations.dropna(subset=["latitude", "longitude"])
    fig = px.scatter_geo(
        located,
        lat="latitude",
        lon="longitude",
        hover_name="name",
        hover_data=["address", "count", "nb_subjects"],
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

    Removes placeholders ("n/a", "Anon"...), unfilled address templates
    ("Street_StreetNo_City_District_ZIP") and scanner identifiers ("336C48").
    """
    # the template can be spread over several parts: "Street StreetNo,City,District,KR,ZIP"
    is_template = "streetno" in institution.lower()
    parts = []
    for part in institution.split(","):
        part = part.strip()
        if not part or PLACEHOLDERS.match(part):
            continue
        words = part.replace("_", " ").replace("/", " ").split()
        words = [
            word
            for word in words
            if not SCANNER_ID.match(word) and not (is_template and word.lower() in TEMPLATE_WORDS)
        ]
        if words:
            parts.append(" ".join(words))
    return ", ".join(parts)


def get_all_locations(df: pd.DataFrame) -> pd.DataFrame:
    """Geocode the institutions of the inventory and merge those at the same location.

    Reuses the locations of the institutions already in locations.tsv.
    """
    institutions = count_institutions(df)
    known = _known_locations()

    to_geocode = sorted({clean_address(x) for x in institutions["name"] if x not in known})
    print(f"{len(institutions)} institutions, {len(to_geocode)} addresses not geocoded yet")
    if DEBUG:
        to_geocode = to_geocode[:3]

    geolocator = Nominatim(user_agent="bids-inventory-institutions", timeout=10)
    # Nominatim usage policy: at most 1 request per second
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, max_retries=2)

    geocoded: dict[str, dict[str, object]] = {}
    for address in to_geocode:
        print(f"[blue]{address}")
        location = _get_location(geocode, address)
        if location is None:
            print("    [red]not found")
            geocoded[address] = {}
            continue
        print(f"    [green]{location.address}")
        details = location.raw.get("address", {})
        geocoded[address] = {
            "address": location.address,
            "city": details.get("city") or details.get("town") or details.get("village"),
            "country": details.get("country"),
            "latitude": location.latitude,
            "longitude": location.longitude,
        }

    rows = []
    for institution in institutions.itertuples():
        if institution.name in known:
            location = known[institution.name]
        else:  # not geocoded in debug mode
            location = geocoded.get(clean_address(institution.name), {})
        rows.append(
            {
                "name": institution.name,
                "count": institution.count,
                "nb_subjects": institution.nb_subjects,
                **{k: location.get(k) for k in LOCATION_COLUMNS},
            }
        )
    return merge_locations(pd.DataFrame(rows))


def merge_locations(institutions: pd.DataFrame) -> pd.DataFrame:
    """Merge the institutions found at the same location.

    The name of a location is the name of its institution found in most datasets.
    Institutions without location are kept as they are.
    """
    located = institutions.dropna(subset=["address"])
    rows = []
    for _, group in located.groupby("address", sort=False):
        group = group.sort_values(["count", "name"], ascending=[False, True])
        first = group.iloc[0]
        rows.append(
            {
                "name": first["name"],
                "count": group["count"].sum(),
                "nb_subjects": group["nb_subjects"].sum(),
                **{k: first[k] for k in LOCATION_COLUMNS},
                "names": json.dumps(sorted(group["name"]), ensure_ascii=False),
            }
        )
    for _, row in institutions[institutions["address"].isna()].iterrows():
        rows.append({**row.to_dict(), "names": json.dumps([row["name"]], ensure_ascii=False)})
    return pd.DataFrame(rows, columns=COLUMNS).sort_values("name", ignore_index=True)


def _known_locations() -> dict[str, dict[str, object]]:
    """Return the location of each institution name already in locations.tsv."""
    if not LOCATIONS_FILE.exists():
        return {}
    locations = pd.read_csv(LOCATIONS_FILE, sep="\t")
    if "names" not in locations:  # file saved before institutions were merged
        locations["names"] = locations["name"].apply(lambda x: json.dumps([x]))
    known = {}
    for _, row in locations.iterrows():
        location = {k: (None if pd.isna(row[k]) else row[k]) for k in LOCATION_COLUMNS}
        for name in json.loads(row["names"]):
            known[name] = location
    return known


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
