"""Institutions of the inventory, described in ``data/institutions.json``.

Each institution:

    "name": {
        "AlternativeNames": ["other names of the same institution found in datasets"],
        "Address": "",
        "City": "",
        "Country": "",
        "Latitude": null,
        "Longitude": null
    }

The names that could not be located are the alternative names of the "unlocated" entry.
The file is updated with ``tools/localize_institutions.py``.
"""

import json
import re
from typing import Any

import pandas as pd

from bids_inventory.listing import _data_dir

INSTITUTIONS_FILE = _data_dir() / "institutions.json"
# entry of institutions.json listing (in its alternative names) the institutions not located
UNLOCATED = "unlocated"

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


def load_institutions() -> dict[str, dict[str, Any]]:
    """Load institutions.json."""
    if not INSTITUTIONS_FILE.exists():
        return {}
    return json.loads(INSTITUTIONS_FILE.read_text(encoding="utf-8"))


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


def institutions_locations(
    institutions: dict[str, dict[str, Any]], counts: pd.DataFrame
) -> pd.DataFrame:
    """Return the number of datasets and subjects of each institution, with its location."""
    known = known_names(institutions)
    totals: dict[str, dict[str, int]] = {}
    for name, count, nb_subjects in zip(counts["name"], counts["count"], counts["nb_subjects"]):
        if name not in known:  # not geocoded in debug mode
            continue
        total = totals.setdefault(known[name], {"count": 0, "nb_subjects": 0})
        total["count"] += int(count)
        total["nb_subjects"] += int(nb_subjects)
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
    for institutions, nb_subjects in zip(df["institutions"], df["nb_subjects"]):
        for institution in institutions if isinstance(institutions, list) else []:
            if not isinstance(institution, str) or not clean_address(institution):
                continue
            counts.setdefault(institution, {"count": 0, "nb_subjects": 0})
            counts[institution]["count"] += 1
            if pd.notna(nb_subjects):
                counts[institution]["nb_subjects"] += int(nb_subjects)
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
