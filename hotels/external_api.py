"""
External hotel data via OpenStreetMap.

Uses the free Nominatim API to geocode a city name, then the Overpass API
to fetch real hotels (tourism=hotel) inside that city's bounding box.
No API key required.
"""
import logging

import requests

logger = logging.getLogger(__name__)

NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
OVERPASS_URL = 'https://overpass-api.de/api/interpreter'
USER_AGENT = 'booking-final-hotel-import/1.0 (educational project)'


class ExternalAPIError(Exception):
    """Raised when the external hotel API cannot be reached or returns bad data."""


def _geocode_city(city):
    """Return (display_name, bounding_box) for a city name, or raise ExternalAPIError."""
    try:
        response = requests.get(
            NOMINATIM_URL,
            params={'q': city, 'format': 'json', 'limit': 1},
            headers={'User-Agent': USER_AGENT},
            timeout=15,
        )
        response.raise_for_status()
        results = response.json()
    except requests.RequestException as e:
        raise ExternalAPIError(f"Could not reach the geocoding service: {e}") from e

    if not results:
        raise ExternalAPIError(f'City "{city}" was not found.')

    place = results[0]
    # boundingbox = [south, north, west, east]
    return place.get('name') or city, place['boundingbox']


def _parse_star_rating(tags):
    """Parse the OSM 'stars' tag into an int between 1 and 5 (default 3)."""
    raw = tags.get('stars', '')
    try:
        return max(1, min(5, int(float(raw))))
    except (TypeError, ValueError):
        return 3


def _build_address(tags):
    street = tags.get('addr:street', '')
    number = tags.get('addr:housenumber', '')
    if street:
        return f"{street} {number}".strip()
    return tags.get('addr:full', '') or 'Address not available'


def _tag_is_yes(value):
    return value not in (None, '', 'no', 'none')


# OSM tag -> amenity name used by the site's match system
# (names must contain the substrings match_score() looks for)
AMENITY_TAG_MAP = {
    'internet_access': 'Free Wi-Fi',
    'air_conditioning': 'Air Conditioning',
    'swimming_pool': 'Swimming Pool',
    'restaurant': 'Restaurant',
    'bar': 'Bar',
    'spa': 'Spa & Wellness',
    'sauna': 'Sauna',
    'fitness_centre': 'Fitness Center (Gym)',
    'parking': 'Parking',
    'wheelchair': 'Wheelchair Accessible',
}


def _parse_amenities(tags):
    """Map real OSM tags to the amenity names the site's matching understands."""
    return [name for tag, name in AMENITY_TAG_MAP.items() if _tag_is_yes(tags.get(tag))]


def _parse_pet_friendly(tags):
    return tags.get('pets_allowed') in ('yes', 'leashed') or tags.get('dog') in ('yes', 'leashed')


def fetch_hotels_for_city(city, limit=20):
    """
    Fetch real hotels in the given city from OpenStreetMap.

    Returns a list of dicts with keys:
    name, city, address, star_rating, latitude, longitude
    """
    city_name, (south, north, west, east) = _geocode_city(city)

    query = f"""
    [out:json][timeout:25];
    nwr["tourism"="hotel"]["name"]({south},{west},{north},{east});
    out center {int(limit)};
    """
    try:
        response = requests.post(
            OVERPASS_URL,
            data={'data': query},
            headers={'User-Agent': USER_AGENT},
            timeout=40,
        )
        response.raise_for_status()
        elements = response.json().get('elements', [])
    except requests.RequestException as e:
        raise ExternalAPIError(f"Could not reach the hotel data service: {e}") from e
    except ValueError as e:
        raise ExternalAPIError("The hotel data service returned an invalid response.") from e

    hotels = []
    for element in elements:
        tags = element.get('tags', {})
        name = tags.get('name', '').strip()
        if not name:
            continue

        # Nodes carry lat/lon directly; ways and relations expose a center point
        latitude = element.get('lat') or element.get('center', {}).get('lat')
        longitude = element.get('lon') or element.get('center', {}).get('lon')

        hotels.append({
            'name': name,
            'city': tags.get('addr:city', '') or city_name,
            'district': tags.get('addr:suburb', '') or tags.get('addr:district', ''),
            'address': _build_address(tags),
            'star_rating': _parse_star_rating(tags),
            'latitude': latitude,
            'longitude': longitude,
            'amenities': _parse_amenities(tags),
            'is_pet_friendly': _parse_pet_friendly(tags),
            'website': tags.get('website', '') or tags.get('contact:website', ''),
            'phone': tags.get('phone', '') or tags.get('contact:phone', ''),
        })

    return hotels
