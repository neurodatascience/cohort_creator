"""Locate the institutions of the inventory and plot them.

``bids_inventory/data/institutions.json`` describes each institution:

    "name": {
        "AlternativeNames": ["other names of the same institution found in datasets"],
        "Address": "",
        "City": "",
        "Country": "",
        "Latitude": null,
        "Longitude": null
    }

This file can be edited by hand (to fix a location or to group institutions):
the institutions already in it are never changed by this script.
The names that could not be located are listed in the alternative names
of the "unlocated" entry: to locate one, move it to a new or existing entry.

The institution names of the inventory that are not in it yet are geocoded
with Nominatim (OpenStreetMap). A name located at the same address as an institution
already in the file is added to its alternative names, otherwise it is added as
a new institution (with empty fields if it could not be located).
The file is saved after each geocoded address:
if the script is stopped, run it again to continue where it stopped.

locations.tsv (number of datasets and subjects of each located institution)
and locations.html (map) are then generated from it.

Institutions that are probably the same can be regrouped:

- ``python localize_institutions.py --suggest`` writes institution_matches.tsv
  with the pairs of institutions that are probably the same;
- review it: ``y`` in the ``accept`` column for the pairs to merge;
- ``python localize_institutions.py --apply-matches`` merges them in institutions.json.

Usage: python localize_institutions.py [--suggest | --apply-matches]
(needs geopy, and rapidfuzz and unidecode for --suggest:
pip install geopy rapidfuzz unidecode)
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from geopy.location import Location
from rich import print

from bids_inventory import load_inventory
from bids_inventory.listing import _data_dir

INSTITUTIONS_FILE = _data_dir() / "institutions.json"
# entry of institutions.json listing (in its alternative names) the institutions not located
UNLOCATED = "unlocated"
LOCATIONS_FILE = Path(__file__).parent / "locations.tsv"
FIGURE_FILE = Path(__file__).parent / "locations.html"

COLUMNS = ["name", "count", "nb_subjects", "address", "city", "country", "latitude", "longitude"]

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
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--suggest",
        action="store_true",
        help="Write the pairs of institutions that are probably the same to institution_matches.tsv.",
    )
    group.add_argument(
        "--apply-matches",
        action="store_true",
        help="Merge the pairs accepted in institution_matches.tsv into institutions.json.",
    )
    args = parser.parse_args()

    if args.suggest:
        from match_institutions import MATCHES_FILE, suggest_matches

        matches = suggest_matches(explode_unlocated(load_institutions()), clean_address)
        matches.to_csv(MATCHES_FILE, index=False, sep="\t", lineterminator="\n")
        print(
            f"Saved {len(matches)} possible matches to {MATCHES_FILE}:\n"
            "write 'y' in the 'accept' column of the ones to merge, then run with --apply-matches"
        )
        return

    if args.apply_matches:
        from match_institutions import MATCHES_FILE, apply_matches

        institutions = load_institutions()
        locations = institutions_locations(institutions, count_institutions(load_inventory()))
        counts = dict(zip(locations["name"], locations["count"]))
        matches = pd.read_csv(MATCHES_FILE, sep="\t", dtype=str, keep_default_na=False)
        merged = apply_matches(explode_unlocated(institutions), matches, counts)
        save_institutions(gather_unlocated(merged))
        print(f"Saved {INSTITUTIONS_FILE}")
        return

    df = load_inventory()
    institutions = update_institutions(load_institutions(), count_institutions(df)["name"])

    locations = institutions_locations(institutions, count_institutions(df))
    locations.to_csv(LOCATIONS_FILE, index=False, sep="\t", lineterminator="\n")
    print(f"Saved {len(locations)} institutions to {LOCATIONS_FILE}")

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


def new_institution(location: dict[str, Any] | None = None) -> dict[str, Any]:
    location = location or {}
    return {
        "AlternativeNames": [],
        "Address": location.get("address") or "",
        "City": location.get("city") or "",
        "Country": location.get("country") or "",
        "Latitude": _to_float(location.get("latitude")),
        "Longitude": _to_float(location.get("longitude")),
    }


def _to_float(value: Any) -> float | None:
    if value is None or value == "" or pd.isna(value):
        return None
    return float(value)


def load_institutions() -> dict[str, dict[str, Any]]:
    """Load institutions.json.

    Files saved in an older format ({name: [names]} with the locations in locations.tsv)
    are converted.
    """
    if not INSTITUTIONS_FILE.exists():
        return {}
    institutions = json.loads(INSTITUTIONS_FILE.read_text(encoding="utf-8"))
    if all(isinstance(x, dict) for x in institutions.values()):
        return gather_unlocated(institutions)

    locations: dict[str, dict[str, Any]] = {}
    if LOCATIONS_FILE.exists():
        for _, row in pd.read_csv(LOCATIONS_FILE, sep="\t").iterrows():
            locations[row["name"]] = {
                k: None if pd.isna(row.get(k)) else row.get(k)
                for k in ["address", "city", "country", "latitude", "longitude"]
            }
    converted = {}
    for name, names in institutions.items():
        converted[name] = new_institution(locations.get(name))
        converted[name]["AlternativeNames"] = sorted(set(names) - {name})
    print(f"Converted {INSTITUTIONS_FILE} to the new format")
    return gather_unlocated(converted)


def is_unlocated(institution: dict[str, Any]) -> bool:
    """Return True for an institution without location, address or alternative names."""
    return (
        institution["Latitude"] is None
        and institution["Longitude"] is None
        and not institution["Address"]
        and not institution["AlternativeNames"]
    )


def gather_unlocated(institutions: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Move the institutions that are not located to the "unlocated" entry.

    Groups of names without location (with alternative names) are kept:
    they were probably made by hand.
    """
    unlocated = institutions.get(UNLOCATED, new_institution())
    names = set(unlocated["AlternativeNames"])
    gathered = {}
    for name, institution in institutions.items():
        if name == UNLOCATED:
            continue
        if is_unlocated(institution):
            names.add(name)
        else:
            gathered[name] = institution
    if names:
        gathered[UNLOCATED] = {**unlocated, "AlternativeNames": sorted(names)}
    return gathered


def explode_unlocated(institutions: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Turn each name of the "unlocated" entry into its own institution.

    To compare them one by one with the other institutions.
    """
    exploded = {k: v for k, v in institutions.items() if k != UNLOCATED}
    for name in institutions.get(UNLOCATED, {}).get("AlternativeNames", []):
        exploded.setdefault(name, new_institution())
    return exploded


def save_institutions(institutions: dict[str, dict[str, Any]]) -> None:
    """Save institutions.json.

    Through a temporary file: stopping the script while saving cannot leave a half-written file.
    """
    tmp_file = INSTITUTIONS_FILE.with_suffix(".json.tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(institutions, f, indent=4, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    tmp_file.replace(INSTITUTIONS_FILE)


def known_names(institutions: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Map each institution name (and alternative name) to its institution in the file."""
    names = {}
    for name, institution in institutions.items():
        names[name] = name
        for alternative in institution["AlternativeNames"]:
            names.setdefault(alternative, name)
    return names


def update_institutions(
    institutions: dict[str, dict[str, Any]], names: Any
) -> dict[str, dict[str, Any]]:
    """Add the institution names that are not in the file yet.

    The institutions already in the file are not changed,
    except to add alternative names.
    """
    known = known_names(institutions)
    new_names = sorted({x for x in names if x not in known})

    # several new names can have the same address once cleaned: geocode it once
    by_address: dict[str, list[str]] = {}
    for name in new_names:
        by_address.setdefault(clean_address(name), []).append(name)
    to_geocode = sorted(by_address)
    print(f"{len(known)} institution names known, {len(to_geocode)} new addresses to geocode")
    if DEBUG:
        to_geocode = to_geocode[:3]

    geolocator = Nominatim(user_agent="bids-inventory-institutions", timeout=10)
    # Nominatim usage policy: at most 1 request per second
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, max_retries=2)

    for address in to_geocode:
        print(f"[blue]{address}")
        location = _get_location(geocode, address)
        if location is None:
            print("    [red]not found")
            found: dict[str, Any] = {}
        else:
            print(f"    [green]{location.address}")
            details = location.raw.get("address", {})
            found = {
                "address": location.address,
                "city": details.get("city") or details.get("town") or details.get("village"),
                "country": details.get("country"),
                "latitude": location.latitude,
                "longitude": location.longitude,
            }
        add_names(institutions, by_address[address], found)
        save_institutions(institutions)

    save_institutions(institutions)
    return institutions


def add_names(
    institutions: dict[str, dict[str, Any]], names: list[str], location: dict[str, Any]
) -> None:
    """Add names found at a location.

    To the institution already at this address if there is one,
    otherwise as a new institution.
    Names that could not be located are added to the "unlocated" entry.
    """
    if not location.get("address"):
        unlocated = institutions.setdefault(UNLOCATED, new_institution())
        unlocated["AlternativeNames"] = sorted(set(unlocated["AlternativeNames"]) | set(names))
        return
    same_address = [
        name
        for name, institution in institutions.items()
        if institution["Address"] == location["address"]
    ]
    if same_address:
        name = same_address[0]
    else:
        name, *names = names
        institutions[name] = new_institution(location)
    alternatives = set(institutions[name]["AlternativeNames"]) | set(names)
    institutions[name]["AlternativeNames"] = sorted(alternatives - {name})


def institutions_locations(
    institutions: dict[str, dict[str, Any]], counts: pd.DataFrame
) -> pd.DataFrame:
    """Return the number of datasets and subjects of each institution, with its location."""
    known = known_names(institutions)
    totals: dict[str, dict[str, int]] = {}
    for row in counts.itertuples():
        if row.name not in known:  # not geocoded in debug mode
            continue
        total = totals.setdefault(known[row.name], {"count": 0, "nb_subjects": 0})
        total["count"] += row.count
        total["nb_subjects"] += row.nb_subjects
    rows = []
    for name, total in sorted(totals.items()):
        institution = institutions[name]
        rows.append(
            {
                "name": name,
                **total,
                "address": institution["Address"] or None,
                "city": institution["City"] or None,
                "country": institution["Country"] or None,
                "latitude": institution["Latitude"],
                "longitude": institution["Longitude"],
            }
        )
    return pd.DataFrame(rows, columns=COLUMNS)


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
