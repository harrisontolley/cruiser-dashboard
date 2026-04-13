#!/usr/bin/env python3
"""Download Overture Maps features and aggregate to H3 hex grids.

Full pipeline: boundary fetch -> Overture extraction (11 layers) ->
H3 hex aggregation -> satellite embeddings (GEE) -> combined output.

Layers: roads, pois, buildings, landuse, addresses, infrastructure,
land_cover, connectors, building_parts, divisions, bathymetry.

Usage::

    # Full pipeline (Sydney, res 9, with satellite)
    python download_multi_release.py --city sydney --relation-id 5750005 \\
        --satellite --ee-project datacruiser --h3-resolution 9

    # Subset of layers, no satellite
    python download_multi_release.py --city sydney --relation-id 5750005 \\
        --hex-agg --layers roads pois buildings

    # Force re-download
    python download_multi_release.py --city sydney --relation-id 5750005 \\
        --hex-agg --no-resume
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import math
import pickle
import sys
import tempfile
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from shapely import make_valid
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import linemerge, polygonize

logger = logging.getLogger("multi_release")

# ============================================================================
# Configuration
# ============================================================================

OVERTURE_RELEASE = "2026-02-18.0"
OVERTURE_S3_BASE = "s3://overturemaps-us-west-2/release"

SCHEMA_VERSION = "4.0.0"

DATA_DIR = Path.cwd() / "data"

RELEASE_TAGS: dict[str, str] = {
    "2026": "2026-02-18.0",
}

ALL_LAYERS = [
    "roads", "pois", "buildings", "landuse",
    "addresses", "infrastructure", "land_cover", "connectors",
    "building_parts", "divisions", "bathymetry",
]

# ---------------------------------------------------------------------------
# Global feature registry — fixed category lists for deterministic schemas.
# Every city/resolution produces the same columns; categories not in the
# registry are bucketed into "other".  Derived from the union of all
# categories observed in Sydney + Melbourne (2026-02-18.0 release).
# ---------------------------------------------------------------------------
GLOBAL_FEATURE_REGISTRY: dict[str, list[str]] = {
    "road_classes": [
        "bridleway", "cycleway", "footway", "living_street", "motorway",
        "path", "pedestrian", "primary", "residential", "secondary",
        "service", "steps", "tertiary", "track", "trunk",
        "unclassified", "unknown",
    ],
    "road_subclasses": [
        "sidewalk", "crosswalk", "link", "driveway", "parking_aisle",
        "alley", "steps",
    ],
    "road_surface_types": [
        "paved", "asphalt", "concrete", "unpaved", "gravel", "dirt",
        "compacted", "cobblestone", "sett", "metal", "wood", "ground",
    ],
    "building_classes": [
        "allotment_house", "apartments", "barn", "beach_hut", "boathouse",
        "bridge_structure", "bungalow", "bunker", "cabin", "carport",
        "cathedral", "chapel", "church", "civic", "college", "commercial",
        "cowshed", "detached", "dormitory", "factory", "farm",
        "farm_auxiliary", "fire_station", "garage", "garages", "government",
        "grandstand", "greenhouse", "guardhouse", "hangar", "hospital",
        "hotel", "house", "hut", "industrial", "kindergarten", "kiosk",
        "library", "manufacture", "military", "monastery", "mosque",
        "office", "outbuilding", "parking", "pavilion", "post_office",
        "presbytery", "public", "religious", "residential", "retail",
        "roof", "school", "semidetached_house", "service", "shed", "silo",
        "sports_centre", "sports_hall", "stable", "stadium",
        "static_caravan", "storage_tank", "supermarket", "synagogue",
        "temple", "terrace", "toilets", "train_station",
        "transformer_tower", "transportation", "university", "unknown",
        "warehouse",
    ],
    "poi_categories": [
        "professional_services", "cafe", "park", "beauty_salon",
        "automotive_repair", "restaurant", "clothing_store", "gym",
        "hair_salon", "real_estate_agent", "contractor",
        "church_cathedral", "home_service",
        "community_services_non_profits", "dentist", "coffee_shop",
        "bakery", "corporate_office", "retail", "furniture_store",
        "financial_service", "real_estate", "pharmacy", "doctor",
        "construction_services", "fast_food_restaurant", "bar",
        "shopping", "education", "hotel", "pet_service", "insurance_agency",
        "auto_dealer", "pizza_restaurant", "child_care", "supermarket",
        "accounting", "plumber", "event_planning",
        "flowers_and_gifts_shop", "sports_club_and_league",
        "gas_station", "liquor_store", "accountant", "physical_therapy",
        "massage", "tattoo_shop", "nail_salon", "dry_cleaning",
        "photographer",
    ],
    "landuse_classes": [
        "airfield", "allotments", "animal_keeping", "aquaculture",
        "bare_rock", "barracks", "base", "basin", "bay", "beach",
        "brownfield", "bunker", "camp_site", "canal", "cape", "cemetery",
        "cliff", "clinic", "college", "commercial", "construction",
        "danger_area", "ditch", "doctors", "dog_park", "drain",
        "driving_range", "driving_school", "dune", "education", "fairway",
        "farmland", "farmyard", "fell", "fishpond", "flowerbed", "forest",
        "garages", "garden", "golf_course", "grass", "grassland",
        "grave_yard", "green", "greenfield", "greenhouse_horticulture",
        "heath", "hospital", "industrial", "institutional", "island",
        "islet", "kindergarten", "lagoon", "lake", "land", "landfill",
        "lateral_water_hazard", "marina", "meadow", "military", "moat",
        "mountain_range", "national_park", "natural_monument",
        "nature_reserve", "obstacle_course", "ocean", "orchard", "park",
        "pedestrian", "pitch", "plant_nursery", "plateau", "playground",
        "plaza", "pond", "protected", "protected_landscape_seascape",
        "quarry", "railway", "range", "recreation_ground", "reef",
        "reflecting_pool", "religious", "reservoir", "residential",
        "resort", "retail", "river", "rock", "rough", "sand", "school",
        "schoolyard", "scree", "scrub", "shingle", "shrubbery",
        "species_management_area", "stadium", "stone", "strait", "stream",
        "strict_nature_reserve", "swimming_pool", "tee", "theme_park",
        "track", "traffic_island", "training_area", "tree_row",
        "university", "valley", "village_green", "vineyard", "wastewater",
        "water", "water_hazard", "water_park", "wetland",
        "wilderness_area", "wood", "works", "zoo",
    ],
    "infrastructure_classes": [
        "artwork", "atm", "barrier", "bench", "bicycle_parking",
        "bicycle_rental", "bollard", "bridge", "bus_station", "bus_stop",
        "charging_station", "communication_tower", "crossing",
        "dam", "drinking_water", "fence", "fire_hydrant", "fountain",
        "gate", "generator", "information", "manhole", "monitoring",
        "parking", "picnic_table", "pier", "pipeline", "platform",
        "post_box", "power_line", "power_pole", "power_tower",
        "railway_station", "recycling", "street_cabinet", "street_lamp",
        "substation", "subway_station", "toilets", "traffic_signals",
        "vending_machine", "wall", "waste_basket",
    ],
    "land_cover_subtypes": [
        "barren", "crop", "forest", "grass", "mangrove",
        "moss", "shrub", "snow", "urban", "wetland",
    ],
}

# Satellite embedding config (Google Earth Engine)
SAT_COLLECTION = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
SAT_DATE_START_DEFAULT = "2019"
SAT_DATE_END_DEFAULT = "2021"
H3_RESOLUTION_DEFAULT = 9
EE_HIGH_VOLUME_URL = "https://earthengine-highvolume.googleapis.com"
MAX_TILE_BYTES = 48 * 1024 * 1024       # 48 MB hard limit per computePixels request
COMPUTE_PIXELS_BYTES_PER_VALUE = 10     # empirical overhead for computePixels NPY (~9 bytes/value)
SAT_MAX_WORKERS = 8                     # parallel tile workers (keep ≤ urllib3 pool size of 10)
SAT_CHECKPOINT_EVERY = 500              # save tile progress every N completed tiles

# H3 average edge length in metres by resolution
H3_EDGE_LENGTH_M = {
    4: 22_606, 5: 8_545, 6: 3_229, 7: 1_220,
    8:    461, 9:   174, 10:  65,  11:   25,
}


# ============================================================================
# Models
# ============================================================================


@dataclass(frozen=True)
class Bounds:
    """Bounding box in lon/lat."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float


# ============================================================================
# Config helpers
# ============================================================================


def utm_crs_from_lonlat(lon: float, lat: float) -> str:
    """Return the UTM EPSG code for a given (lon, lat) coordinate."""
    zone = int(math.floor((lon + 180) / 6)) + 1
    zone = max(1, min(60, zone))
    if lat >= 0:
        return f"EPSG:326{zone:02d}"
    return f"EPSG:327{zone:02d}"


# ============================================================================
# IO helpers
# ============================================================================


def ensure_dir(path: Path) -> Path:
    """Create *path* (and parents) if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def atomic_write(target: Path) -> Generator[Path, None, None]:
    """Yield a temp file path in the same directory; rename on success."""
    ensure_dir(target.parent)
    tmp = None
    try:
        tmp = tempfile.NamedTemporaryFile(
            dir=target.parent, suffix=target.suffix, delete=False
        )
        tmp_path = Path(tmp.name)
        tmp.close()
        yield tmp_path
        tmp_path.rename(target)
    except BaseException:
        if tmp is not None:
            Path(tmp.name).unlink(missing_ok=True)
        raise


def save_json(data: dict[str, Any], path: Path) -> Path:
    """Write a JSON file atomically."""
    with atomic_write(path) as tmp:
        tmp.write_text(json.dumps(data, indent=2, default=str))
    return path


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON file."""
    return json.loads(path.read_text())


def save_geodataframe(gdf: gpd.GeoDataFrame, path: Path) -> Path:
    """Save a GeoDataFrame as GeoParquet."""
    ensure_dir(path.parent)
    path = Path(str(path))
    if gdf.geometry.name in gdf.columns and (len(gdf) == 0 or not gdf.geometry.isna().all()):
        gdf.to_parquet(path, engine="pyarrow")
    else:
        pd.DataFrame(gdf).to_parquet(path, engine="pyarrow")
    logger.info("Saved %d rows -> %s", len(gdf), path)
    return path


# ============================================================================
# Schema definitions
# ============================================================================


@dataclass(frozen=True)
class ColumnSpec:
    """Specification for a single DataFrame column."""

    name: str
    dtype: str
    nullable: bool = True
    description: str = ""


ROADS_SCHEMA: list[ColumnSpec] = [
    ColumnSpec("geometry", "geometry", nullable=False),
    ColumnSpec("overture_id", "str", nullable=False),
    ColumnSpec("road_class", "str", nullable=False),
    ColumnSpec("speed_limit_kmh", "float64"),
    ColumnSpec("lanes", "float64"),
    ColumnSpec("is_bridge", "bool"),
    ColumnSpec("is_tunnel", "bool"),
    ColumnSpec("road_surface", "str"),
    ColumnSpec("width_m", "float64"),
    ColumnSpec("is_link", "bool"),
    ColumnSpec("is_under_construction", "bool"),
]

POIS_SCHEMA: list[ColumnSpec] = [
    ColumnSpec("geometry", "geometry", nullable=False),
    ColumnSpec("overture_id", "str", nullable=False),
    ColumnSpec("name", "str"),
    ColumnSpec("category", "str", nullable=False),
    ColumnSpec("confidence", "float64"),
    ColumnSpec("categories_alt", "str"),
]

BUILDINGS_SCHEMA: list[ColumnSpec] = [
    ColumnSpec("geometry", "geometry", nullable=False),
    ColumnSpec("overture_id", "str", nullable=False),
    ColumnSpec("building_class", "str"),
    ColumnSpec("height", "float64"),
    ColumnSpec("num_floors", "float64"),
    ColumnSpec("area_m2", "float64"),
    ColumnSpec("facade_material", "str"),
    ColumnSpec("roof_material", "str"),
    ColumnSpec("roof_shape", "str"),
    ColumnSpec("roof_height", "float64"),
    ColumnSpec("num_floors_underground", "float64"),
    ColumnSpec("is_underground", "bool"),
]

LANDUSE_SCHEMA: list[ColumnSpec] = [
    ColumnSpec("geometry", "geometry", nullable=False),
    ColumnSpec("overture_id", "str", nullable=False),
    ColumnSpec("land_type", "str", nullable=False),
    ColumnSpec("land_class", "str"),
    ColumnSpec("area_m2", "float64"),
    ColumnSpec("land_subtype", "str"),
    ColumnSpec("surface", "str"),
    ColumnSpec("is_salt", "bool"),
    ColumnSpec("is_intermittent", "bool"),
]

_DTYPE_MAP: dict[str, set[str]] = {
    "float64": {"float64", "float32", "Float64", "Float32"},
    "int64": {"int64", "int32", "Int64", "Int32", "uint64", "uint32"},
    "str": {"object", "string", "str"},
    "object": {"object", "string", "str"},
    "bool": {"bool", "boolean", "object"},
    "geometry": {"geometry"},
}


def validate_dataframe(
    df: pd.DataFrame | Any,
    schema: list[ColumnSpec],
) -> list[str]:
    """Validate a DataFrame against a schema. Returns error messages."""
    errors: list[str] = []
    if df is None:
        return ["DataFrame is None"]
    if len(df) == 0:
        return []
    for spec in schema:
        if spec.name not in df.columns:
            if spec.name == "geometry" and hasattr(df, "geometry"):
                continue
            errors.append(f"Missing required column: {spec.name}")
            continue
        if not spec.nullable and bool(df[spec.name].isna().any()):
            null_count = df[spec.name].isna().sum()
            errors.append(
                f"Column '{spec.name}' has {null_count} null values but is not nullable"
            )
    return errors


# ============================================================================
# DuckDB / Overture helpers
# ============================================================================


def get_duckdb_connection() -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection with httpfs and spatial extensions loaded."""
    con = duckdb.connect()
    con.install_extension("httpfs")
    con.load_extension("httpfs")
    con.install_extension("spatial")
    con.load_extension("spatial")
    con.execute("SET s3_region='us-west-2'")
    con.execute("SET s3_access_key_id=''")
    con.execute("SET s3_secret_access_key=''")
    return con


def overture_s3_url(theme: str, type_: str, release: str = OVERTURE_RELEASE) -> str:
    """Build the S3 URL for an Overture Maps theme/type."""
    return f"{OVERTURE_S3_BASE}/{release}/theme={theme}/type={type_}/*"


def bbox_filter_sql(bounds: Bounds) -> str:
    """Build a SQL WHERE clause for Overture bbox filtering."""
    return (
        f"bbox.xmin <= {bounds.max_lon} AND bbox.xmax >= {bounds.min_lon} "
        f"AND bbox.ymin <= {bounds.max_lat} AND bbox.ymax >= {bounds.min_lat}"
    )


# ============================================================================
# Boundary fetch (Overpass API)
# ============================================================================


def _clean_geometry(geom: Polygon | MultiPolygon) -> Polygon | MultiPolygon:
    """Ensure geometry is valid via make_valid."""
    if not geom.is_valid:
        geom = make_valid(geom)
    if geom.is_empty:
        raise ValueError("Geometry is empty after validation")
    return geom


def _build_polygon_from_overpass_relation(
    element: dict,
) -> Polygon | MultiPolygon:
    """Reconstruct a Polygon/MultiPolygon from an Overpass relation element."""
    outer_lines: list[LineString] = []
    inner_lines: list[LineString] = []

    for member in element.get("members", []):
        if member.get("type") != "way":
            continue
        geom = member.get("geometry", [])
        if len(geom) < 2:
            continue
        coords = [(pt["lon"], pt["lat"]) for pt in geom]
        line = LineString(coords)
        role = member.get("role", "outer")
        if role == "inner":
            inner_lines.append(line)
        else:
            outer_lines.append(line)

    if not outer_lines:
        raise ValueError("Overpass relation has no outer way members")

    merged_outer = linemerge(outer_lines)
    outer_polys = list(polygonize(merged_outer))

    if not outer_polys:
        raise ValueError("Could not polygonize outer rings from Overpass relation")

    inner_polys: list[Polygon] = []
    if inner_lines:
        merged_inner = linemerge(inner_lines)
        inner_polys = list(polygonize(merged_inner))

    if len(outer_polys) == 1 and not inner_polys:
        return outer_polys[0]

    if len(outer_polys) == 1 and inner_polys:
        shell = outer_polys[0].exterior.coords
        holes = [p.exterior.coords for p in inner_polys]
        return Polygon(shell, holes)

    result_polys: list[Polygon] = []
    for outer in outer_polys:
        matching_holes = [
            p.exterior.coords for p in inner_polys if outer.contains(p)
        ]
        if matching_holes:
            result_polys.append(Polygon(outer.exterior.coords, matching_holes))
        else:
            result_polys.append(outer)

    if len(result_polys) == 1:
        return result_polys[0]
    return MultiPolygon(result_polys)


_OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def fetch_city_boundary_overpass(
    relation_id: int,
    *,
    timeout: int = 180,
    retries: int = 3,
) -> gpd.GeoDataFrame:
    """Fetch a city boundary from the Overpass API using an OSM relation ID.

    Tries multiple Overpass mirror endpoints with retries and exponential
    backoff to handle gateway timeouts on large city boundaries.
    """
    query = f"[out:json][timeout:{timeout}]; rel({relation_id}); out geom;"
    logger.info("Querying Overpass API for relation %d ...", relation_id)

    last_exc: Exception | None = None
    for attempt in range(retries * len(_OVERPASS_ENDPOINTS)):
        endpoint = _OVERPASS_ENDPOINTS[attempt % len(_OVERPASS_ENDPOINTS)]
        try:
            logger.info(
                "Overpass attempt %d/%d via %s",
                attempt + 1, retries * len(_OVERPASS_ENDPOINTS), endpoint,
            )
            resp = requests.post(
                endpoint,
                data={"data": query},
                timeout=timeout + 30,
            )
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as exc:
            last_exc = exc
            wait = 2 ** (attempt // len(_OVERPASS_ENDPOINTS))
            logger.warning(
                "Overpass request failed (%s): %s — retrying in %ds",
                endpoint, exc, wait,
            )
            time.sleep(wait)
    else:
        raise RuntimeError(
            f"All Overpass attempts failed for relation {relation_id}"
        ) from last_exc

    elements = data.get("elements", [])
    if not elements:
        raise ValueError(
            f"Overpass returned no elements for relation {relation_id}"
        )

    element = elements[0]
    name = element.get("tags", {}).get("name", f"relation-{relation_id}")

    geom = _build_polygon_from_overpass_relation(element)
    geom = _clean_geometry(geom)

    osm_id = f"osm-relation-{relation_id}"
    gdf = gpd.GeoDataFrame(
        {"id": [osm_id], "name": [name], "division_id": [osm_id]},
        geometry=[geom],
        crs="EPSG:4326",
    )

    logger.info(
        "Boundary fetched: id=%s, name=%s, geom_type=%s",
        osm_id, name, geom.geom_type,
    )
    return gdf


# ============================================================================
# Overture field parsers
# ============================================================================


def _parse_overture_speed_limits(speed_limits: object) -> float | None:
    """Parse Overture speed_limits structured field to km/h."""
    if speed_limits is None or (isinstance(speed_limits, float) and np.isnan(speed_limits)):
        return None
    if isinstance(speed_limits, (list, tuple)):
        for limit in speed_limits:
            if not isinstance(limit, dict):
                continue
            max_speed = limit.get("max_speed")
            if not isinstance(max_speed, dict):
                continue
            value = max_speed.get("value")
            unit = max_speed.get("unit", "km/h")
            if value is None:
                continue
            try:
                v = float(value)
            except (ValueError, TypeError):
                continue
            if "mph" in str(unit).lower():
                v *= 1.60934
            return v
    if isinstance(speed_limits, (int, float)) and not np.isnan(speed_limits):
        return float(speed_limits)
    return None


def _parse_level_rules(level_rules: object) -> int | None:
    """Extract numeric level from Overture level_rules structured field."""
    if level_rules is None or (isinstance(level_rules, float) and np.isnan(level_rules)):
        return None
    if isinstance(level_rules, (list, tuple)):
        for rule in level_rules:
            if not isinstance(rule, dict):
                continue
            value = rule.get("value")
            if value is not None:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    continue
    return None


def _is_bridge_from_level(level: object) -> bool:
    """level > 0 indicates a bridge or overpass."""
    if level is None or (isinstance(level, float) and np.isnan(level)):
        return False
    try:
        return int(level) > 0
    except (ValueError, TypeError):
        return False


def _is_tunnel_from_level(level: object) -> bool:
    """level < 0 indicates a tunnel or underpass."""
    if level is None or (isinstance(level, float) and np.isnan(level)):
        return False
    try:
        return int(level) < 0
    except (ValueError, TypeError):
        return False


def _parse_road_surface(road_surface: object) -> str | None:
    """Extract surface value from Overture road_surface structured field."""
    if road_surface is None or (isinstance(road_surface, float) and np.isnan(road_surface)):
        return None
    if isinstance(road_surface, str):
        return road_surface if road_surface else None
    if isinstance(road_surface, (list, tuple)):
        for entry in road_surface:
            if isinstance(entry, dict):
                val = entry.get("value")
                if val is not None:
                    return str(val)
            elif isinstance(entry, str):
                return entry
    return None


def _parse_width_rules(width_rules: object) -> float | None:
    """Extract numeric width from Overture width_rules structured field."""
    if width_rules is None or (isinstance(width_rules, float) and np.isnan(width_rules)):
        return None
    if isinstance(width_rules, (int, float)) and not np.isnan(width_rules):
        return float(width_rules)
    if isinstance(width_rules, (list, tuple)):
        for rule in width_rules:
            if not isinstance(rule, dict):
                continue
            value = rule.get("value")
            if value is None:
                continue
            try:
                return float(value)
            except (ValueError, TypeError):
                continue
    return None


def _parse_road_flags(road_flags: object) -> dict[str, bool]:
    """Extract is_link and is_under_construction from Overture road flags."""
    result = {"is_link": False, "is_under_construction": False}
    if road_flags is None or (isinstance(road_flags, float) and np.isnan(road_flags)):
        return result
    if isinstance(road_flags, (list, tuple)):
        for flag in road_flags:
            if isinstance(flag, str):
                if "link" in flag.lower():
                    result["is_link"] = True
                if "construction" in flag.lower():
                    result["is_under_construction"] = True
            elif isinstance(flag, dict):
                values = flag.get("values") or []
                if isinstance(values, (list, tuple)):
                    for v in values:
                        v_str = str(v).lower()
                        if "link" in v_str:
                            result["is_link"] = True
                        if "construction" in v_str:
                            result["is_under_construction"] = True
    return result


def _parse_access_restrictions(access_restrictions: object) -> dict[str, bool]:
    """Extract per-mode access denial flags from Overture access_restrictions."""
    result = {
        "denied_foot": False,
        "denied_bicycle": False,
        "denied_hgv": False,
        "has_any_restriction": False,
    }
    if access_restrictions is None or (isinstance(access_restrictions, float) and np.isnan(access_restrictions)):
        return result
    if not isinstance(access_restrictions, (list, tuple)):
        return result
    for entry in access_restrictions:
        if not isinstance(entry, dict):
            continue
        access_type = str(entry.get("access_type", "")).lower()
        if access_type != "denied":
            continue
        result["has_any_restriction"] = True
        when = entry.get("when")
        if not isinstance(when, dict):
            continue
        modes = when.get("mode", [])
        if not isinstance(modes, (list, tuple)):
            modes = [modes]
        for mode in modes:
            mode_str = str(mode).lower()
            if mode_str == "foot":
                result["denied_foot"] = True
            elif mode_str == "bicycle":
                result["denied_bicycle"] = True
            elif mode_str == "hgv":
                result["denied_hgv"] = True
    return result


def _parse_subclass_rules(subclass_rules: object) -> str | None:
    """Extract the dominant subclass value from Overture subclass_rules."""
    if subclass_rules is None or (isinstance(subclass_rules, float) and np.isnan(subclass_rules)):
        return None
    if isinstance(subclass_rules, str):
        return subclass_rules if subclass_rules else None
    if isinstance(subclass_rules, (list, tuple)):
        for rule in subclass_rules:
            if isinstance(rule, str):
                return rule
            if isinstance(rule, dict):
                value = rule.get("value")
                if value is not None:
                    return str(value)
    return None


def _parse_routes(routes: object) -> dict:
    """Extract route count and national route flag from Overture routes."""
    result = {"route_count": 0, "has_national_route": False}
    if routes is None or (isinstance(routes, float) and np.isnan(routes)):
        return result
    if not isinstance(routes, (list, tuple)):
        return result
    national_patterns = {"US:I", "US:US", "AU:N", "AU:A", "GB:M", "GB:A", "DE:B",
                         "FR:N", "FR:A", "IT:A", "ES:A", "JP:N", "NZ:SH", "CA:T"}
    seen_routes = set()
    for route in routes:
        if not isinstance(route, dict):
            continue
        network = route.get("network", "")
        ref = route.get("ref", "")
        route_key = f"{network}:{ref}"
        if route_key not in seen_routes:
            seen_routes.add(route_key)
        if isinstance(network, str) and network:
            for pat in national_patterns:
                if network.startswith(pat):
                    result["has_national_route"] = True
                    break
    result["route_count"] = len(seen_routes)
    return result


def _parse_road_name(names: object) -> str | None:
    """Extract primary road name from Overture names struct."""
    if names is None or (isinstance(names, float) and np.isnan(names)):
        return None
    if isinstance(names, dict):
        primary = names.get("primary")
        if primary and isinstance(primary, str):
            return primary
    return None


def _parse_speed_limits_full(speed_limits: object) -> dict:
    """Parse Overture speed_limits to extract max, min, and variable speed info."""
    result = {"max_speed_kmh": None, "min_speed_kmh": None, "is_variable": False}
    if speed_limits is None or (isinstance(speed_limits, float) and np.isnan(speed_limits)):
        return result
    if isinstance(speed_limits, (int, float)) and not np.isnan(speed_limits):
        result["max_speed_kmh"] = float(speed_limits)
        return result
    if not isinstance(speed_limits, (list, tuple)):
        return result

    def _convert_speed(speed_obj: dict) -> float | None:
        if not isinstance(speed_obj, dict):
            return None
        value = speed_obj.get("value")
        if value is None:
            return None
        try:
            v = float(value)
        except (ValueError, TypeError):
            return None
        unit = speed_obj.get("unit", "km/h")
        if "mph" in str(unit).lower():
            v *= 1.60934
        return v

    for limit in speed_limits:
        if not isinstance(limit, dict):
            continue
        # Max speed
        max_speed = limit.get("max_speed")
        if max_speed is not None and result["max_speed_kmh"] is None:
            result["max_speed_kmh"] = _convert_speed(max_speed)
        # Min speed
        min_speed = limit.get("min_speed")
        if min_speed is not None and result["min_speed_kmh"] is None:
            result["min_speed_kmh"] = _convert_speed(min_speed)
        # Variable speed (time-based scoping)
        when = limit.get("when")
        if isinstance(when, dict) and when.get("during"):
            result["is_variable"] = True
    return result


def _parse_categories_alternate(categories: object) -> str | None:
    """Join alternate categories into a pipe-separated string."""
    if categories is None or (isinstance(categories, float) and np.isnan(categories)):
        return None
    if isinstance(categories, str):
        return categories if categories else None
    if isinstance(categories, (list, tuple)):
        valid = [str(c) for c in categories if c is not None]
        return "|".join(valid) if valid else None
    return None


# ============================================================================
# Overture extraction functions
# ============================================================================


def _boundary_to_bounds(boundary_geom: Polygon | MultiPolygon) -> Bounds:
    minx, miny, maxx, maxy = boundary_geom.bounds
    return Bounds(min_lon=minx, min_lat=miny, max_lon=maxx, max_lat=maxy)


def _boundary_wkt(boundary_geom: Polygon | MultiPolygon) -> str:
    return boundary_geom.wkt


def extract_roads(
    boundary_geom: Polygon | MultiPolygon,
    release: str = OVERTURE_RELEASE,
) -> gpd.GeoDataFrame:
    """Extract road segments from Overture transportation/segment theme."""
    con = get_duckdb_connection()
    url = overture_s3_url("transportation", "segment", release=release)
    bounds = _boundary_to_bounds(boundary_geom)
    bbox_sql = bbox_filter_sql(bounds)
    wkt = _boundary_wkt(boundary_geom)

    query = f"""
        SELECT
            id AS overture_id,
            class AS road_class,
            speed_limits,
            road_surface,
            width_rules,
            road_flags,
            level_rules,
            access_restrictions,
            subclass_rules,
            names,
            routes,
            ST_AsWKB(geometry) AS geometry
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE {bbox_sql}
          AND subtype = 'road'
          AND ST_Intersects(geometry, ST_GeomFromText('{wkt}'))
    """

    logger.info("Extracting roads from Overture (release %s) ...", release)
    result = con.execute(query).fetchdf()

    if result.empty:
        logger.warning("No roads found in Overture for the given boundary")
        return gpd.GeoDataFrame(
            columns=[
                "geometry", "overture_id", "road_class", "speed_limit_kmh", "lanes",
                "is_bridge", "is_tunnel", "road_surface", "width_m", "is_link", "is_under_construction",
                "access_denied_foot", "access_denied_bicycle", "access_denied_hgv", "has_access_restriction",
                "subclass", "route_count", "has_national_route", "road_name",
                "min_speed_kmh", "is_variable_speed",
            ],
            geometry="geometry",
            crs="EPSG:4326",
        )

    gdf = gpd.GeoDataFrame(
        result,
        geometry=gpd.GeoSeries.from_wkb(result["geometry"].apply(bytes), crs="EPSG:4326"),
        crs="EPSG:4326",
    )

    if "speed_limits" in gdf.columns:
        gdf["speed_limit_kmh"] = gdf["speed_limits"].apply(_parse_overture_speed_limits)
    else:
        gdf["speed_limit_kmh"] = np.nan

    gdf["lanes"] = np.nan

    if "level_rules" in gdf.columns:
        gdf["_level"] = gdf["level_rules"].apply(_parse_level_rules)
        gdf["is_bridge"] = gdf["_level"].apply(_is_bridge_from_level)
        gdf["is_tunnel"] = gdf["_level"].apply(_is_tunnel_from_level)
        gdf.drop(columns=["_level"], inplace=True)
    else:
        gdf["is_bridge"] = False
        gdf["is_tunnel"] = False

    if "road_surface" in gdf.columns:
        gdf["road_surface"] = gdf["road_surface"].apply(_parse_road_surface)
    else:
        gdf["road_surface"] = None

    if "width_rules" in gdf.columns:
        gdf["width_m"] = gdf["width_rules"].apply(_parse_width_rules)
    else:
        gdf["width_m"] = np.nan

    if "road_flags" in gdf.columns:
        flags = gdf["road_flags"].apply(_parse_road_flags)
        gdf["is_link"] = flags.apply(lambda d: d["is_link"])
        gdf["is_under_construction"] = flags.apply(lambda d: d["is_under_construction"])
    else:
        gdf["is_link"] = False
        gdf["is_under_construction"] = False

    if "road_class" in gdf.columns:
        gdf["road_class"] = gdf["road_class"].fillna("unknown")
    else:
        gdf["road_class"] = "unknown"

    # --- Access restrictions ---
    if "access_restrictions" in gdf.columns:
        ar = gdf["access_restrictions"].apply(_parse_access_restrictions)
        gdf["access_denied_foot"] = ar.apply(lambda d: d["denied_foot"])
        gdf["access_denied_bicycle"] = ar.apply(lambda d: d["denied_bicycle"])
        gdf["access_denied_hgv"] = ar.apply(lambda d: d["denied_hgv"])
        gdf["has_access_restriction"] = ar.apply(lambda d: d["has_any_restriction"])
    else:
        gdf["access_denied_foot"] = False
        gdf["access_denied_bicycle"] = False
        gdf["access_denied_hgv"] = False
        gdf["has_access_restriction"] = False

    # --- Subclass ---
    if "subclass_rules" in gdf.columns:
        gdf["subclass"] = gdf["subclass_rules"].apply(_parse_subclass_rules)
    else:
        gdf["subclass"] = None

    # --- Routes ---
    if "routes" in gdf.columns:
        rt = gdf["routes"].apply(_parse_routes)
        gdf["route_count"] = rt.apply(lambda d: d["route_count"])
        gdf["has_national_route"] = rt.apply(lambda d: d["has_national_route"])
    else:
        gdf["route_count"] = 0
        gdf["has_national_route"] = False

    # --- Road name ---
    if "names" in gdf.columns:
        gdf["road_name"] = gdf["names"].apply(_parse_road_name)
    else:
        gdf["road_name"] = None

    # --- Richer speed limits ---
    if "speed_limits" in gdf.columns:
        sl = gdf["speed_limits"].apply(_parse_speed_limits_full)
        gdf["min_speed_kmh"] = sl.apply(lambda d: d["min_speed_kmh"])
        gdf["is_variable_speed"] = sl.apply(lambda d: d["is_variable"])
    else:
        gdf["min_speed_kmh"] = np.nan
        gdf["is_variable_speed"] = False

    keep_cols = [
        "geometry", "overture_id", "road_class", "speed_limit_kmh", "lanes",
        "is_bridge", "is_tunnel", "road_surface", "width_m", "is_link", "is_under_construction",
        "access_denied_foot", "access_denied_bicycle", "access_denied_hgv", "has_access_restriction",
        "subclass", "route_count", "has_national_route", "road_name",
        "min_speed_kmh", "is_variable_speed",
    ]
    gdf = gdf[[c for c in keep_cols if c in gdf.columns]].copy()

    gdf = gdf[gdf.geometry.geom_type.isin(["LineString", "MultiLineString"])].copy()
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].copy()

    logger.info("Extracted %d road segments", len(gdf))
    return gdf


def extract_places(
    boundary_geom: Polygon | MultiPolygon,
    release: str = OVERTURE_RELEASE,
) -> gpd.GeoDataFrame:
    """Extract places (POIs) from Overture places/place theme."""
    con = get_duckdb_connection()
    url = overture_s3_url("places", "place", release=release)
    bounds = _boundary_to_bounds(boundary_geom)
    bbox_sql = bbox_filter_sql(bounds)
    wkt = _boundary_wkt(boundary_geom)

    query = f"""
        SELECT
            id AS overture_id,
            names.primary AS name,
            categories.primary AS category,
            categories.alternate AS categories_alt_raw,
            confidence,
            ST_AsWKB(geometry) AS geometry
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE {bbox_sql}
          AND ST_Intersects(geometry, ST_GeomFromText('{wkt}'))
    """

    logger.info("Extracting places from Overture (release %s) ...", release)
    result = con.execute(query).fetchdf()

    if result.empty:
        logger.warning("No places found in Overture for the given boundary")
        return gpd.GeoDataFrame(
            columns=["geometry", "overture_id", "name", "category", "confidence", "categories_alt"],
            geometry="geometry",
            crs="EPSG:4326",
        )

    gdf = gpd.GeoDataFrame(
        result,
        geometry=gpd.GeoSeries.from_wkb(result["geometry"].apply(bytes), crs="EPSG:4326"),
        crs="EPSG:4326",
    )

    gdf["category"] = gdf["category"].fillna("unknown")

    if "categories_alt_raw" in gdf.columns:
        gdf["categories_alt"] = gdf["categories_alt_raw"].apply(_parse_categories_alternate)
    else:
        gdf["categories_alt"] = None

    keep_cols = ["geometry", "overture_id", "name", "category", "confidence", "categories_alt"]
    gdf = gdf[[c for c in keep_cols if c in gdf.columns]].copy()

    gdf = gdf[gdf.geometry.geom_type.isin(["Point", "MultiPoint"])].copy()
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].copy()

    logger.info("Extracted %d places", len(gdf))
    return gdf


def extract_buildings(
    boundary_geom: Polygon | MultiPolygon,
    release: str = OVERTURE_RELEASE,
    projected_crs: str | None = None,
) -> gpd.GeoDataFrame:
    """Extract buildings from Overture buildings/building theme."""
    con = get_duckdb_connection()
    url = overture_s3_url("buildings", "building", release=release)
    bounds = _boundary_to_bounds(boundary_geom)
    bbox_sql = bbox_filter_sql(bounds)
    wkt = _boundary_wkt(boundary_geom)

    query = f"""
        SELECT
            id AS overture_id,
            class AS building_class,
            height,
            num_floors,
            facade_material,
            roof_material,
            roof_shape,
            roof_height,
            num_floors_underground,
            is_underground,
            ST_AsWKB(geometry) AS geometry
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE {bbox_sql}
          AND ST_Intersects(geometry, ST_GeomFromText('{wkt}'))
    """

    logger.info("Extracting buildings from Overture (release %s) ...", release)
    result = con.execute(query).fetchdf()

    if result.empty:
        logger.warning("No buildings found in Overture for the given boundary")
        return gpd.GeoDataFrame(
            columns=[
                "geometry", "overture_id", "building_class", "height", "num_floors", "area_m2",
                "facade_material", "roof_material", "roof_shape", "roof_height",
                "num_floors_underground", "is_underground",
            ],
            geometry="geometry",
            crs="EPSG:4326",
        )

    gdf = gpd.GeoDataFrame(
        result,
        geometry=gpd.GeoSeries.from_wkb(result["geometry"].apply(bytes), crs="EPSG:4326"),
        crs="EPSG:4326",
    )

    for col in ("height", "num_floors", "roof_height", "num_floors_underground"):
        if col in gdf.columns:
            gdf[col] = pd.to_numeric(gdf[col], errors="coerce")
        else:
            gdf[col] = np.nan

    gdf["building_class"] = gdf.get("building_class", pd.Series(["unknown"] * len(gdf))).fillna("unknown")

    for col in ("facade_material", "roof_material", "roof_shape"):
        if col not in gdf.columns:
            gdf[col] = None

    if "is_underground" in gdf.columns:
        gdf["is_underground"] = gdf["is_underground"].fillna(False).astype(bool)
    else:
        gdf["is_underground"] = False

    gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].copy()

    if projected_crs is None:
        centroid = boundary_geom.centroid
        projected_crs = utm_crs_from_lonlat(centroid.x, centroid.y)
    gdf["area_m2"] = gdf.to_crs(projected_crs).geometry.area

    keep_cols = [
        "geometry", "overture_id", "building_class", "height", "num_floors", "area_m2",
        "facade_material", "roof_material", "roof_shape", "roof_height",
        "num_floors_underground", "is_underground",
    ]
    gdf = gdf[[c for c in keep_cols if c in gdf.columns]].copy()

    logger.info("Extracted %d buildings", len(gdf))
    return gdf


def extract_land_use(
    boundary_geom: Polygon | MultiPolygon,
    release: str = OVERTURE_RELEASE,
    projected_crs: str | None = None,
) -> gpd.GeoDataFrame:
    """Extract land use from Overture base/land_use + base/land + base/water."""
    con = get_duckdb_connection()
    bounds = _boundary_to_bounds(boundary_geom)
    bbox_sql = bbox_filter_sql(bounds)
    wkt = _boundary_wkt(boundary_geom)

    parts: list[gpd.GeoDataFrame] = []

    subtype_configs = {
        "land_use": {"label": "land_use", "extra_cols": "subtype AS land_subtype, surface,"},
        "land": {"label": "land", "extra_cols": "surface,"},
        "water": {"label": "water", "extra_cols": "is_salt, is_intermittent,"},
    }

    for type_name, cfg in subtype_configs.items():
        url = overture_s3_url("base", type_name, release=release)
        extra = cfg["extra_cols"]
        query = f"""
            SELECT
                id AS overture_id,
                class AS land_class,
                {extra}
                ST_AsWKB(geometry) AS geometry
            FROM read_parquet('{url}', hive_partitioning=true)
            WHERE {bbox_sql}
              AND ST_Intersects(geometry, ST_GeomFromText('{wkt}'))
        """

        try:
            result = con.execute(query).fetchdf()
            if not result.empty:
                gdf = gpd.GeoDataFrame(
                    result,
                    geometry=gpd.GeoSeries.from_wkb(result["geometry"].apply(bytes), crs="EPSG:4326"),
                    crs="EPSG:4326",
                )
                gdf["land_type"] = cfg["label"]
                gdf["land_class"] = gdf["land_class"].fillna("unknown")
                for col in ("land_subtype", "surface", "is_salt", "is_intermittent"):
                    if col not in gdf.columns:
                        gdf[col] = None
                for bool_col in ("is_salt", "is_intermittent"):
                    if bool_col in gdf.columns:
                        gdf[bool_col] = gdf[bool_col].fillna(False).astype(bool)
                parts.append(gdf)
        except Exception as exc:
            logger.warning("Could not extract %s: %s", type_name, exc)

    if not parts:
        logger.warning("No land use features found in Overture for the given boundary")
        return gpd.GeoDataFrame(
            columns=[
                "geometry", "overture_id", "land_type", "land_class", "area_m2",
                "land_subtype", "surface", "is_salt", "is_intermittent",
            ],
            geometry="geometry",
            crs="EPSG:4326",
        )

    combined = pd.concat(parts, ignore_index=True)
    combined = gpd.GeoDataFrame(combined, geometry="geometry", crs="EPSG:4326")

    combined = combined[combined.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    combined = combined[~combined.geometry.is_empty & combined.geometry.notna()].copy()

    if projected_crs is None:
        centroid = boundary_geom.centroid
        projected_crs = utm_crs_from_lonlat(centroid.x, centroid.y)
    combined["area_m2"] = combined.to_crs(projected_crs).geometry.area

    keep_cols = [
        "geometry", "overture_id", "land_type", "land_class", "area_m2",
        "land_subtype", "surface", "is_salt", "is_intermittent",
    ]
    combined = combined[[c for c in keep_cols if c in combined.columns]].copy()

    logger.info("Extracted %d land use features", len(combined))
    return combined


def extract_addresses(
    boundary_geom: Polygon | MultiPolygon,
    release: str = OVERTURE_RELEASE,
) -> gpd.GeoDataFrame:
    """Extract addresses from Overture addresses/address theme."""
    con = get_duckdb_connection()
    bounds = _boundary_to_bounds(boundary_geom)
    bbox_sql = bbox_filter_sql(bounds)
    wkt = _boundary_wkt(boundary_geom)

    url = overture_s3_url("addresses", "address", release=release)
    query = f"""
        SELECT
            id AS overture_id,
            number,
            street,
            postcode,
            unit,
            country,
            ST_AsWKB(geometry) AS geometry
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE {bbox_sql}
          AND ST_Intersects(geometry, ST_GeomFromText('{wkt}'))
    """

    logger.info("Extracting addresses from Overture (release %s) ...", release)
    result = con.execute(query).fetchdf()

    if result.empty:
        logger.warning("No addresses found in Overture for the given boundary")
        return gpd.GeoDataFrame(
            columns=["geometry", "overture_id", "number", "street", "postcode", "unit", "country"],
            geometry="geometry", crs="EPSG:4326",
        )

    gdf = gpd.GeoDataFrame(
        result,
        geometry=gpd.GeoSeries.from_wkb(result["geometry"].apply(bytes), crs="EPSG:4326"),
        crs="EPSG:4326",
    )
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()

    logger.info("Extracted %d addresses", len(gdf))
    return gdf


def extract_infrastructure(
    boundary_geom: Polygon | MultiPolygon,
    release: str = OVERTURE_RELEASE,
) -> gpd.GeoDataFrame:
    """Extract infrastructure from Overture base/infrastructure theme."""
    con = get_duckdb_connection()
    bounds = _boundary_to_bounds(boundary_geom)
    bbox_sql = bbox_filter_sql(bounds)
    wkt = _boundary_wkt(boundary_geom)

    url = overture_s3_url("base", "infrastructure", release=release)
    query = f"""
        SELECT
            id AS overture_id,
            class AS infra_class,
            subtype AS infra_subtype,
            ST_AsWKB(geometry) AS geometry
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE {bbox_sql}
          AND ST_Intersects(geometry, ST_GeomFromText('{wkt}'))
    """

    logger.info("Extracting infrastructure from Overture (release %s) ...", release)
    result = con.execute(query).fetchdf()

    if result.empty:
        logger.warning("No infrastructure found in Overture for the given boundary")
        return gpd.GeoDataFrame(
            columns=["geometry", "overture_id", "infra_class", "infra_subtype"],
            geometry="geometry", crs="EPSG:4326",
        )

    gdf = gpd.GeoDataFrame(
        result,
        geometry=gpd.GeoSeries.from_wkb(result["geometry"].apply(bytes), crs="EPSG:4326"),
        crs="EPSG:4326",
    )
    gdf["infra_class"] = gdf["infra_class"].fillna("unknown")
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()

    logger.info("Extracted %d infrastructure features", len(gdf))
    return gdf


def extract_land_cover(
    boundary_geom: Polygon | MultiPolygon,
    release: str = OVERTURE_RELEASE,
    projected_crs: str | None = None,
) -> gpd.GeoDataFrame:
    """Extract land cover from Overture base/land_cover theme."""
    con = get_duckdb_connection()
    bounds = _boundary_to_bounds(boundary_geom)
    bbox_sql = bbox_filter_sql(bounds)
    wkt = _boundary_wkt(boundary_geom)

    url = overture_s3_url("base", "land_cover", release=release)
    query = f"""
        SELECT
            id AS overture_id,
            subtype AS landcover_subtype,
            ST_AsWKB(geometry) AS geometry
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE {bbox_sql}
          AND ST_Intersects(geometry, ST_GeomFromText('{wkt}'))
    """

    logger.info("Extracting land cover from Overture (release %s) ...", release)
    result = con.execute(query).fetchdf()

    if result.empty:
        logger.warning("No land cover found in Overture for the given boundary")
        return gpd.GeoDataFrame(
            columns=["geometry", "overture_id", "landcover_subtype", "area_m2"],
            geometry="geometry", crs="EPSG:4326",
        )

    gdf = gpd.GeoDataFrame(
        result,
        geometry=gpd.GeoSeries.from_wkb(result["geometry"].apply(bytes), crs="EPSG:4326"),
        crs="EPSG:4326",
    )
    gdf["landcover_subtype"] = gdf["landcover_subtype"].fillna("unknown")
    gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].copy()

    if projected_crs is None:
        centroid = boundary_geom.centroid
        projected_crs = utm_crs_from_lonlat(centroid.x, centroid.y)
    gdf["area_m2"] = gdf.to_crs(projected_crs).geometry.area

    logger.info("Extracted %d land cover features", len(gdf))
    return gdf


def extract_connectors(
    boundary_geom: Polygon | MultiPolygon,
    release: str = OVERTURE_RELEASE,
) -> gpd.GeoDataFrame:
    """Extract transportation connectors (intersections) from Overture."""
    con = get_duckdb_connection()
    bounds = _boundary_to_bounds(boundary_geom)
    bbox_sql = bbox_filter_sql(bounds)
    wkt = _boundary_wkt(boundary_geom)

    url = overture_s3_url("transportation", "connector", release=release)
    query = f"""
        SELECT
            id AS overture_id,
            ST_AsWKB(geometry) AS geometry
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE {bbox_sql}
          AND ST_Intersects(geometry, ST_GeomFromText('{wkt}'))
    """

    logger.info("Extracting connectors from Overture (release %s) ...", release)
    result = con.execute(query).fetchdf()

    if result.empty:
        logger.warning("No connectors found in Overture for the given boundary")
        return gpd.GeoDataFrame(
            columns=["geometry", "overture_id"],
            geometry="geometry", crs="EPSG:4326",
        )

    gdf = gpd.GeoDataFrame(
        result,
        geometry=gpd.GeoSeries.from_wkb(result["geometry"].apply(bytes), crs="EPSG:4326"),
        crs="EPSG:4326",
    )
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()

    logger.info("Extracted %d connectors", len(gdf))
    return gdf


def extract_building_parts(
    boundary_geom: Polygon | MultiPolygon,
    release: str = OVERTURE_RELEASE,
    projected_crs: str | None = None,
) -> gpd.GeoDataFrame:
    """Extract building parts from Overture buildings/building_part theme."""
    con = get_duckdb_connection()
    bounds = _boundary_to_bounds(boundary_geom)
    bbox_sql = bbox_filter_sql(bounds)
    wkt = _boundary_wkt(boundary_geom)

    url = overture_s3_url("buildings", "building_part", release=release)
    query = f"""
        SELECT
            id AS overture_id,
            building_id,
            height,
            num_floors,
            num_floors_underground,
            is_underground,
            min_height,
            ST_AsWKB(geometry) AS geometry
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE {bbox_sql}
          AND ST_Intersects(geometry, ST_GeomFromText('{wkt}'))
    """

    logger.info("Extracting building parts from Overture (release %s) ...", release)
    result = con.execute(query).fetchdf()

    if result.empty:
        logger.warning("No building parts found in Overture for the given boundary")
        return gpd.GeoDataFrame(
            columns=[
                "geometry", "overture_id", "building_id", "height",
                "num_floors", "num_floors_underground", "is_underground",
                "min_height", "area_m2",
            ],
            geometry="geometry", crs="EPSG:4326",
        )

    gdf = gpd.GeoDataFrame(
        result,
        geometry=gpd.GeoSeries.from_wkb(result["geometry"].apply(bytes), crs="EPSG:4326"),
        crs="EPSG:4326",
    )

    for col in ("height", "num_floors", "num_floors_underground", "min_height"):
        if col in gdf.columns:
            gdf[col] = pd.to_numeric(gdf[col], errors="coerce")
        else:
            gdf[col] = np.nan

    if "is_underground" in gdf.columns:
        gdf["is_underground"] = gdf["is_underground"].fillna(False).astype(bool)
    else:
        gdf["is_underground"] = False

    gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].copy()

    if projected_crs is None:
        centroid = boundary_geom.centroid
        projected_crs = utm_crs_from_lonlat(centroid.x, centroid.y)
    gdf["area_m2"] = gdf.to_crs(projected_crs).geometry.area

    logger.info("Extracted %d building parts", len(gdf))
    return gdf


def extract_divisions(
    boundary_geom: Polygon | MultiPolygon,
    release: str = OVERTURE_RELEASE,
    projected_crs: str | None = None,
) -> dict[str, gpd.GeoDataFrame]:
    """Extract all 3 division types from Overture divisions theme.

    Returns dict with keys 'division', 'division_area', 'division_boundary'.
    """
    con = get_duckdb_connection()
    bounds = _boundary_to_bounds(boundary_geom)
    bbox_sql = bbox_filter_sql(bounds)
    wkt = _boundary_wkt(boundary_geom)

    results: dict[str, gpd.GeoDataFrame] = {}

    # Division points
    url = overture_s3_url("divisions", "division", release=release)
    query = f"""
        SELECT
            id AS overture_id,
            subtype AS division_subtype,
            class AS division_class,
            admin_level,
            population,
            ST_AsWKB(geometry) AS geometry
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE {bbox_sql}
          AND ST_Intersects(geometry, ST_GeomFromText('{wkt}'))
    """
    try:
        logger.info("Extracting divisions from Overture (release %s) ...", release)
        df = con.execute(query).fetchdf()
        if not df.empty:
            gdf = gpd.GeoDataFrame(
                df,
                geometry=gpd.GeoSeries.from_wkb(df["geometry"].apply(bytes), crs="EPSG:4326"),
                crs="EPSG:4326",
            )
            gdf["admin_level"] = pd.to_numeric(gdf["admin_level"], errors="coerce")
            gdf["population"] = pd.to_numeric(gdf["population"], errors="coerce")
            results["division"] = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
            logger.info("Extracted %d division points", len(results["division"]))
    except Exception as exc:
        logger.warning("Could not extract divisions: %s", exc)

    # Division areas
    url = overture_s3_url("divisions", "division_area", release=release)
    query = f"""
        SELECT
            id AS overture_id,
            subtype AS division_subtype,
            class AS area_class,
            admin_level,
            is_land,
            ST_AsWKB(geometry) AS geometry
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE {bbox_sql}
          AND ST_Intersects(geometry, ST_GeomFromText('{wkt}'))
    """
    try:
        logger.info("Extracting division areas from Overture (release %s) ...", release)
        df = con.execute(query).fetchdf()
        if not df.empty:
            gdf = gpd.GeoDataFrame(
                df,
                geometry=gpd.GeoSeries.from_wkb(df["geometry"].apply(bytes), crs="EPSG:4326"),
                crs="EPSG:4326",
            )
            gdf["admin_level"] = pd.to_numeric(gdf["admin_level"], errors="coerce")
            gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
            results["division_area"] = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].copy()
            logger.info("Extracted %d division areas", len(results["division_area"]))
    except Exception as exc:
        logger.warning("Could not extract division areas: %s", exc)

    # Division boundaries
    url = overture_s3_url("divisions", "division_boundary", release=release)
    query = f"""
        SELECT
            id AS overture_id,
            ST_AsWKB(geometry) AS geometry
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE {bbox_sql}
          AND ST_Intersects(geometry, ST_GeomFromText('{wkt}'))
    """
    try:
        logger.info("Extracting division boundaries from Overture (release %s) ...", release)
        df = con.execute(query).fetchdf()
        if not df.empty:
            gdf = gpd.GeoDataFrame(
                df,
                geometry=gpd.GeoSeries.from_wkb(df["geometry"].apply(bytes), crs="EPSG:4326"),
                crs="EPSG:4326",
            )
            results["division_boundary"] = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
            logger.info("Extracted %d division boundaries", len(results["division_boundary"]))
    except Exception as exc:
        logger.warning("Could not extract division boundaries: %s", exc)

    return results


def extract_bathymetry(
    boundary_geom: Polygon | MultiPolygon,
    release: str = OVERTURE_RELEASE,
    projected_crs: str | None = None,
) -> gpd.GeoDataFrame:
    """Extract bathymetry from Overture base/bathymetry theme."""
    con = get_duckdb_connection()
    bounds = _boundary_to_bounds(boundary_geom)
    bbox_sql = bbox_filter_sql(bounds)
    wkt = _boundary_wkt(boundary_geom)

    url = overture_s3_url("base", "bathymetry", release=release)
    query = f"""
        SELECT
            id AS overture_id,
            ST_AsWKB(geometry) AS geometry
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE {bbox_sql}
          AND ST_Intersects(geometry, ST_GeomFromText('{wkt}'))
    """

    logger.info("Extracting bathymetry from Overture (release %s) ...", release)
    try:
        result = con.execute(query).fetchdf()
    except Exception as exc:
        logger.warning("Could not extract bathymetry: %s", exc)
        return gpd.GeoDataFrame(
            columns=["geometry", "overture_id", "area_m2"],
            geometry="geometry", crs="EPSG:4326",
        )

    if result.empty:
        logger.warning("No bathymetry found in Overture for the given boundary")
        return gpd.GeoDataFrame(
            columns=["geometry", "overture_id", "area_m2"],
            geometry="geometry", crs="EPSG:4326",
        )

    gdf = gpd.GeoDataFrame(
        result,
        geometry=gpd.GeoSeries.from_wkb(result["geometry"].apply(bytes), crs="EPSG:4326"),
        crs="EPSG:4326",
    )
    gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].copy()

    if projected_crs is None:
        centroid = boundary_geom.centroid
        projected_crs = utm_crs_from_lonlat(centroid.x, centroid.y)
    if not gdf.empty:
        gdf["area_m2"] = gdf.to_crs(projected_crs).geometry.area
    else:
        gdf["area_m2"] = pd.Series(dtype=float)

    logger.info("Extracted %d bathymetry features", len(gdf))
    return gdf


# ============================================================================
# Cache invalidation + extract_all
# ============================================================================


def _needs_reextraction(parquet_path: Path, schema: list[ColumnSpec]) -> bool:
    """Check if an existing parquet file is missing columns from the schema."""
    if not parquet_path.exists():
        return True
    try:
        import pyarrow.parquet as pq
        pq_schema = pq.read_schema(parquet_path)
        existing_cols = set(pq_schema.names)
        expected_cols = {s.name for s in schema if s.name != "geometry"}
        missing = expected_cols - existing_cols
        if missing:
            logger.info("Cache miss for %s: missing columns %s", parquet_path.name, sorted(missing))
            return True
        return False
    except Exception:
        return True


def _count_parquet_rows(path: Path) -> int:
    """Count rows in a parquet file without loading it fully."""
    try:
        import pyarrow.parquet as pq
        return pq.read_metadata(path).num_rows
    except Exception:
        return -1


def extract_all(
    boundary_geom: Polygon | MultiPolygon,
    out_dir: Path,
    layers: list[str] | None = None,
    release: str = OVERTURE_RELEASE,
    projected_crs: str | None = None,
) -> dict[str, Path]:
    """Run all Overture extraction steps and save results."""
    if layers is None:
        layers = ALL_LAYERS

    ensure_dir(out_dir)
    results: dict[str, Path] = {}

    _extractors = {
        "roads": (lambda: extract_roads(boundary_geom, release=release), ROADS_SCHEMA, "roads.parquet"),
        "pois": (lambda: extract_places(boundary_geom, release=release), POIS_SCHEMA, "pois.parquet"),
        "buildings": (lambda: extract_buildings(boundary_geom, release=release, projected_crs=projected_crs), BUILDINGS_SCHEMA, "buildings.parquet"),
        "landuse": (lambda: extract_land_use(boundary_geom, release=release, projected_crs=projected_crs), LANDUSE_SCHEMA, "landuse.parquet"),
        "addresses": (lambda: extract_addresses(boundary_geom, release=release), None, "addresses.parquet"),
        "infrastructure": (lambda: extract_infrastructure(boundary_geom, release=release), None, "infrastructure.parquet"),
        "land_cover": (lambda: extract_land_cover(boundary_geom, release=release, projected_crs=projected_crs), None, "land_cover.parquet"),
        "connectors": (lambda: extract_connectors(boundary_geom, release=release), None, "connectors.parquet"),
        "building_parts": (lambda: extract_building_parts(boundary_geom, release=release, projected_crs=projected_crs), None, "building_parts.parquet"),
        "bathymetry": (lambda: extract_bathymetry(boundary_geom, release=release, projected_crs=projected_crs), None, "bathymetry.parquet"),
    }

    for layer_name in layers:
        # Divisions are special — extract_divisions returns a dict of 3 GeoDataFrames
        if layer_name == "divisions":
            div_dir = out_dir
            div_files = ["divisions.parquet", "division_areas.parquet", "division_boundaries.parquet"]
            if all((div_dir / f).exists() for f in div_files):
                logger.info("Skipping divisions (cache valid)")
                results["divisions"] = div_dir / "divisions.parquet"
                continue
            try:
                div_data = extract_divisions(boundary_geom, release=release, projected_crs=projected_crs)
                for key, fname in [("division", "divisions.parquet"),
                                   ("division_area", "division_areas.parquet"),
                                   ("division_boundary", "division_boundaries.parquet")]:
                    if key in div_data and not div_data[key].empty:
                        save_geodataframe(div_data[key], div_dir / fname)
                    else:
                        # Save empty GeoDataFrame to mark as extracted
                        empty = gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs="EPSG:4326")
                        save_geodataframe(empty, div_dir / fname)
                results["divisions"] = div_dir / "divisions.parquet"
            except Exception as exc:
                logger.warning("Division extraction failed: %s", exc)
            continue

        if layer_name not in _extractors:
            continue
        extract_fn, schema, filename = _extractors[layer_name]
        path = out_dir / filename

        if schema is not None and not _needs_reextraction(path, schema):
            logger.info("Skipping %s (cache valid, all columns present)", layer_name)
            results[layer_name] = path
            continue
        elif schema is None and path.exists():
            logger.info("Skipping %s (cache exists)", layer_name)
            results[layer_name] = path
            continue

        try:
            gdf = extract_fn()
            save_geodataframe(gdf, path)
            if schema is not None:
                errors = validate_dataframe(gdf, schema)
                if errors:
                    logger.warning("%s schema warnings: %s", layer_name.capitalize(), errors)
            results[layer_name] = path
        except Exception as exc:
            logger.warning("%s extraction failed: %s", layer_name.capitalize(), exc)

    metadata = {
        "source": "overture",
        "release": release,
        "schema_version": SCHEMA_VERSION,
        "layers_extracted": list(results.keys()),
        "row_counts": {k: _count_parquet_rows(v) for k, v in results.items()},
        "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    save_json(metadata, out_dir / "extraction_metadata.json")

    return results


# ============================================================================
# H3 Hex Grid
# ============================================================================


def _generate_h3_hex_grid(
    boundary_geom: Polygon | MultiPolygon,
    resolution: int,
) -> gpd.GeoDataFrame:
    """Generate an H3 hex grid covering *boundary_geom* at *resolution*.

    Returns a GeoDataFrame with columns ``hex_id`` and ``geometry`` (EPSG:4326).
    """
    import h3  # lazy import

    cell_ids = h3.geo_to_cells(boundary_geom.__geo_interface__, resolution)

    records = []
    for cell in cell_ids:
        # h3-py v4: cell_to_boundary returns list of (lat, lng) tuples
        boundary_coords = h3.cell_to_boundary(cell)
        # flip to (lng, lat) for Shapely
        coords_lonlat = [(lng, lat) for lat, lng in boundary_coords]
        records.append({"hex_id": cell, "geometry": Polygon(coords_lonlat)})

    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")
    logger.info(
        "Generated %d H3 hexes at resolution %d", len(gdf), resolution
    )
    return gdf


# ============================================================================
# OSM Hex Aggregation — comprehensive features for traffic FM training
# ============================================================================

# Land use categories for green/built fraction computation
_GREEN_TYPES = frozenset({
    "forest", "grass", "meadow", "recreation_ground", "park", "nature_reserve",
    "wood", "scrub", "wetland", "grassland", "garden",
    "farmland", "orchard", "vineyard",
})
_BUILT_TYPES = frozenset({
    "residential", "commercial", "industrial", "retail", "construction",
    "institutional", "military", "railway",
    "education", "medical", "transportation",
})


def _aggregate_roads_to_hexes(
    roads_gdf: gpd.GeoDataFrame,
    hex_gdf: gpd.GeoDataFrame,
    projected_crs: str,
) -> pd.DataFrame:
    """Comprehensive road feature aggregation per hex via spatial intersection.

    Produces: total_road_length_m, road_segment_count, avg_edge_length_m,
    per-road-class lengths, speed stats, bridge/tunnel/link/construction
    fractions, surface coverage %, width coverage %.
    """
    if roads_gdf.empty or hex_gdf.empty:
        return pd.DataFrame(columns=["hex_id", "total_road_length_m"])

    # Keep all road attributes through the spatial intersection
    keep_cols = ["geometry", "overture_id", "road_class"]
    for c in ("speed_limit_kmh", "is_bridge", "is_tunnel", "is_link",
              "is_under_construction", "road_surface", "width_m",
              "access_denied_foot", "access_denied_bicycle", "access_denied_hgv",
              "has_access_restriction", "subclass", "route_count",
              "has_national_route", "road_name", "min_speed_kmh", "is_variable_speed"):
        if c in roads_gdf.columns:
            keep_cols.append(c)

    roads_proj = roads_gdf[keep_cols].to_crs(projected_crs)
    hexes_proj = hex_gdf[["hex_id", "geometry"]].to_crs(projected_crs)

    df = gpd.overlay(roads_proj, hexes_proj, how="intersection", keep_geom_type=False)
    if df.empty:
        return pd.DataFrame(columns=["hex_id", "total_road_length_m"])

    df["length_m"] = df.geometry.length

    # --- Core metrics ---
    total_length = df.groupby("hex_id")["length_m"].sum().rename("total_road_length_m")
    segment_count = df.groupby("hex_id").size().rename("road_segment_count")
    avg_edge = df.groupby("hex_id")["length_m"].mean().rename("avg_edge_length_m")

    parts = [total_length, segment_count, avg_edge]

    # --- Per road class lengths (global registry) ---
    if "road_class" in df.columns:
        registry_classes = set(GLOBAL_FEATURE_REGISTRY["road_classes"])
        df["road_class"] = df["road_class"].where(df["road_class"].isin(registry_classes), "other")
        class_agg = df.groupby(["hex_id", "road_class"])["length_m"].sum().reset_index()
        class_pivot = class_agg.pivot_table(
            index="hex_id", columns="road_class", values="length_m",
            aggfunc="sum", fill_value=0,
        )
        class_pivot.columns = [f"road_length_{c}_m" for c in class_pivot.columns]
        for cls in GLOBAL_FEATURE_REGISTRY["road_classes"]:
            col = f"road_length_{cls}_m"
            if col not in class_pivot.columns:
                class_pivot[col] = 0
        if "road_length_other_m" not in class_pivot.columns:
            class_pivot["road_length_other_m"] = 0
        parts.append(class_pivot)

    # --- Speed stats (length-weighted average + coverage %) ---
    if "speed_limit_kmh" in df.columns:
        has_speed = df["speed_limit_kmh"].notna()
        if bool(has_speed.any()):
            speed_df = df.loc[has_speed].copy()
            speed_df["_wt"] = speed_df["speed_limit_kmh"] * speed_df["length_m"]
            speed_g = speed_df.groupby("hex_id")
            avg_speed = (speed_g["_wt"].sum() / speed_g["length_m"].sum()).rename("avg_maxspeed_kmh")
            speed_len = speed_g["length_m"].sum()
            speed_cov = (speed_len / total_length).rename("maxspeed_coverage_pct")
            parts.extend([avg_speed, speed_cov])

    # --- Min speed stats ---
    if "min_speed_kmh" in df.columns:
        has_min = df["min_speed_kmh"].notna()
        if bool(has_min.any()):
            min_df = df.loc[has_min].copy()
            min_df["_wt"] = min_df["min_speed_kmh"] * min_df["length_m"]
            min_g = min_df.groupby("hex_id")
            avg_min = (min_g["_wt"].sum() / min_g["length_m"].sum()).rename("avg_min_speed_kmh")
            min_len = min_g["length_m"].sum()
            min_cov = (min_len / total_length).rename("min_speed_coverage_pct")
            parts.extend([avg_min, min_cov])

    # --- Variable speed coverage ---
    if "is_variable_speed" in df.columns:
        flag = df["is_variable_speed"].astype(float).fillna(0)
        weighted = (flag * df["length_m"]).groupby(df["hex_id"]).sum()
        frac = (weighted / total_length).rename("has_variable_speed_pct")
        parts.append(frac)

    # --- Bridge / tunnel / link / under_construction fractions ---
    for bool_col in ("is_bridge", "is_tunnel", "is_link", "is_under_construction"):
        if bool_col in df.columns:
            flag = df[bool_col].astype(float).fillna(0)
            weighted = (flag * df["length_m"]).groupby(df["hex_id"]).sum()
            frac = (weighted / total_length).rename(f"pct_{bool_col}_length")
            parts.append(frac)

    # --- Road surface coverage % ---
    if "road_surface" in df.columns:
        has_surface = df["road_surface"].notna()
        if bool(has_surface.any()):
            surf_len = df.loc[has_surface].groupby("hex_id")["length_m"].sum()
            surf_cov = (surf_len / total_length).rename("road_surface_coverage_pct")
            parts.append(surf_cov)

    # --- Road surface type breakdown (paved vs unpaved + per-type lengths) ---
    if "road_surface" in df.columns:
        has_surface = df["road_surface"].notna()
        if bool(has_surface.any()):
            paved_types = {"paved", "asphalt", "concrete", "sett", "cobblestone", "metal"}
            unpaved_types = {"unpaved", "gravel", "dirt", "compacted", "ground", "wood"}
            surf_df = df.loc[has_surface].copy()
            surf_df["_is_paved"] = surf_df["road_surface"].isin(paved_types).astype(float)
            surf_df["_is_unpaved"] = surf_df["road_surface"].isin(unpaved_types).astype(float)
            paved_len = (surf_df["_is_paved"] * surf_df["length_m"]).groupby(surf_df["hex_id"]).sum()
            unpaved_len = (surf_df["_is_unpaved"] * surf_df["length_m"]).groupby(surf_df["hex_id"]).sum()
            paved_pct = (paved_len / total_length).rename("road_surface_paved_pct")
            unpaved_pct = (unpaved_len / total_length).rename("road_surface_unpaved_pct")
            parts.extend([paved_pct, unpaved_pct])
            # Per surface type lengths
            registry_surfaces = set(GLOBAL_FEATURE_REGISTRY["road_surface_types"])
            surf_df["_surf_type"] = surf_df["road_surface"].where(
                surf_df["road_surface"].isin(registry_surfaces), "other"
            )
            surf_agg = surf_df.groupby(["hex_id", "_surf_type"])["length_m"].sum().reset_index()
            surf_pivot = surf_agg.pivot_table(
                index="hex_id", columns="_surf_type", values="length_m",
                aggfunc="sum", fill_value=0,
            )
            surf_pivot.columns = [f"road_surface_length_{c}_m" for c in surf_pivot.columns]
            for st in GLOBAL_FEATURE_REGISTRY["road_surface_types"]:
                col = f"road_surface_length_{st}_m"
                if col not in surf_pivot.columns:
                    surf_pivot[col] = 0
            if "road_surface_length_other_m" not in surf_pivot.columns:
                surf_pivot["road_surface_length_other_m"] = 0
            parts.append(surf_pivot)

    # --- Width stats (length-weighted average + max) ---
    if "width_m" in df.columns:
        has_width = df["width_m"].notna()
        if bool(has_width.any()):
            width_len = df.loc[has_width].groupby("hex_id")["length_m"].sum()
            width_cov = (width_len / total_length).rename("road_width_coverage_pct")
            parts.append(width_cov)
            width_df = df.loc[has_width].copy()
            width_df["_wt"] = width_df["width_m"] * width_df["length_m"]
            width_g = width_df.groupby("hex_id")
            avg_width = (width_g["_wt"].sum() / width_g["length_m"].sum()).rename("avg_road_width_m")
            max_width = width_g["width_m"].max().rename("max_road_width_m")
            parts.extend([avg_width, max_width])
        else:
            has_width_any = False

    # --- Access restriction fractions ---
    for ar_col in ("access_denied_foot", "access_denied_bicycle", "access_denied_hgv"):
        if ar_col in df.columns:
            flag = df[ar_col].astype(float).fillna(0)
            weighted = (flag * df["length_m"]).groupby(df["hex_id"]).sum()
            frac = (weighted / total_length).rename(f"pct_{ar_col}_length")
            parts.append(frac)
    if "has_access_restriction" in df.columns:
        flag = df["has_access_restriction"].astype(float).fillna(0)
        weighted = (flag * df["length_m"]).groupby(df["hex_id"]).sum()
        frac = (weighted / total_length).rename("has_access_restriction_pct")
        parts.append(frac)

    # --- Subclass breakdown (global registry) ---
    if "subclass" in df.columns:
        has_subclass = df["subclass"].notna()
        if bool(has_subclass.any()):
            registry_subclasses = set(GLOBAL_FEATURE_REGISTRY["road_subclasses"])
            sub_df = df.loc[has_subclass].copy()
            sub_df["_subclass"] = sub_df["subclass"].where(
                sub_df["subclass"].isin(registry_subclasses), "other"
            )
            sub_agg = sub_df.groupby(["hex_id", "_subclass"])["length_m"].sum().reset_index()
            sub_pivot = sub_agg.pivot_table(
                index="hex_id", columns="_subclass", values="length_m",
                aggfunc="sum", fill_value=0,
            )
            sub_pivot.columns = [f"road_length_subclass_{c}_m" for c in sub_pivot.columns]
            for sc in GLOBAL_FEATURE_REGISTRY["road_subclasses"]:
                col = f"road_length_subclass_{sc}_m"
                if col not in sub_pivot.columns:
                    sub_pivot[col] = 0
            if "road_length_subclass_other_m" not in sub_pivot.columns:
                sub_pivot["road_length_subclass_other_m"] = 0
            parts.append(sub_pivot)

    # --- Named road stats ---
    if "road_name" in df.columns:
        has_name = df["road_name"].notna()
        if bool(has_name.any()):
            named_len = df.loc[has_name].groupby("hex_id")["length_m"].sum()
            named_pct = (named_len / total_length).rename("named_road_pct")
            parts.append(named_pct)
            unique_names = df.loc[has_name].groupby("hex_id")["road_name"].nunique().rename("unique_road_names")
            parts.append(unique_names)

    # --- Route features ---
    if "route_count" in df.columns:
        route_total = df.groupby("hex_id")["route_count"].sum().rename("route_count_total")
        parts.append(route_total)
    if "has_national_route" in df.columns:
        nat_flag = df["has_national_route"].astype(float).fillna(0)
        has_nat = nat_flag.groupby(df["hex_id"]).max().rename("has_national_route")
        parts.append(has_nat)

    result = pd.concat(parts, axis=1).fillna(0).reset_index()
    logger.info("Road features: %d hexes, %d columns", len(result), len(result.columns))
    return result


def _aggregate_pois_to_hexes(
    pois_gdf: gpd.GeoDataFrame,
    h3_resolution: int,
) -> pd.DataFrame:
    """Comprehensive POI aggregation: total count, per-category counts, diversity."""
    import h3

    if pois_gdf.empty:
        return pd.DataFrame(columns=["hex_id", "poi_count_total"])

    lats = pois_gdf.geometry.y.values
    lons = pois_gdf.geometry.x.values
    assign = np.vectorize(h3.latlng_to_cell)
    hex_ids = assign(lats, lons, h3_resolution)

    df = pd.DataFrame({
        "hex_id": hex_ids,
        "category": pois_gdf["category"].values if "category" in pois_gdf.columns else "unknown",
    })
    if "categories_alt" in pois_gdf.columns:
        df["categories_alt"] = pois_gdf["categories_alt"].values

    # --- Total count ---
    poi_total = df.groupby("hex_id").size().rename("poi_count_total")

    # --- Category diversity ---
    poi_diversity = df.groupby("hex_id")["category"].nunique().rename("poi_category_diversity")

    # --- Per-category counts (global registry) ---
    registry_cats = set(GLOBAL_FEATURE_REGISTRY["poi_categories"])
    df["cat_col"] = df["category"].where(df["category"].isin(registry_cats), "other")
    cat_counts = df.groupby(["hex_id", "cat_col"]).size().unstack(fill_value=0)
    cat_counts.columns = [f"poi_count_{c}" for c in cat_counts.columns]
    for cat in GLOBAL_FEATURE_REGISTRY["poi_categories"]:
        col = f"poi_count_{cat}"
        if col not in cat_counts.columns:
            cat_counts[col] = 0
    if "poi_count_other" not in cat_counts.columns:
        cat_counts["poi_count_other"] = 0

    parts = [poi_total, poi_diversity, cat_counts]

    # --- Alt category diversity ---
    if "categories_alt" in df.columns:
        has_alt = df["categories_alt"].notna()
        if bool(has_alt.any()):
            alt_df = df.loc[has_alt, ["hex_id", "categories_alt"]].copy()
            alt_df["_alt_cats"] = alt_df["categories_alt"].str.split("|")
            alt_exploded = alt_df.explode("_alt_cats")
            alt_diversity = (
                alt_exploded.groupby("hex_id")["_alt_cats"]
                .nunique()
                .rename("poi_alt_category_diversity")
            )
            parts.append(alt_diversity)

        alt_pct = (
            df.groupby("hex_id")["categories_alt"]
            .apply(lambda s: s.notna().mean())
            .rename("poi_has_alt_category_pct")
        )
        parts.append(alt_pct)

    result = pd.concat(parts, axis=1).fillna(0).reset_index()
    logger.info("POI features: %d hexes, %d columns", len(result), len(result.columns))
    return result


def _aggregate_buildings_to_hexes(
    buildings_gdf: gpd.GeoDataFrame,
    h3_resolution: int,
    projected_crs: str | None = None,
) -> pd.DataFrame:
    """Comprehensive building aggregation: counts/areas per type, avg height."""
    import h3

    if buildings_gdf.empty:
        return pd.DataFrame(columns=["hex_id", "building_count", "building_total_area_m2"])

    # Assign buildings to hexes via centroid
    if projected_crs:
        centroids = buildings_gdf.to_crs(projected_crs).geometry.centroid.to_crs("EPSG:4326")
    else:
        centroids = buildings_gdf.geometry.centroid
    lats = centroids.y.values
    lons = centroids.x.values
    assign = np.vectorize(h3.latlng_to_cell)
    hex_ids = assign(lats, lons, h3_resolution)

    df = pd.DataFrame({"hex_id": hex_ids})
    df["area_m2"] = buildings_gdf["area_m2"].values if "area_m2" in buildings_gdf.columns else np.nan
    df["building_class"] = (
        buildings_gdf["building_class"].values
        if "building_class" in buildings_gdf.columns
        else "unknown"
    )
    if "height" in buildings_gdf.columns:
        df["height"] = buildings_gdf["height"].values

    # --- Total count and area ---
    building_count = df.groupby("hex_id").size().rename("building_count")
    total_area = df.groupby("hex_id")["area_m2"].sum().rename("building_total_area_m2")

    # --- Per-type counts and areas (global registry) ---
    df["type_col"] = df["building_class"].fillna("unknown")
    registry_types = set(GLOBAL_FEATURE_REGISTRY["building_classes"])
    df["type_col"] = df["type_col"].where(df["type_col"].isin(registry_types), "other")

    type_agg = df.groupby(["hex_id", "type_col"]).agg(
        count=("area_m2", "size"),
        area=("area_m2", "sum"),
    ).reset_index()

    count_pivot = type_agg.pivot_table(
        index="hex_id", columns="type_col", values="count", fill_value=0
    )
    count_pivot.columns = [f"building_count_{c}" for c in count_pivot.columns]
    for cls in GLOBAL_FEATURE_REGISTRY["building_classes"]:
        col = f"building_count_{cls}"
        if col not in count_pivot.columns:
            count_pivot[col] = 0
    if "building_count_other" not in count_pivot.columns:
        count_pivot["building_count_other"] = 0

    area_pivot = type_agg.pivot_table(
        index="hex_id", columns="type_col", values="area", fill_value=0
    )
    area_pivot.columns = [f"building_area_{c}_m2" for c in area_pivot.columns]
    for cls in GLOBAL_FEATURE_REGISTRY["building_classes"]:
        col = f"building_area_{cls}_m2"
        if col not in area_pivot.columns:
            area_pivot[col] = 0
    if "building_area_other_m2" not in area_pivot.columns:
        area_pivot["building_area_other_m2"] = 0

    parts = [building_count, total_area, count_pivot, area_pivot]

    # --- Avg height ---
    if "height" in df.columns and bool(df["height"].notna().any()):
        avg_height = df.groupby("hex_id")["height"].mean().rename("avg_building_height_m")
        parts.append(avg_height)

    result = pd.concat(parts, axis=1).fillna(0).reset_index()
    logger.info("Building features: %d hexes, %d columns", len(result), len(result.columns))
    return result


def _aggregate_landuse_to_hexes(
    landuse_gdf: gpd.GeoDataFrame,
    hex_gdf: gpd.GeoDataFrame,
    projected_crs: str,
) -> pd.DataFrame:
    """Comprehensive landuse aggregation: per-type areas, green/built fractions."""
    if landuse_gdf.empty or hex_gdf.empty:
        return pd.DataFrame(columns=["hex_id", "landuse_total_area_m2"])

    # Keep land_type and land_class through intersection
    keep_cols = ["geometry", "land_type"]
    if "land_class" in landuse_gdf.columns:
        keep_cols.append("land_class")

    lu_proj = landuse_gdf[keep_cols].to_crs(projected_crs)
    hexes_proj = hex_gdf[["hex_id", "geometry"]].to_crs(projected_crs)

    df = gpd.overlay(lu_proj, hexes_proj, how="intersection", keep_geom_type=False)
    if df.empty:
        return pd.DataFrame(columns=["hex_id", "landuse_total_area_m2"])

    df["area_m2"] = df.geometry.area

    # Use land_class for detailed type if available, fall back to land_type
    type_col_name = "land_class" if "land_class" in df.columns else "land_type"
    df["_type"] = df[type_col_name].fillna(df["land_type"]).fillna("other")

    # Map to global registry (unknown classes → "other")
    registry_classes = set(GLOBAL_FEATURE_REGISTRY["landuse_classes"])
    df["_type"] = df["_type"].where(df["_type"].isin(registry_classes), "other")

    # --- Per landuse type areas (global registry) ---
    type_agg = df.groupby(["hex_id", "_type"])["area_m2"].sum().reset_index()
    area_pivot = type_agg.pivot_table(
        index="hex_id", columns="_type", values="area_m2",
        aggfunc="sum", fill_value=0,
    )
    area_pivot.columns = [f"landuse_area_{c}_m2" for c in area_pivot.columns]
    for cls in GLOBAL_FEATURE_REGISTRY["landuse_classes"]:
        col = f"landuse_area_{cls}_m2"
        if col not in area_pivot.columns:
            area_pivot[col] = 0
    if "landuse_area_other_m2" not in area_pivot.columns:
        area_pivot["landuse_area_other_m2"] = 0

    # --- Total area ---
    total_area = df.groupby("hex_id")["area_m2"].sum().rename("landuse_total_area_m2")

    # --- Green / built fractions ---
    df["_is_green"] = df["_type"].isin(_GREEN_TYPES)
    df["_is_built"] = df["_type"].isin(_BUILT_TYPES)

    green_area = df[df["_is_green"]].groupby("hex_id")["area_m2"].sum()
    built_area = df[df["_is_built"]].groupby("hex_id")["area_m2"].sum()

    green_frac = (green_area / total_area).rename("total_green_fraction").fillna(0).clip(0, 1)
    built_frac = (built_area / total_area).rename("total_built_fraction").fillna(0).clip(0, 1)

    result = pd.concat([total_area, area_pivot, green_frac, built_frac], axis=1).fillna(0).reset_index()
    logger.info("Landuse features: %d hexes, %d columns", len(result), len(result.columns))
    return result


def _aggregate_addresses_to_hexes(
    addresses_gdf: gpd.GeoDataFrame,
    h3_resolution: int,
) -> pd.DataFrame:
    """Aggregate addresses per hex: total count, postcode/unit coverage, street diversity."""
    import h3

    if addresses_gdf.empty:
        return pd.DataFrame(columns=["hex_id", "address_count_total"])

    lats = addresses_gdf.geometry.y.values
    lons = addresses_gdf.geometry.x.values
    assign = np.vectorize(h3.latlng_to_cell)
    hex_ids = assign(lats, lons, h3_resolution)

    df = pd.DataFrame({"hex_id": hex_ids})
    for col in ("postcode", "unit", "street"):
        if col in addresses_gdf.columns:
            df[col] = addresses_gdf[col].values
        else:
            df[col] = None

    address_total = df.groupby("hex_id").size().rename("address_count_total")
    postcode_pct = df.groupby("hex_id")["postcode"].apply(lambda s: s.notna().mean()).rename("address_has_postcode_pct")
    unit_pct = df.groupby("hex_id")["unit"].apply(lambda s: s.notna().mean()).rename("address_has_unit_pct")
    unique_streets = df.groupby("hex_id")["street"].nunique().rename("address_unique_streets")

    result = pd.concat([address_total, postcode_pct, unit_pct, unique_streets], axis=1).fillna(0).reset_index()
    logger.info("Address features: %d hexes, %d columns", len(result), len(result.columns))
    return result


def _aggregate_infrastructure_to_hexes(
    infra_gdf: gpd.GeoDataFrame,
    h3_resolution: int,
) -> pd.DataFrame:
    """Aggregate infrastructure per hex: total count, per-class counts, diversity."""
    import h3

    if infra_gdf.empty:
        return pd.DataFrame(columns=["hex_id", "infra_count_total"])

    # Use centroid for all geometry types
    centroids = infra_gdf.geometry.centroid
    lats = centroids.y.values
    lons = centroids.x.values
    assign = np.vectorize(h3.latlng_to_cell)
    hex_ids = assign(lats, lons, h3_resolution)

    df = pd.DataFrame({
        "hex_id": hex_ids,
        "infra_class": infra_gdf["infra_class"].values if "infra_class" in infra_gdf.columns else "unknown",
    })

    infra_total = df.groupby("hex_id").size().rename("infra_count_total")
    infra_diversity = df.groupby("hex_id")["infra_class"].nunique().rename("infra_class_diversity")

    # Per-class counts (global registry)
    registry_classes = set(GLOBAL_FEATURE_REGISTRY["infrastructure_classes"])
    df["cls_col"] = df["infra_class"].where(df["infra_class"].isin(registry_classes), "other")
    cls_counts = df.groupby(["hex_id", "cls_col"]).size().unstack(fill_value=0)
    cls_counts.columns = [f"infra_count_{c}" for c in cls_counts.columns]
    for cls in GLOBAL_FEATURE_REGISTRY["infrastructure_classes"]:
        col = f"infra_count_{cls}"
        if col not in cls_counts.columns:
            cls_counts[col] = 0
    if "infra_count_other" not in cls_counts.columns:
        cls_counts["infra_count_other"] = 0

    result = pd.concat([infra_total, infra_diversity, cls_counts], axis=1).fillna(0).reset_index()
    logger.info("Infrastructure features: %d hexes, %d columns", len(result), len(result.columns))
    return result


def _aggregate_land_cover_to_hexes(
    landcover_gdf: gpd.GeoDataFrame,
    hex_gdf: gpd.GeoDataFrame,
    projected_crs: str,
) -> pd.DataFrame:
    """Aggregate land cover per hex: per-subtype areas, green/urban fractions."""
    if landcover_gdf.empty or hex_gdf.empty:
        return pd.DataFrame(columns=["hex_id", "landcover_total_area_m2"])

    lc_proj = landcover_gdf[["geometry", "landcover_subtype"]].to_crs(projected_crs)
    hexes_proj = hex_gdf[["hex_id", "geometry"]].to_crs(projected_crs)

    df = gpd.overlay(lc_proj, hexes_proj, how="intersection", keep_geom_type=False)
    if df.empty:
        return pd.DataFrame(columns=["hex_id", "landcover_total_area_m2"])

    df["area_m2"] = df.geometry.area

    # Per-subtype areas (global registry — all 10 subtypes)
    registry_subtypes = set(GLOBAL_FEATURE_REGISTRY["land_cover_subtypes"])
    df["_subtype"] = df["landcover_subtype"].fillna("unknown")
    df["_subtype"] = df["_subtype"].where(df["_subtype"].isin(registry_subtypes), "other")

    type_agg = df.groupby(["hex_id", "_subtype"])["area_m2"].sum().reset_index()
    area_pivot = type_agg.pivot_table(
        index="hex_id", columns="_subtype", values="area_m2",
        aggfunc="sum", fill_value=0,
    )
    area_pivot.columns = [f"landcover_area_{c}_m2" for c in area_pivot.columns]
    for st in GLOBAL_FEATURE_REGISTRY["land_cover_subtypes"]:
        col = f"landcover_area_{st}_m2"
        if col not in area_pivot.columns:
            area_pivot[col] = 0
    if "landcover_area_other_m2" not in area_pivot.columns:
        area_pivot["landcover_area_other_m2"] = 0

    total_area = df.groupby("hex_id")["area_m2"].sum().rename("landcover_total_area_m2")

    # Green and urban fractions
    _green_lc = {"forest", "grass", "shrub", "mangrove", "moss", "wetland"}
    df["_is_green"] = df["_subtype"].isin(_green_lc)
    green_area = df[df["_is_green"]].groupby("hex_id")["area_m2"].sum()
    green_frac = (green_area / total_area).rename("landcover_green_fraction").fillna(0).clip(0, 1)

    df["_is_urban"] = df["_subtype"] == "urban"
    urban_area = df[df["_is_urban"]].groupby("hex_id")["area_m2"].sum()
    urban_frac = (urban_area / total_area).rename("landcover_urban_fraction").fillna(0).clip(0, 1)

    result = pd.concat([total_area, area_pivot, green_frac, urban_frac], axis=1).fillna(0).reset_index()
    logger.info("Land cover features: %d hexes, %d columns", len(result), len(result.columns))
    return result


def _aggregate_connectors_to_hexes(
    connectors_gdf: gpd.GeoDataFrame,
    h3_resolution: int,
) -> pd.DataFrame:
    """Aggregate connectors (intersections) per hex: count and density."""
    import h3

    if connectors_gdf.empty:
        return pd.DataFrame(columns=["hex_id", "connector_count_total"])

    lats = connectors_gdf.geometry.y.values
    lons = connectors_gdf.geometry.x.values
    assign = np.vectorize(h3.latlng_to_cell)
    hex_ids = assign(lats, lons, h3_resolution)

    df = pd.DataFrame({"hex_id": hex_ids})
    connector_total = df.groupby("hex_id").size().rename("connector_count_total")

    # Density (per km²) — use H3 edge length to estimate hex area
    hex_edge_m = H3_EDGE_LENGTH_M.get(h3_resolution, 174)
    hex_area_km2 = (2.598 * (hex_edge_m / 1000) ** 2)  # regular hex area ≈ 2.598 * s²
    connector_density = (connector_total / hex_area_km2).rename("connector_density_per_km2")

    result = pd.concat([connector_total, connector_density], axis=1).fillna(0).reset_index()
    logger.info("Connector features: %d hexes, %d columns", len(result), len(result.columns))
    return result


def _aggregate_building_parts_to_hexes(
    parts_gdf: gpd.GeoDataFrame,
    h3_resolution: int,
    projected_crs: str | None = None,
) -> pd.DataFrame:
    """Aggregate building parts per hex: count, area, height, floors."""
    import h3

    if parts_gdf.empty:
        return pd.DataFrame(columns=["hex_id", "building_part_count"])

    if projected_crs:
        centroids = parts_gdf.to_crs(projected_crs).geometry.centroid.to_crs("EPSG:4326")
    else:
        centroids = parts_gdf.geometry.centroid
    lats = centroids.y.values
    lons = centroids.x.values
    assign = np.vectorize(h3.latlng_to_cell)
    hex_ids = assign(lats, lons, h3_resolution)

    df = pd.DataFrame({"hex_id": hex_ids})
    df["area_m2"] = parts_gdf["area_m2"].values if "area_m2" in parts_gdf.columns else np.nan
    for col in ("height", "num_floors", "is_underground"):
        if col in parts_gdf.columns:
            df[col] = parts_gdf[col].values
        else:
            df[col] = np.nan if col != "is_underground" else False

    part_count = df.groupby("hex_id").size().rename("building_part_count")
    total_area = df.groupby("hex_id")["area_m2"].sum().rename("building_part_total_area_m2")

    parts = [part_count, total_area]

    if "height" in df.columns and bool(df["height"].notna().any()):
        avg_height = df.groupby("hex_id")["height"].mean().rename("building_part_avg_height_m")
        parts.append(avg_height)

    if "num_floors" in df.columns and bool(df["num_floors"].notna().any()):
        avg_floors = df.groupby("hex_id")["num_floors"].mean().rename("building_part_avg_num_floors")
        parts.append(avg_floors)

    if "is_underground" in df.columns:
        underground = df[df["is_underground"] == True].groupby("hex_id").size().rename("building_part_underground_count")  # noqa: E712
        parts.append(underground)

    result = pd.concat(parts, axis=1).fillna(0).reset_index()
    logger.info("Building part features: %d hexes, %d columns", len(result), len(result.columns))
    return result


def _aggregate_divisions_to_hexes(
    division_data: dict[str, gpd.GeoDataFrame],
    hex_gdf: gpd.GeoDataFrame,
    projected_crs: str,
) -> pd.DataFrame:
    """Aggregate division features per hex from all 3 division types."""
    parts: list[pd.Series] = []
    import h3

    # Division points — count and admin levels
    if "division" in division_data and not division_data["division"].empty:
        div_gdf = division_data["division"]
        lats = div_gdf.geometry.centroid.y.values
        lons = div_gdf.geometry.centroid.x.values
        hex_edge = H3_EDGE_LENGTH_M.get(9, 174)  # default
        # Determine resolution from hex_gdf
        if not hex_gdf.empty:
            sample_hex = hex_gdf["hex_id"].iloc[0]
            res = h3.get_resolution(sample_hex)
        else:
            res = 9
        assign = np.vectorize(h3.latlng_to_cell)
        hex_ids = assign(lats, lons, res)

        df = pd.DataFrame({
            "hex_id": hex_ids,
            "admin_level": div_gdf["admin_level"].values if "admin_level" in div_gdf.columns else np.nan,
        })
        div_count = df.groupby("hex_id").size().rename("division_count")
        parts.append(div_count)

        if bool(df["admin_level"].notna().any()):
            min_level = df.groupby("hex_id")["admin_level"].min().rename("division_min_admin_level")
            max_level = df.groupby("hex_id")["admin_level"].max().rename("division_max_admin_level")
            parts.extend([min_level, max_level])

    # Division areas — count overlapping
    if "division_area" in division_data and not division_data["division_area"].empty:
        da_gdf = division_data["division_area"]
        da_proj = da_gdf[["geometry"]].to_crs(projected_crs)
        hexes_proj = hex_gdf[["hex_id", "geometry"]].to_crs(projected_crs)
        try:
            joined = gpd.sjoin(hexes_proj, da_proj, how="inner", predicate="intersects")
            area_count = joined.groupby("hex_id").size().rename("division_area_count")
            parts.append(area_count)
        except Exception as exc:
            logger.warning("Division area spatial join failed: %s", exc)

    # Division boundaries — total line length per hex
    if "division_boundary" in division_data and not division_data["division_boundary"].empty:
        db_gdf = division_data["division_boundary"]
        db_proj = db_gdf[["geometry"]].to_crs(projected_crs)
        hexes_proj = hex_gdf[["hex_id", "geometry"]].to_crs(projected_crs)
        try:
            overlay = gpd.overlay(db_proj, hexes_proj, how="intersection", keep_geom_type=False)
            if not overlay.empty:
                overlay["length_m"] = overlay.geometry.length
                boundary_len = overlay.groupby("hex_id")["length_m"].sum().rename("division_boundary_length_m")
                parts.append(boundary_len)
        except Exception as exc:
            logger.warning("Division boundary overlay failed: %s", exc)

    if not parts:
        return pd.DataFrame(columns=["hex_id", "division_count"])

    result = pd.concat(parts, axis=1).fillna(0).reset_index()
    logger.info("Division features: %d hexes, %d columns", len(result), len(result.columns))
    return result


def _aggregate_bathymetry_to_hexes(
    bathymetry_gdf: gpd.GeoDataFrame,
    hex_gdf: gpd.GeoDataFrame,
    projected_crs: str,
) -> pd.DataFrame:
    """Aggregate bathymetry per hex: area and fraction."""
    if bathymetry_gdf.empty or hex_gdf.empty:
        return pd.DataFrame(columns=["hex_id", "bathymetry_area_m2"])

    # Filter out geometries with NaN/Inf coordinates that crash make_valid
    valid_mask = bathymetry_gdf.geometry.apply(
        lambda g: g is not None and g.is_valid or (g is not None and not any(
            c != c or abs(c) == float("inf")  # NaN or Inf check
            for coord in (g.exterior.coords if hasattr(g, "exterior") else [])
            for c in coord
        ))
    )
    bath_clean = bathymetry_gdf[valid_mask].copy()
    if bath_clean.empty:
        return pd.DataFrame(columns=["hex_id", "bathymetry_area_m2"])

    # Apply make_valid before overlay to handle any remaining invalid geometries
    bath_clean["geometry"] = bath_clean.geometry.apply(
        lambda g: make_valid(g) if g is not None and not g.is_valid else g
    )
    bath_clean = bath_clean[bath_clean.geometry.notna() & ~bath_clean.geometry.is_empty].copy()
    if bath_clean.empty:
        return pd.DataFrame(columns=["hex_id", "bathymetry_area_m2"])

    bath_proj = bath_clean[["geometry"]].to_crs(projected_crs)
    hexes_proj = hex_gdf[["hex_id", "geometry"]].to_crs(projected_crs)

    try:
        df = gpd.overlay(bath_proj, hexes_proj, how="intersection", keep_geom_type=False)
    except Exception as exc:
        logger.warning("Bathymetry overlay failed: %s — returning empty", exc)
        return pd.DataFrame(columns=["hex_id", "bathymetry_area_m2"])
    if df.empty:
        return pd.DataFrame(columns=["hex_id", "bathymetry_area_m2"])

    df["area_m2"] = df.geometry.area

    bath_area = df.groupby("hex_id")["area_m2"].sum().rename("bathymetry_area_m2")

    # Compute fraction using hex cell areas
    hex_areas = hexes_proj.copy()
    hex_areas["cell_area_m2"] = hex_areas.geometry.area
    hex_areas = hex_areas.set_index("hex_id")["cell_area_m2"]
    bath_frac = (bath_area / hex_areas).rename("bathymetry_fraction").fillna(0).clip(0, 1)

    result = pd.concat([bath_area, bath_frac], axis=1).fillna(0).reset_index()
    logger.info("Bathymetry features: %d hexes, %d columns", len(result), len(result.columns))
    return result


def _apply_ml_transforms(df: pd.DataFrame) -> pd.DataFrame:
    """Apply ML transforms to raw hex features for foundation model training.

    Transforms:
    - log1p for right-skewed count/area/length features
    - Binary indicators for zero-inflated percentage features
    """
    result = df.copy()

    # --- log1p transform for skewed features ---
    # Identify columns by pattern for automatic log1p
    log1p_patterns = [
        "poi_count_",        # all per-category POI counts
        "road_length_",      # all per-class road lengths + subclass lengths
        "building_count_",   # all per-type building counts
        "building_area_",    # all per-type building areas
        "landuse_area_",     # all per-type landuse areas
        "infra_count_",      # all per-class infrastructure counts
        "landcover_area_",   # all per-subtype land cover areas
        "building_part_",    # building part counts/areas
        "road_surface_length_",  # all per-surface-type road lengths
    ]
    # Explicit columns that also need log1p
    log1p_explicit = [
        "poi_count_total", "poi_category_diversity", "poi_alt_category_diversity",
        "total_road_length_m", "building_total_area_m2", "landuse_total_area_m2",
        "address_count_total", "address_unique_streets",
        "infra_count_total", "infra_class_diversity",
        "landcover_total_area_m2",
        "connector_count_total", "connector_density_per_km2",
        "building_part_count", "building_part_total_area_m2",
        "division_count", "division_area_count", "division_boundary_length_m",
        "bathymetry_area_m2",
        "unique_road_names", "route_count_total",
    ]

    log1p_cols = set()
    for col in result.columns:
        if any(col.startswith(p) for p in log1p_patterns):
            log1p_cols.add(col)
    for col in log1p_explicit:
        if col in result.columns:
            log1p_cols.add(col)

    for col in sorted(log1p_cols):
        result[f"log1p_{col}"] = np.log1p(result[col].astype(float))

    # --- Binary indicators for zero-inflated percentage features ---
    binary_map = {
        "pct_is_bridge_length": "has_bridge",
        "pct_is_tunnel_length": "has_tunnel",
        "pct_is_link_length": "has_link",
        "pct_is_under_construction_length": "has_under_construction",
        "has_access_restriction_pct": "has_access_restrictions",
        "pct_access_denied_foot_length": "has_foot_restriction",
        "pct_access_denied_bicycle_length": "has_bicycle_restriction",
        "pct_access_denied_hgv_length": "has_hgv_restriction",
    }
    for src, dst in binary_map.items():
        if src in result.columns:
            result[dst] = (result[src] > 0).astype(int)

    return result


def aggregate_osm_to_hexes(
    hex_gdf: gpd.GeoDataFrame,
    osm_paths: dict[str, Path],
    out_dir: Path,
    projected_crs: str,
    h3_resolution: int,
    resume: bool,
) -> Path:
    """Aggregate all available OSM layers to H3 hex level and save as parquet.

    Saves two files:
    - ``hex_features_raw.parquet`` — all features before ML transforms
    - ``hex_features.parquet`` — ML-ready with log1p + binary transforms

    Returns the path to ``hex_features.parquet``.
    """
    res_tag = f"res{h3_resolution:02d}"
    cache_path = out_dir / f"hex_features_{res_tag}.parquet"
    if resume and cache_path.exists():
        # Validate cached file has a reasonable number of columns.
        # Stale caches from earlier code versions may have fewer columns.
        try:
            import pyarrow.parquet as pq
            cached_cols = len(pq.read_schema(cache_path).names)
            # A valid hex features file should have at least ~50 columns
            # (hex_id + geometry + cell_area + road/poi/building/landuse features + ML transforms)
            if cached_cols < 50:
                logger.warning(
                    "Hex features cache STALE: %s has only %d columns (expected 50+), regenerating",
                    cache_path.name, cached_cols,
                )
            else:
                logger.info("Hex features cache hit: %s (%d cols)", cache_path, cached_cols)
                return cache_path
        except Exception:
            logger.warning("Could not validate cache %s, regenerating", cache_path.name)

    logger.info("Aggregating OSM layers to H3 hexes (resolution=%d) ...", h3_resolution)

    result = hex_gdf[["hex_id", "geometry"]].copy()

    # Compute cell areas in projected CRS
    result_proj = result.to_crs(projected_crs)
    result["cell_area_m2"] = result_proj.geometry.area

    if "roads" in osm_paths and osm_paths["roads"].exists():
        roads_gdf = gpd.read_parquet(osm_paths["roads"])
        road_agg = _aggregate_roads_to_hexes(roads_gdf, hex_gdf, projected_crs)
        result = result.merge(road_agg, on="hex_id", how="left")
        logger.info("Road aggregation: %d hexes with road data", len(road_agg))

    if "pois" in osm_paths and osm_paths["pois"].exists():
        pois_gdf = gpd.read_parquet(osm_paths["pois"])
        poi_agg = _aggregate_pois_to_hexes(pois_gdf, h3_resolution)
        result = result.merge(poi_agg, on="hex_id", how="left")
        logger.info("POI aggregation: %d hexes with POI data", len(poi_agg))

    if "buildings" in osm_paths and osm_paths["buildings"].exists():
        buildings_gdf = gpd.read_parquet(osm_paths["buildings"])
        building_agg = _aggregate_buildings_to_hexes(buildings_gdf, h3_resolution, projected_crs)
        result = result.merge(building_agg, on="hex_id", how="left")
        logger.info("Building aggregation: %d hexes with building data", len(building_agg))

    if "landuse" in osm_paths and osm_paths["landuse"].exists():
        landuse_gdf = gpd.read_parquet(osm_paths["landuse"])
        lu_agg = _aggregate_landuse_to_hexes(landuse_gdf, hex_gdf, projected_crs)
        result = result.merge(lu_agg, on="hex_id", how="left")
        logger.info("Landuse aggregation: %d hexes with landuse data", len(lu_agg))

    if "addresses" in osm_paths and osm_paths["addresses"].exists():
        addr_gdf = gpd.read_parquet(osm_paths["addresses"])
        addr_agg = _aggregate_addresses_to_hexes(addr_gdf, h3_resolution)
        result = result.merge(addr_agg, on="hex_id", how="left")
        logger.info("Address aggregation: %d hexes with address data", len(addr_agg))

    if "infrastructure" in osm_paths and osm_paths["infrastructure"].exists():
        infra_gdf = gpd.read_parquet(osm_paths["infrastructure"])
        infra_agg = _aggregate_infrastructure_to_hexes(infra_gdf, h3_resolution)
        result = result.merge(infra_agg, on="hex_id", how="left")
        logger.info("Infrastructure aggregation: %d hexes with infra data", len(infra_agg))

    if "land_cover" in osm_paths and osm_paths["land_cover"].exists():
        lc_gdf = gpd.read_parquet(osm_paths["land_cover"])
        lc_agg = _aggregate_land_cover_to_hexes(lc_gdf, hex_gdf, projected_crs)
        result = result.merge(lc_agg, on="hex_id", how="left")
        logger.info("Land cover aggregation: %d hexes with land cover data", len(lc_agg))

    if "connectors" in osm_paths and osm_paths["connectors"].exists():
        conn_gdf = gpd.read_parquet(osm_paths["connectors"])
        conn_agg = _aggregate_connectors_to_hexes(conn_gdf, h3_resolution)
        result = result.merge(conn_agg, on="hex_id", how="left")
        logger.info("Connector aggregation: %d hexes with connector data", len(conn_agg))

    if "building_parts" in osm_paths and osm_paths["building_parts"].exists():
        bp_gdf = gpd.read_parquet(osm_paths["building_parts"])
        bp_agg = _aggregate_building_parts_to_hexes(bp_gdf, h3_resolution, projected_crs)
        result = result.merge(bp_agg, on="hex_id", how="left")
        logger.info("Building parts aggregation: %d hexes with part data", len(bp_agg))

    if "divisions" in osm_paths and osm_paths["divisions"].exists():
        div_data: dict[str, gpd.GeoDataFrame] = {}
        div_dir = osm_paths["divisions"].parent
        for key, fname in [("division", "divisions.parquet"),
                           ("division_area", "division_areas.parquet"),
                           ("division_boundary", "division_boundaries.parquet")]:
            p = div_dir / fname
            if p.exists():
                gdf = gpd.read_parquet(p)
                if not gdf.empty:
                    div_data[key] = gdf
        if div_data:
            div_agg = _aggregate_divisions_to_hexes(div_data, hex_gdf, projected_crs)
            result = result.merge(div_agg, on="hex_id", how="left")
            logger.info("Division aggregation: %d hexes with division data", len(div_agg))

    if "bathymetry" in osm_paths and osm_paths["bathymetry"].exists():
        bath_gdf = gpd.read_parquet(osm_paths["bathymetry"])
        bath_agg = _aggregate_bathymetry_to_hexes(bath_gdf, hex_gdf, projected_crs)
        result = result.merge(bath_agg, on="hex_id", how="left")
        logger.info("Bathymetry aggregation: %d hexes with bathymetry data", len(bath_agg))

    result = result.fillna(0)

    # Save raw features (before transforms)
    raw_path = out_dir / f"hex_features_raw_{res_tag}.parquet"
    save_geodataframe(result, raw_path)
    logger.info("Saved raw hex features: %d hexes x %d cols -> %s",
                len(result), len(result.columns), raw_path)

    # Apply ML transforms and save
    result_ml = _apply_ml_transforms(result)
    save_geodataframe(result_ml, cache_path)
    logger.info("Saved ML hex features: %d hexes x %d cols -> %s",
                len(result_ml), len(result_ml.columns), cache_path)
    return cache_path


# ============================================================================
# Satellite Embeddings (GEE) — computePixels tile-based approach
# ============================================================================

def _sat_resolution_scale(resolution: int) -> float:
    """Return download scale (m) giving ~4 pixels across one H3 hex edge."""
    return max(10.0, H3_EDGE_LENGTH_M.get(resolution, 174) / 4.0)


def _sat_assign_pixels_to_hexes(
    H: int, W: int,
    minx: float, miny: float, maxx: float, maxy: float,
    h3_resolution: int,
) -> np.ndarray:
    """Return a flat (H*W,) array mapping every pixel centre to its H3 hex ID."""
    import h3
    lons = np.linspace(minx, maxx, W, endpoint=False) + (maxx - minx) / (2 * W)
    lats = np.linspace(maxy, miny, H, endpoint=False) - (maxy - miny) / (2 * H)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    assign = np.vectorize(h3.latlng_to_cell)
    return assign(lat_grid.ravel(), lon_grid.ravel(), h3_resolution)


def _sat_aggregate_tile(
    arr: np.ndarray,
    pixel_hex_ids: np.ndarray,
):
    """Aggregate one raster tile to per-hex sums using numpy bincount (no pandas).

    Returns (unique_hexes, band_sums, pixel_counts) or (None, None, None).
    band_sums shape: (n_unique, n_bands) float64
    """
    band_names = arr.dtype.names
    valid = ~np.isnan(arr[band_names[0]].ravel())
    if not valid.any():
        return None, None, None
    ids_valid = pixel_hex_ids[valid]
    unique_hexes, local_inv = np.unique(ids_valid, return_inverse=True)
    n_local = len(unique_hexes)
    band_sums = np.array([
        np.bincount(local_inv,
                    weights=arr[b].ravel()[valid].astype(np.float64),
                    minlength=n_local)
        for b in band_names
    ]).T  # (n_local, n_bands)
    pixel_counts = np.bincount(local_inv, minlength=n_local)
    return unique_hexes, band_sums, pixel_counts


def _sat_fetch_tile(image, tx0: float, ty1: float, scale_deg: float,
                    tw: int, th: int) -> np.ndarray:
    """Fetch one raster tile via ee.data.computePixels (high-volume API)."""
    import ee
    request = {
        "expression": image,
        "fileFormat": "NPY",
        "grid": {
            "dimensions": {"width": tw, "height": th},
            "affineTransform": {
                "scaleX":  scale_deg, "shearX": 0, "translateX": tx0,
                "shearY":  0, "scaleY": -scale_deg, "translateY": ty1,
            },
            "crsCode": "EPSG:4326",
        },
    }
    data = ee.data.computePixels(request)
    return np.load(io.BytesIO(data))


def _sat_checkpoint_path(cache_path: Path) -> Path:
    return cache_path.with_suffix(".checkpoint.pkl")


def _sat_save_checkpoint(ckpt_path: Path, sums: dict, counts: dict,
                         completed: set, total_tiles: int) -> None:
    tmp = ckpt_path.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        pickle.dump({"sums": sums, "counts": counts, "completed": completed,
                     "total_tiles": total_tiles}, f, protocol=4)
    tmp.replace(ckpt_path)


def _sat_load_checkpoint(ckpt_path: Path) -> tuple[dict, dict, set, int]:
    if not ckpt_path.exists():
        return {}, {}, set(), 0
    with open(ckpt_path, "rb") as f:
        data = pickle.load(f)
    return data["sums"], data["counts"], data["completed"], data.get("total_tiles", 0)


def fetch_satellite_hex_embeddings(
    boundary_geom: Polygon | MultiPolygon,
    out_dir: Path,
    ee_project: str,
    date_start: str = SAT_DATE_START_DEFAULT,
    date_end: str = SAT_DATE_END_DEFAULT,
    h3_resolution: int = H3_RESOLUTION_DEFAULT,
    resume: bool = True,
    scale: float | None = None,
    workers: int = SAT_MAX_WORKERS,
) -> Path:
    """Fetch Google Satellite Embedding V1 features aggregated to H3 hexes.

    Uses ee.data.computePixels (high-volume tile API) to download tiles in
    parallel, assigns every pixel to its H3 hex via numpy bincount aggregation,
    and saves the result as a Parquet file.  Progress is checkpointed every
    SAT_CHECKPOINT_EVERY tiles so interrupted runs can resume automatically.
    """
    import ee

    ensure_dir(out_dir)
    cache_path = out_dir / f"satellite_hex_embeddings_res{h3_resolution:02d}.parquet"

    if resume and cache_path.exists():
        logger.info("Satellite embeddings cache hit: %s", cache_path)
        return cache_path

    if scale is None:
        scale = _sat_resolution_scale(h3_resolution)
    hex_edge = H3_EDGE_LENGTH_M.get(h3_resolution, 174)
    if scale > hex_edge:
        logger.warning(
            "Scale %.0f m > H3 res-%d edge %.0f m — "
            "each pixel maps to a unique hex (pixel-centre sampling, not area average).",
            scale, h3_resolution, hex_edge,
        )

    logger.info(
        "Fetching satellite embeddings via computePixels "
        "(project=%s, dates=%s-%s, res=%d, scale=%.0f m, workers=%d) ...",
        ee_project, date_start, date_end, h3_resolution, scale, workers,
    )

    ee.Initialize(project=ee_project, opt_url=EE_HIGH_VOLUME_URL)

    if not hasattr(ee.data, "computePixels"):
        raise RuntimeError(
            "ee.data.computePixels not available — upgrade: pip install -U earthengine-api"
        )

    hull_coords = list(boundary_geom.convex_hull.exterior.coords)
    aoi = ee.Geometry.Polygon([[list(c) for c in hull_coords]])
    image = (
        ee.ImageCollection(SAT_COLLECTION)
        .filterDate(f"{date_start}-01-01", f"{date_end}-12-31")
        .filterBounds(aoi)
        .mean()
    )

    scale_deg = scale / 111_320.0
    minx, miny, maxx, maxy = boundary_geom.bounds
    full_W = max(1, math.ceil((maxx - minx) / scale_deg))
    full_H = max(1, math.ceil((maxy - miny) / scale_deg))

    all_bands = image.bandNames().getInfo()
    tile_px = max(32, int(math.sqrt(MAX_TILE_BYTES / (len(all_bands) * COMPUTE_PIXELS_BYTES_PER_VALUE))))

    n_tiles_x = math.ceil(full_W / tile_px)
    n_tiles_y = math.ceil(full_H / tile_px)
    total_tiles = n_tiles_x * n_tiles_y

    logger.info(
        "Grid %d×%d px | %d×%d tiles of %d px | %d total | %d bands | %d workers",
        full_W, full_H, n_tiles_x, n_tiles_y, tile_px, total_tiles, len(all_bands), workers,
    )

    # Load checkpoint if resuming
    ckpt_path = _sat_checkpoint_path(cache_path)
    sums, counts, completed_tiles, ckpt_total = _sat_load_checkpoint(ckpt_path)
    if completed_tiles:
        if ckpt_total != total_tiles:
            logger.warning(
                "Checkpoint tile count (%d) differs from current grid (%d) — ignoring.",
                ckpt_total, total_tiles,
            )
            sums, counts, completed_tiles = {}, {}, set()
        else:
            logger.info(
                "Resuming from checkpoint: %d/%d tiles already done",
                len(completed_tiles), total_tiles,
            )

    lock = threading.Lock()
    done_count = [len(completed_tiles)]
    log_every = max(1, total_tiles // 10)
    n_bands = len(all_bands)

    def process_tile(ix: int, iy: int) -> None:
        if (ix, iy) in completed_tiles:
            return
        tx0 = minx + ix * tile_px * scale_deg
        ty1 = maxy - iy * tile_px * scale_deg
        tw  = min(tile_px, full_W - ix * tile_px)
        th  = min(tile_px, full_H - iy * tile_px)
        if tw <= 0 or th <= 0:
            return
        tx1 = tx0 + tw * scale_deg
        ty0 = ty1 - th * scale_deg

        arr = _sat_fetch_tile(image, tx0, ty1, scale_deg, tw, th)
        tile_hex_ids = _sat_assign_pixels_to_hexes(th, tw, tx0, ty0, tx1, ty1, h3_resolution)
        unique_hexes, band_sums, pixel_counts = _sat_aggregate_tile(arr, tile_hex_ids)
        if unique_hexes is None:
            return

        with lock:
            for i, hid in enumerate(unique_hexes):
                if hid in sums:
                    sums[hid]   += band_sums[i]
                    counts[hid] += int(pixel_counts[i])
                else:
                    sums[hid]   = band_sums[i].copy()
                    counts[hid] = int(pixel_counts[i])
            completed_tiles.add((ix, iy))
            done_count[0] += 1
            n_done = done_count[0]
            if n_done % log_every == 0 or n_done == total_tiles:
                logger.info("  %d/%d tiles done", n_done, total_tiles)
            if n_done % SAT_CHECKPOINT_EVERY == 0:
                _sat_save_checkpoint(ckpt_path, sums, counts, completed_tiles, total_tiles)
                logger.info("  Checkpoint saved (%d/%d)", n_done, total_tiles)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(process_tile, ix, iy)
            for iy in range(n_tiles_y)
            for ix in range(n_tiles_x)
        ]
        for f in as_completed(futures):
            f.result()

    # Vectorised mean computation
    hex_ids = [hid for hid, c in counts.items() if c > 0]
    sums_mat   = np.array([sums[hid]   for hid in hex_ids])
    counts_vec = np.array([counts[hid] for hid in hex_ids], dtype=np.float64)
    means_mat  = sums_mat / counts_vec[:, None]

    df = pd.DataFrame(means_mat, columns=all_bands)
    df.insert(0, "hex_id", hex_ids)

    avg_px = counts_vec.sum() / max(len(hex_ids), 1)
    logger.info("Avg %.1f pixels/hex | %d unique hexes at res-%d", avg_px, len(df), h3_resolution)

    df.to_parquet(cache_path, engine="pyarrow", index=False)
    logger.info("Satellite embeddings saved: %d hexes, %d bands -> %s", len(df), len(all_bands), cache_path)

    if ckpt_path.exists():
        ckpt_path.unlink()

    return cache_path


def merge_osm_satellite(
    hex_features_path: Path,
    sat_path: Path,
    out_path: Path,
) -> Path:
    """Left-join hex OSM features with satellite embeddings on hex_id."""
    hex_gdf = gpd.read_parquet(hex_features_path)
    sat_df = pd.read_parquet(sat_path)

    n_hex = len(hex_gdf)
    merged = hex_gdf.merge(sat_df, on="hex_id", how="left")
    n_matched = merged["hex_id"].isin(sat_df["hex_id"]).sum()

    logger.info(
        "Merge: %d hex features + %d satellite rows -> %d matched / %d unmatched",
        n_hex, len(sat_df), n_matched, n_hex - n_matched,
    )

    save_geodataframe(merged, out_path)
    return out_path


# ============================================================================
# Multi-release download logic
# ============================================================================


def _release_already_done(out_dir: Path, layers: list[str]) -> bool:
    """Return True if *out_dir* already has extraction_metadata.json covering
    all requested layers."""
    meta_path = out_dir / "extraction_metadata.json"
    if not meta_path.exists():
        return False
    try:
        meta = load_json(meta_path)
        existing = set(meta.get("layers_extracted", []))
        return set(layers).issubset(existing)
    except Exception:
        return False


def _print_summary(results: dict[str, dict]) -> None:
    """Print a formatted summary table."""
    print(f"\n{'=' * 70}")
    print(f"{'Year':<6} {'Release Tag':<25} {'Status':<10} {'Details'}")
    print(f"{'-' * 70}")
    for year in sorted(results):
        r = results[year]
        tag = RELEASE_TAGS[year]
        status = r["status"]
        if status == "success":
            counts = r.get("row_counts", {})
            detail = ", ".join(f"{k}: {v:,}" for k, v in counts.items())
            hex_count = r.get("hex_count")
            if hex_count is not None:
                detail += f", hexes: {hex_count:,}"
        elif status == "skipped":
            detail = "already downloaded (resume)"
        else:
            detail = r.get("error_summary", "unknown error")
        print(f"{year:<6} {tag:<25} {status:<10} {detail}")
    print(f"{'=' * 70}\n")


def download_multi_release(
    city: str,
    relation_id: int,
    years: list[str],
    layers: list[str],
    resume: bool,
    boundary_geom: Polygon | MultiPolygon | None = None,
    projected_crs: str | None = None,
    hex_gdf: gpd.GeoDataFrame | None = None,
    h3_resolution: int = H3_RESOLUTION_DEFAULT,
    data_dir: Path = DATA_DIR,
) -> dict[str, dict]:
    """Download Overture feature data for *city* across multiple releases.

    If *boundary_geom* is provided the Overpass boundary fetch is skipped.
    If *hex_gdf* is provided OSM hex aggregation is performed for each release.
    """
    if boundary_geom is None:
        logger.info("Fetching boundary for %s (relation %d) ...", city, relation_id)
        boundary_gdf = fetch_city_boundary_overpass(relation_id)
        boundary_geom = boundary_gdf.geometry.iloc[0]
        centroid = boundary_geom.centroid
        projected_crs = utm_crs_from_lonlat(centroid.x, centroid.y)
        logger.info("Boundary OK — CRS=%s", projected_crs)

    base_dir = data_dir / city / "overture_releases"
    ensure_dir(base_dir)

    results: dict[str, dict] = {}

    for year in years:
        tag = RELEASE_TAGS[year]
        out_dir = base_dir / tag
        logger.info("[%s] Release %s -> %s", year, tag, out_dir)

        extraction_skipped = False
        if resume and _release_already_done(out_dir, layers):
            logger.info("[%s] Raw extraction skipped (already downloaded)", year)
            extraction_skipped = True
            results[year] = {"status": "skipped"}
        else:
            t0 = time.monotonic()
            try:
                paths = extract_all(
                    boundary_geom,
                    out_dir,
                    layers=layers,
                    release=tag,
                    projected_crs=projected_crs,
                )
                elapsed = time.monotonic() - t0

                meta_path = out_dir / "extraction_metadata.json"
                row_counts = {}
                if meta_path.exists():
                    meta = load_json(meta_path)
                    row_counts = meta.get("row_counts", {})

                results[year] = {
                    "status": "success",
                    "elapsed_s": round(elapsed, 1),
                    "layers": list(paths.keys()),
                    "row_counts": row_counts,
                }
                logger.info("[%s] Extraction done in %.1fs — %s", year, elapsed, row_counts)

            except Exception:
                elapsed = time.monotonic() - t0
                tb = traceback.format_exc()
                error_lines = [line for line in tb.strip().splitlines() if line.strip()]
                error_summary = error_lines[-1][:80] if error_lines else "unknown"
                results[year] = {
                    "status": "failed",
                    "elapsed_s": round(elapsed, 1),
                    "error_summary": error_summary,
                }
                logger.warning("[%s] FAILED (%.1fs): %s", year, elapsed, error_summary)
                logger.debug("[%s] Full traceback:\n%s", year, tb)
                continue  # skip hex aggregation on extraction failure

        # Hex aggregation — runs even if extraction was skipped (cached raw data)
        if hex_gdf is not None and results[year]["status"] != "failed":
            # Build osm_paths from whatever parquet files exist in out_dir
            osm_paths = {}
            for layer_name in layers:
                p = out_dir / f"{layer_name}.parquet"
                if p.exists():
                    osm_paths[layer_name] = p

            hex_path = aggregate_osm_to_hexes(
                hex_gdf=hex_gdf,
                osm_paths=osm_paths,
                out_dir=out_dir,
                projected_crs=projected_crs,
                h3_resolution=h3_resolution,
                resume=resume,
            )
            results[year]["hex_features_path"] = str(hex_path)
            results[year]["hex_count"] = _count_parquet_rows(hex_path)

    return results


# ============================================================================
# CLI
# ============================================================================


def _setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    )
    root.addHandler(console)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Overture Maps feature data across multiple release years."
    )
    parser.add_argument(
        "--city", default="sydney", help="City name (default: sydney)."
    )
    parser.add_argument(
        "--relation-id", type=int, default=5750005,
        help="OSM relation ID for boundary fetch (default: 5750005 = Sydney)."
    )
    parser.add_argument(
        "--releases", nargs="+", default=list(RELEASE_TAGS.keys()),
        choices=list(RELEASE_TAGS.keys()),
        help="Which release years to download (default: all).",
    )
    parser.add_argument(
        "--layers", nargs="+", default=ALL_LAYERS,
        choices=ALL_LAYERS,
        help="Which layers to extract (default: all).",
    )
    parser.add_argument(
        "--no-resume", action="store_true",
        help="Force re-download even if output exists.",
    )
    parser.add_argument(
        "--hex-agg", action="store_true",
        help="Aggregate OSM layers to H3 hex-level features after extraction.",
    )
    parser.add_argument(
        "--satellite", action="store_true",
        help="Fetch GEE satellite embeddings per hex (auto-enables --hex-agg).",
    )
    parser.add_argument(
        "--ee-project", default=None,
        help="GEE project ID (required if --satellite).",
    )
    parser.add_argument(
        "--sat-date-start", default=SAT_DATE_START_DEFAULT,
        help=f"Start year for satellite data (default: {SAT_DATE_START_DEFAULT}).",
    )
    parser.add_argument(
        "--sat-date-end", default=SAT_DATE_END_DEFAULT,
        help=f"End year for satellite data (default: {SAT_DATE_END_DEFAULT}).",
    )
    parser.add_argument(
        "--h3-resolution", type=int, default=H3_RESOLUTION_DEFAULT,
        help=f"H3 resolution (default: {H3_RESOLUTION_DEFAULT}).",
    )
    parser.add_argument(
        "--no-sat-cache", action="store_true",
        help="Force re-fetch satellite embeddings even if cached.",
    )
    parser.add_argument(
        "--data-dir", default=str(DATA_DIR),
        help=f"Base data directory for pipeline outputs (default: {DATA_DIR}).",
    )
    parser.add_argument(
        "--upload-s3", action="store_true",
        help="Upload outputs to S3 after pipeline completion.",
    )

    args = parser.parse_args()

    # Validate
    if args.satellite and not args.ee_project:
        parser.error("--ee-project is required when using --satellite")

    hex_agg = args.hex_agg or args.satellite  # satellite implies hex-agg

    # Use --data-dir as base for all output paths
    data_dir = Path(args.data_dir)

    _setup_logging()

    logger.info(
        "Multi-release download: city=%s, releases=%s, layers=%s, resume=%s, hex_agg=%s, satellite=%s",
        args.city, args.releases, args.layers, not args.no_resume, hex_agg, args.satellite,
    )

    # 1. Fetch boundary once
    logger.info("Fetching boundary for %s (relation %d) ...", args.city, args.relation_id)
    boundary_gdf = fetch_city_boundary_overpass(args.relation_id)
    boundary_geom = boundary_gdf.geometry.iloc[0]
    centroid = boundary_geom.centroid
    projected_crs = utm_crs_from_lonlat(centroid.x, centroid.y)
    logger.info("Boundary OK — CRS=%s", projected_crs)

    # 2. Generate hex grid once (if needed)
    hex_gdf = None
    if hex_agg:
        hex_gdf = _generate_h3_hex_grid(boundary_geom, args.h3_resolution)

    # 3. OSM download + optional hex agg per release
    results = download_multi_release(
        city=args.city,
        relation_id=args.relation_id,
        years=args.releases,
        layers=args.layers,
        resume=not args.no_resume,
        boundary_geom=boundary_geom,
        projected_crs=projected_crs,
        hex_gdf=hex_gdf,
        h3_resolution=args.h3_resolution,
        data_dir=data_dir,
    )

    # 4. Satellite embeddings (once per city, cached)
    sat_path = None
    if args.satellite:
        sat_out_dir = data_dir / args.city / "satellite"
        sat_path = fetch_satellite_hex_embeddings(
            boundary_geom=boundary_geom,
            out_dir=sat_out_dir,
            ee_project=args.ee_project,
            date_start=args.sat_date_start,
            date_end=args.sat_date_end,
            h3_resolution=args.h3_resolution,
            resume=not args.no_sat_cache,
        )

    # 5. Merge OSM hex features + satellite embeddings per release
    if sat_path:
        for year, r in results.items():
            print(year, r["status"], r.get("hex_features_path"))
            if (r["status"] in ["success", "skipped"] and r.get("hex_features_path")):
                tag = RELEASE_TAGS[year]
                res_tag = f"res{args.h3_resolution:02d}"
                out_path = data_dir / args.city / "overture_releases" / tag / f"combined_{res_tag}.parquet"
                merge_osm_satellite(Path(r["hex_features_path"]), sat_path, out_path)
                logger.info("[%s] Combined parquet saved -> %s", year, out_path)

    _print_summary(results)

    failed = sum(1 for r in results.values() if r["status"] == "failed")
    succeeded = sum(1 for r in results.values() if r["status"] == "success")
    skipped = sum(1 for r in results.values() if r["status"] == "skipped")
    print(f"Summary: {succeeded} succeeded, {skipped} skipped, {failed} failed")

    # 6. Upload to S3 (if requested)
    if args.upload_s3 and failed < len(results):
        try:
            from upload_to_s3 import upload_city_to_s3
        except ImportError:
            logger.error("Cannot import upload_to_s3 — make sure upload_to_s3.py is in the same directory")
            sys.exit(1)

        for year in args.releases:
            tag = RELEASE_TAGS[year]
            logger.info("[%s] Uploading to S3 ...", year)
            upload_city_to_s3(
                city=args.city,
                release=tag,
                h3_resolution=args.h3_resolution,
                include_satellite=args.satellite,
                data_dir=data_dir,
            )

    if failed == len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
