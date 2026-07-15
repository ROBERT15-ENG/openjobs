"""City geocoding and distance helpers (no external API)."""

import math
import re

# Approximate city centres (lat, lng) for radius search
CITY_COORDS = {
    'nairobi': (-1.2921, 36.8219),
    'sydney': (-33.8688, 151.2093),
    'melbourne': (-37.8136, 144.9631),
    'brisbane': (-27.4698, 153.0251),
    'perth': (-31.9505, 115.8605),
    'adelaide': (-34.9285, 138.6007),
    'lagos': (6.5244, 3.3792),
    'london': (51.5074, -0.1278),
    'new york': (40.7128, -74.0060),
    'san francisco': (37.7749, -122.4194),
    'usa': (39.8283, -98.5795),
    'auckland': (-36.8485, 174.7633),
    'singapore': (1.3521, 103.8198),
    'dubai': (25.2048, 55.2708),
    'toronto': (43.6532, -79.3832),
}


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance in kilometres."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def geocode_location(location_text):
    """Best-effort lat/lng from free-text location (city substring match)."""
    if not location_text:
        return None, None
    text = location_text.lower().strip()
    if 'remote' in text or 'global' in text or 'anywhere' in text:
        return None, None
    for city, coords in CITY_COORDS.items():
        if city in text:
            return coords
    # First token fallback (e.g. "Sydney, NSW")
    token = re.split(r'[,/|]', text)[0].strip()
    return CITY_COORDS.get(token, (None, None))


def distance_km_from(job_row, near_lat, near_lng):
    lat = job_row.get('latitude')
    lng = job_row.get('longitude')
    if lat is None or lng is None or near_lat is None or near_lng is None:
        return None
    return round(haversine_km(near_lat, near_lng, lat, lng), 1)
