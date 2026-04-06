from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings


def geocode_address(address_components):
    """
    Convert address components to latitude and longitude using Google Maps Geocoding API

    Args:
        address_components (dict): Dictionary containing address components
            Expected keys: building, landmark, pincode, country, state, city, city_area

    Returns:
        tuple: (latitude, longitude) as Decimal objects or (None, None) if geocoding fails
    """
    if not hasattr(settings, "GOOGLE_MAPS_API_KEY") or not settings.GOOGLE_MAPS_API_KEY:
        return None, None

    # Build complete address string
    address_parts = []

    if address_components.get("building"):
        address_parts.append(address_components["building"])
    if address_components.get("landmark"):
        address_parts.append(address_components["landmark"])
    if address_components.get("city_area"):
        address_parts.append(address_components["city_area"])
    if address_components.get("city"):
        address_parts.append(address_components["city"])
    if address_components.get("state"):
        address_parts.append(address_components["state"])
    if address_components.get("country"):
        address_parts.append(address_components["country"])
    if address_components.get("pincode"):
        address_parts.append(address_components["pincode"])

    if not address_parts:
        return None, None

    full_address = ", ".join(address_parts)

    try:
        # Make request to Google Maps Geocoding API
        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": full_address, "key": settings.GOOGLE_MAPS_API_KEY}

        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data["status"] == "OK" and data["results"]:
            location = data["results"][0]["geometry"]["location"]
            lat = location["lat"]
            lng = location["lng"]

            # Convert to Decimal for precise database storage
            try:
                latitude = Decimal(str(lat))
                longitude = Decimal(str(lng))
                return latitude, longitude
            except (InvalidOperation, ValueError):
                return None, None
        else:
            return None, None

    except (requests.RequestException, KeyError, ValueError):
        return None, None


def geocode_site_location(site_location):
    """
    Geocode a SiteLocation instance and update its latitude and longitude fields

    Args:
        site_location: SiteLocation model instance

    Returns:
        bool: True if geocoding was successful, False otherwise
    """
    address_components = {
        "building": site_location.site_address_building,
        "landmark": site_location.site_address_landmark,
        "pincode": site_location.site_address_pincode,
        "country": (
            getattr(site_location.site_address_country, "name", None)
            if site_location.site_address_country
            else None
        ),
        "state": (
            getattr(site_location.site_address_state, "name", None)
            if site_location.site_address_state
            else None
        ),
        "city": (
            getattr(site_location.site_address_city, "name", None)
            if site_location.site_address_city
            else None
        ),
        "city_area": (
            getattr(site_location.site_address_city_area, "city_area_name", None)
            if site_location.site_address_city_area
            else None
        ),
    }

    latitude, longitude = geocode_address(address_components)

    if latitude is not None and longitude is not None:
        site_location.latitude = latitude
        site_location.longitude = longitude
        return True

    return False
