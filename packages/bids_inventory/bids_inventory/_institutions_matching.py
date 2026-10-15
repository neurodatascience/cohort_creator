"""Suggest institutions of institutions.json that are probably the same, and merge them.

- ``bids_inventory institutions suggest`` writes institution_matches.tsv:
  pairs of institutions that are probably the same, with a score and the reasons why.
- after reviewing it (``y`` in the ``accept`` column for the pairs to merge),
  ``bids_inventory institutions apply-matches`` merges the accepted pairs in institutions.json.

Needs the 'institutions' extra.
"""

import math
import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
from rapidfuzz import fuzz
from unidecode import unidecode

from bids_inventory.logger import bi_logger

bi_log = bi_logger()

# default name of the file with the matches to review
MATCHES_FILE = Path("institution_matches.tsv")

# only suggest pairs with a score of at least
MIN_SCORE = 75

ABBREVIATIONS = {
    "univ": "university",
    "uni": "university",
    "universitat": "university",
    "universite": "university",
    "universidad": "university",
    "universita": "university",
    "universiteit": "university",
    "inst": "institute",
    "institut": "institute",
    "instituto": "institute",
    "ctr": "center",
    "centre": "center",
    "centro": "center",
    "zentrum": "center",
    "hosp": "hospital",
    "hopital": "hospital",
    "dept": "department",
    "st": "saint",
    # the same city in different languages
    "geneve": "geneva",
    "genf": "geneva",
    "muenchen": "munich",
    "munchen": "munich",
    "koln": "cologne",
    "koeln": "cologne",
    "wien": "vienna",
    "zuerich": "zurich",
    "roma": "rome",
    "milano": "milan",
    "kobenhavn": "copenhagen",
}
STOP_WORDS = {
    "of", "the", "and", "for", "at", "in", "on",
    "de", "du", "des", "la", "le", "les", "et", "di", "del", "della", "y",
    "fur", "fuer", "der", "die", "das", "und", "van", "voor",
}  # fmt: skip
# a word found in more than this fraction of the names is generic ("university", "mri"...)
GENERIC_FRACTION = 0.02
# ... and in at least this number of names (for files with few names)
GENERIC_MIN_COUNT = 3
POSTAL_CODE = re.compile(r"^(?=.*\d)[a-z0-9]{4,7}$")


def normalize(text: str) -> list[str]:
    """Return the words of a name: lower case, no accents, no punctuation, no stop words."""
    text = unidecode(text).lower()
    words = re.sub(r"[^a-z0-9]+", " ", text).split()
    words = [ABBREVIATIONS.get(word, word) for word in words]
    return [word for word in words if word not in STOP_WORDS]


def split_name(name: str, clean: Callable[[str], str]) -> tuple[list[str], list[str]]:
    """Split a name into the words of the institution and the words of its address."""
    parts = clean(name).split(",")
    return normalize(parts[0]), normalize(" ".join(parts[1:]))


def acronym(words: list[str]) -> str:
    return "".join(word[0] for word in words if not word.isdigit())


def distance_km(a: dict[str, Any], b: dict[str, Any]) -> float | None:
    """Return the distance between 2 institutions, if both are located."""
    if None in (a["Latitude"], a["Longitude"], b["Latitude"], b["Longitude"]):
        return None
    lat1, lon1, lat2, lon2 = map(
        math.radians, [a["Latitude"], a["Longitude"], b["Latitude"], b["Longitude"]]
    )
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(h))


def score_names(
    a: tuple[list[str], list[str]],
    b: tuple[list[str], list[str]],
    generic: set[str],
    nearby: bool,
) -> tuple[float, list[str]]:
    """Score how likely 2 names are the same institution.

    ``nearby``: the 2 institutions are known to be at the same place
    (close to each other or in the same city).
    """
    (inst_a, address_a), (inst_b, address_b) = a, b
    score, reasons = 0.0, []

    specific_a = {w for w in inst_a if w not in generic}
    specific_b = {w for w in inst_b if w not in generic}
    if specific_a and specific_b:
        # the same distinctive words, in any order
        similarity = fuzz.token_sort_ratio(
            " ".join(sorted(specific_a)), " ".join(sorted(specific_b))
        )
        # a single distinctive word (often an acronym: "BIC") is not enough on its own
        if similarity >= 90 and (nearby or min(len(specific_a), len(specific_b)) > 1):
            score = similarity
            reasons.append(f"similar names ({similarity:.0f})")
        # the distinctive words of one name are all in the other ("BIC" and "McLean Hospital BIC"):
        # only likely the same institution if they are at the same place
        elif nearby and (specific_a <= specific_b or specific_b <= specific_a):
            score = 85
            reasons.append("one name contains the other")

    for short, long in [(inst_a, inst_b), (inst_b, inst_a)]:
        if (
            nearby
            and len(short) == 1
            and len(short[0]) >= 2
            and len(long) >= 2
            and short[0] == acronym(long)
        ):
            score = max(score, 80)
            reasons.append(f"acronym ({short[0].upper()})")

    numbers_a = {w for w in address_a if any(c.isdigit() for c in w)}
    numbers_b = {w for w in address_b if any(c.isdigit() for c in w)}
    postal_codes = {w for w in numbers_a & numbers_b if POSTAL_CODE.match(w)}
    street_numbers = (numbers_a & numbers_b) - postal_codes
    if postal_codes and street_numbers:
        score = max(score, 95)
        reasons.append("same postal code and street number")
    elif postal_codes and score:
        score = min(score + 5, 100)
        reasons.append("same postal code")
    return score, reasons


def are_nearby(
    a: dict[str, Any],
    b: dict[str, Any],
    words_a: set[str],
    words_b: set[str],
) -> tuple[bool, str]:
    """Return whether 2 institutions are at the same place, and why.

    Close to each other, in the same city,
    or the city of one is in the names of the other (when it is not located).
    """
    distance = distance_km(a, b)
    if distance is not None:
        return distance < 5, f"{distance:.1f} km apart"
    city_a, city_b = " ".join(normalize(a["City"])), " ".join(normalize(b["City"]))
    if city_a and city_a == city_b:
        return True, "same city"
    for city, words in [(city_a, words_b), (city_b, words_a)]:
        if city and set(city.split()) <= words:
            return True, f"{city} in the name"
    return False, ""


def suggest_matches(
    institutions: dict[str, dict[str, Any]], clean: Callable[[str], str]
) -> pd.DataFrame:
    """Return the pairs of institutions that are probably the same institution."""
    keys = sorted(institutions)
    names = {
        key: [split_name(name, clean) for name in [key, *institutions[key]["AlternativeNames"]]]
        for key in keys
    }
    word_counts = Counter(
        word for splits in names.values() for inst, _ in splits for word in set(inst)
    )
    n_names = sum(len(splits) for splits in names.values())
    generic = {
        word
        for word, count in word_counts.items()
        if count > GENERIC_FRACTION * n_names and count >= GENERIC_MIN_COUNT
    }

    all_words = {
        key: {word for inst, address in splits for word in inst + address}
        for key, splits in names.items()
    }

    rows = []
    for i, key_a in enumerate(keys):
        a = institutions[key_a]
        for key_b in keys[i + 1 :]:
            b = institutions[key_b]
            if a["Country"] and b["Country"] and a["Country"] != b["Country"]:
                continue
            nearby, where = are_nearby(a, b, all_words[key_a], all_words[key_b])
            score, reasons = 0.0, []
            for name_a in names[key_a]:
                for name_b in names[key_b]:
                    name_score, name_reasons = score_names(name_a, name_b, generic, nearby)
                    if name_score > score:
                        score, reasons = name_score, name_reasons
            if not score:
                continue
            if where:
                reasons.append(where)
            distance = distance_km(a, b)
            if distance is not None and distance < 0.5:
                score = min(score + 5, 100)
            elif distance is not None and distance > 50:
                # far apart: probably not the same, or one of them is located wrongly
                score -= 20
            if score >= MIN_SCORE:
                rows.append(
                    {
                        "score": round(score),
                        "institution_1": key_a,
                        "institution_2": key_b,
                        "reasons": "; ".join(reasons),
                        "city_1": a["City"],
                        "city_2": b["City"],
                        "accept": "",
                    }
                )
    columns = ["score", "institution_1", "institution_2", "reasons", "city_1", "city_2", "accept"]
    return (
        pd.DataFrame(rows, columns=columns)
        .sort_values(["score", "institution_1"], ascending=[False, True])
        .reset_index(drop=True)
    )


def apply_matches(
    institutions: dict[str, dict[str, Any]], matches: pd.DataFrame, counts: dict[str, int]
) -> dict[str, dict[str, Any]]:
    """Merge the accepted pairs of institutions.

    Pairs are chained: if A-B and B-C are accepted, A, B and C are merged.
    The merged institution is the located institution used by the most datasets
    (``counts``): its fields are kept, the other names become its alternative names.
    """
    parent = {key: key for key in institutions}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    accepted = matches[matches["accept"].astype(str).str.strip().str.lower().isin(["y", "yes"])]
    for institution_1, institution_2 in zip(
        accepted["institution_1"].astype(str), accepted["institution_2"].astype(str)
    ):
        missing = [k for k in (institution_1, institution_2) if k not in institutions]
        if missing:
            bi_log.warning(f"Skipping a match, not in institutions.json anymore: {missing}")
            continue
        parent[find(institution_1)] = find(institution_2)

    groups: dict[str, list[str]] = {}
    for key in institutions:
        groups.setdefault(find(key), []).append(key)

    merged = {}
    for members in groups.values():
        if len(members) == 1:
            merged[members[0]] = institutions[members[0]]
            continue
        key = max(
            members,
            key=lambda k: (institutions[k]["Latitude"] is not None, counts.get(k, 0), k),
        )
        names = {name for k in members for name in [k, *institutions[k]["AlternativeNames"]]}
        merged[key] = {**institutions[key], "AlternativeNames": sorted(names - {key})}
        bi_log.info(f"Merged into {key!r}: {sorted(set(members) - {key})}")
    return merged
