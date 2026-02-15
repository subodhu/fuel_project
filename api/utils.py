import logging
import openrouteservice
from django.conf import settings
from django.core.cache import cache
from django.contrib.gis.geos import LineString
from .models import FuelStation

logger = logging.getLogger(__name__)

# Cache timeouts (seconds)
CACHE_TIMEOUT_FULL = 60 * 60  # 1 hour for full result
CACHE_TIMEOUT_GEOCODE = 60 * 60 * 24  # 24 hours for geocoding
CACHE_TIMEOUT_ROUTE = 60 * 60  # 1 hour for route details


def _cache_get(key):
    try:
        return cache.get(key)
    except Exception as e:
        logger.warning("Cache GET failed for key %s: %s", key, e)
        return None


def _cache_set(key, value, timeout):
    try:
        cache.set(key, value, timeout)
    except Exception as e:
        logger.warning("Cache SET failed for key %s: %s", key, e)


def get_route_and_optimize(start_str, finish_str):
    # Normalize inputs for stable cache keys
    start_norm = start_str.strip().lower()
    finish_norm = finish_str.strip().lower()
    full_cache_key = f"ors:route_result:{start_norm}:{finish_norm}"

    # Try to return a cached full result
    cached_result = _cache_get(full_cache_key)
    if cached_result:
        return cached_result, None

    client = openrouteservice.Client(key=settings.ORS_API_KEY)

    # Geocoding & Routing (API Calls)
    try:
        # Geocode Start (try geocode cache first - will be populated when full cache miss)
        start_key = f"ors:pelias_coords:{start_norm}"
        start_res = _cache_get(start_key)
        if not start_res:
            start_res = client.pelias_search(text=start_str, country="USA")
            if start_res and "features" in start_res:
                _cache_set(start_key, start_res, CACHE_TIMEOUT_GEOCODE)

        if not start_res or not start_res.get("features"):
            return None, "Start location not found"
        start_coords = start_res["features"][0]["geometry"]["coordinates"]

        # Geocode End (try geocode cache first)
        end_key = f"ors:pelias_coords:{finish_norm}"
        end_res = _cache_get(end_key)
        if not end_res:
            end_res = client.pelias_search(text=finish_str, country="USA")
            if end_res and "features" in end_res:
                _cache_set(end_key, end_res, CACHE_TIMEOUT_GEOCODE)

        if not end_res or not end_res.get("features"):
            return None, "Finish location not found"
        end_coords = end_res["features"][0]["geometry"]["coordinates"]

        # Get Route (do not cache directions; rely on full-result cache)
        route = client.directions(
            coordinates=[start_coords, end_coords],
            profile="driving-car",
            format="geojson",
            units="mi",
        )

    except Exception as e:
        return None, f"ORS Error: {str(e)}"

    feature = route["features"][0]
    route_geom = feature["geometry"]
    total_miles = feature["properties"]["summary"]["distance"]

    # Database Spatial Filtering
    route_line = LineString(route_geom["coordinates"])
    # Find stations within ~10 miles (0.15 degrees)
    stations = FuelStation.objects.filter(location__dwithin=(route_line, 0.15))

    # Linear Projection
    candidates = []
    deg_to_miles = 69.0

    for station in stations:
        dist_deg = route_line.project(station.location)
        candidates.append(
            {
                "station": station,
                "mile_marker": dist_deg * deg_to_miles,
                "price": station.retail_price,
            }
        )

    candidates.sort(key=lambda x: x["mile_marker"])

    # Greedy Optimization
    stops = []
    current_miles = 0
    total_cost = 0
    RANGE = 500
    MPG = 10

    while True:
        if (current_miles + RANGE) >= total_miles:
            # Final leg cost
            remaining = total_miles - current_miles
            price = stops[-1]["price"] if stops else 3.50  # Default price if no stops
            total_cost += (remaining / MPG) * price
            break

        max_reach = current_miles + RANGE
        reachable = [
            s for s in candidates if current_miles < s["mile_marker"] <= max_reach
        ]

        if not reachable:
            return None, "Stranded: No fuel stations within range."

        best = min(reachable, key=lambda x: x["price"])

        # Add cost to get to this station
        dist = best["mile_marker"] - current_miles
        prev_price = stops[-1]["price"] if stops else best["price"]  # or start price
        total_cost += (dist / MPG) * prev_price

        stops.append(
            {
                "city": best["station"].city,
                "state": best["station"].state,
                "price": best["station"].retail_price,
                "mile_marker": round(best["mile_marker"], 1),
                "coordinates": [best["station"].location.x, best["station"].location.y],
            }
        )
        current_miles = best["mile_marker"]

    result = {
        # "route_geometry": route_geom,
        "total_miles": round(total_miles, 1),
        "fuel_stops": stops,
        "total_fuel_cost": round(total_cost, 2),
    }

    # Cache the full result for subsequent identical requests
    _cache_set(full_cache_key, result, CACHE_TIMEOUT_FULL)

    return result, None
