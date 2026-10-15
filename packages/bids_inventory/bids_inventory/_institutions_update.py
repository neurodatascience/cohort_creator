"""Geocode the institutions of the inventory: ``bids_inventory institutions update``.

The institution names of the inventory that are not in institutions.json yet
are geocoded with Nominatim (OpenStreetMap). A name located at the same address
as an institution already in the file is added to its alternative names,
otherwise it is added as a new institution.
Names that could not be located are added to the "unlocated" entry.

Needs the 'institutions' extra.
"""

from typing import Any

from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from geopy.location import Location

from bids_inventory.institutions import (
    UNLOCATED,
    clean_address,
    known_names,
    new_institution,
    save_institutions,
)
from bids_inventory.logger import bi_logger

bi_log = bi_logger()


def update_institutions(
    institutions: dict[str, dict[str, Any]], names: Any, debug: bool = False
) -> dict[str, dict[str, Any]]:
    """Add the institution names that are not in the file yet.

    The institutions already in the file are not changed,
    except to add alternative names.
    The file is saved after each geocoded address:
    if the update is stopped, running it again continues where it stopped.

    Parameters
    ----------
    debug : bool
        Only geocode a few addresses.
    """
    known = known_names(institutions)
    new_names = sorted({x for x in names if x not in known})

    # several new names can have the same address once cleaned: geocode it once
    by_address: dict[str, list[str]] = {}
    for name in new_names:
        by_address.setdefault(clean_address(name), []).append(name)
    to_geocode = sorted(by_address)
    bi_log.info(f"{len(known)} institution names known, {len(to_geocode)} new addresses to geocode")
    if debug:
        to_geocode = to_geocode[:3]

    geolocator = Nominatim(user_agent="bids-inventory-institutions", timeout=10)
    # Nominatim usage policy: at most 1 request per second
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, max_retries=2)

    for address in to_geocode:
        bi_log.info(address)
        location = _get_location(geocode, address)
        if location is None:
            bi_log.info("  not found")
            found: dict[str, Any] = {}
        else:
            bi_log.info(f"  {location.address}")
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


def _get_location(geocode: RateLimiter, address: str) -> None | Location:
    """Geocode an address, then parts of it if it is not found."""
    if not address:
        return None
    try:
        if location := geocode(address, addressdetails=True):
            return location
    except Exception as e:
        bi_log.warning(f"Could not geocode {address!r}: {e!r}")
    tokens = [x.strip() for x in address.split(",")]
    if len(tokens) > 1:
        # try without the first part (often a department), then only with it
        return _get_location(geocode, ", ".join(tokens[1:])) or _get_location(geocode, tokens[0])
    return None
