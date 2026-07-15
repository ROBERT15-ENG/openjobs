"""Job row normalization for API responses."""

from geo_util import distance_km_from, geocode_location
from seo_util import job_url_path


def date_posted_value(row):
    if not row:
        return None
    return row.get('posted_at') or row.get('created_at')


def enrich_job(row, near_lat=None, near_lng=None):
    """Add date_posted, url, and optional distance_km."""
    data = dict(row)
    data['date_posted'] = date_posted_value(data)
    data['url'] = job_url_path(data['id'], data.get('title', ''))
    dist = distance_km_from(data, near_lat, near_lng)
    if dist is not None:
        data['distance_km'] = dist
    return data


def geocode_job_location(location_text):
    lat, lng = geocode_location(location_text)
    return lat, lng
