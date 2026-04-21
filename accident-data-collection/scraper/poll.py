#!/usr/bin/env python3
"""
Traffic incident scraper — polls TfNSW, QLDTraffic, and DTP Victoria every
time it's run, writes raw snapshots + normalized Parquet to S3, exits.

Designed to be invoked by a systemd timer on EC2 every 5 minutes.
See deploy/traffic-scraper.timer.

Source schemas and quirks are documented in
../api-data-reference.md — this file depends on those findings being current.
"""

from __future__ import annotations

import gzip
import io
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

import boto3
import pyarrow as pa
import pyarrow.parquet as pq
import requests
from dateutil import parser as dtparser
from dateutil import tz as dttz

_MEL_TZ = dttz.gettz("Australia/Melbourne")

# =============================================================================
# Config
# =============================================================================

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
HTTP_TIMEOUT = int(os.environ.get("HTTP_TIMEOUT", "30"))
HTTP_RETRIES = int(os.environ.get("HTTP_RETRIES", "3"))

S3_BUCKET = os.environ.get("S3_BUCKET", "datacruiser-stdb")
S3_PREFIX = os.environ.get("S3_PREFIX", "raw/traffic-incidents").rstrip("/")
S3_PROCESSED_PREFIX = os.environ.get(
    "S3_PROCESSED_PREFIX", "processed/traffic-incidents"
).rstrip("/")
AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-2")

TFNSW_API_KEY = os.environ.get("TFNSW_API_KEY", "").strip()
QLDTRAFFIC_API_KEY = os.environ.get(
    "QLDTRAFFIC_API_KEY", "3e83add325cbb69ac4d8e5bf433d770b"
).strip()
DTPVIC_API_KEY = os.environ.get("DTPVIC_API_KEY", "").strip()

# Bounding boxes: [min_lon, min_lat, max_lon, max_lat]
BBOX = {
    "sydney": (150.5, -34.2, 151.5, -33.5),
    "melbourne": (144.5, -38.1, 145.5, -37.5),
    "brisbane": (152.7, -27.8, 153.3, -27.2),
}

# Unplanned categories we care about (crashes, breakdowns, hazards, weather,
# flooding). Planned items (roadworks, scheduled closures) filtered out.
TFNSW_KEEP_CATEGORIES = {
    "CRASH",
    "BREAKDOWN",
    "HAZARD",
    "ADVERSE WEATHER",
    "FLOOD",
    "FIRE",
    "TRAFFIC LIGHTS BLACKED OUT",
    "TRAFFIC LIGHTS FLASHING YELLOW",
    "EMERGENCY ROADWORK",
}

QLD_KEEP_TYPES = {"Crash", "Hazard", "Flooding", "Congestion"}

VIC_KEEP_TYPES = {
    "Incident",
    "Unplanned",
    "Breakdown",
    "Hazard",
    "Crash",
    "Flood",
    "Fire",
}


# =============================================================================
# Logging — JSON lines to stdout so systemd journal + CloudWatch can parse
# =============================================================================


class JSONLFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for k, v in record.__dict__.items():
            if k in payload or k in {
                "args", "msg", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "name",
            }:
                continue
            try:
                json.dumps(v)
                payload[k] = v
            except TypeError:
                payload[k] = repr(v)
        return json.dumps(payload, default=str)


log = logging.getLogger("scraper")
log.setLevel(LOG_LEVEL)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONLFormatter())
log.addHandler(handler)
log.propagate = False


# =============================================================================
# Normalized schema
# =============================================================================


@dataclass
class NormalizedIncident:
    # Identity
    incident_id: str               # "{source}:{native_id}"
    source: str                    # tfnsw | qldtraffic | dtpvic
    city: str                      # sydney | brisbane | melbourne

    # Classification
    event_type: str                # crash | breakdown | hazard | flood | fire | congestion | roadwork | event | other
    event_subtype: str | None
    severity: str | None           # major | high | medium | low | unknown

    # Location
    latitude: float
    longitude: float
    road_name: str | None
    cross_street: str | None
    suburb: str | None
    lga: str | None
    region: str | None

    # Description
    description: str | None
    headline: str | None

    # Timing (all tz-aware UTC)
    start_time: datetime | None
    end_time: datetime | None
    ended: bool
    last_updated: datetime | None

    # Impact
    lanes_affected: int | None
    direction: str | None
    attending_groups: list[str] | None

    # Provenance
    source_url: str | None
    collected_at: datetime
    raw_payload: str               # original JSON feature, preserved verbatim


# =============================================================================
# HTTP helpers
# =============================================================================


def http_get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    retries: int = HTTP_RETRIES,
    timeout: int = HTTP_TIMEOUT,
) -> requests.Response:
    """GET with exponential-backoff retry on 5xx / network errors."""
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=timeout)
            if r.status_code < 500:
                return r  # 2xx/3xx/4xx are not retried — caller handles
            log.warning(
                "http_5xx",
                extra={"url": url, "status": r.status_code, "attempt": attempt},
            )
        except requests.RequestException as e:
            last_exc = e
            log.warning("http_error", extra={"url": url, "attempt": attempt, "err": str(e)})
        if attempt < retries:
            time.sleep(2**attempt)
    if last_exc:
        raise last_exc
    # Return the last response (a 5xx) rather than raising, so caller can handle
    return r


# =============================================================================
# S3 writer
# =============================================================================


s3 = boto3.client("s3", region_name=AWS_REGION)


def s3_put_bytes(key: str, data: bytes, content_type: str, content_encoding: str | None = None) -> None:
    kwargs: dict[str, Any] = {"Bucket": S3_BUCKET, "Key": key, "Body": data, "ContentType": content_type}
    if content_encoding:
        kwargs["ContentEncoding"] = content_encoding
    s3.put_object(**kwargs)


def write_raw_snapshot(source: str, payload: dict, fetched_at: datetime) -> str:
    """Write a gzipped raw GeoJSON snapshot, Hive-partitioned by date."""
    dt = fetched_at.strftime("%Y-%m-%d")
    hour = fetched_at.strftime("%H")
    ts = fetched_at.strftime("%Y%m%dT%H%M%SZ")
    key = f"{S3_PREFIX}/source={source}/dt={dt}/hour={hour}/{ts}.geojson.gz"
    body = gzip.compress(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
        compresslevel=6,
    )
    s3_put_bytes(key, body, content_type="application/geo+json", content_encoding="gzip")
    return key


def write_normalized_parquet(records: list[NormalizedIncident], city: str, source: str, fetched_at: datetime) -> str | None:
    if not records:
        return None
    dt = fetched_at.strftime("%Y-%m-%d")
    ts = fetched_at.strftime("%Y%m%dT%H%M%SZ")
    key = f"{S3_PROCESSED_PREFIX}/dt={dt}/city={city}/source={source}/{ts}.parquet"

    # Build Arrow table — explicit schema guarantees stable column order + types
    schema = pa.schema([
        ("incident_id", pa.string()),
        ("source", pa.string()),
        ("city", pa.string()),
        ("event_type", pa.string()),
        ("event_subtype", pa.string()),
        ("severity", pa.string()),
        ("latitude", pa.float64()),
        ("longitude", pa.float64()),
        ("road_name", pa.string()),
        ("cross_street", pa.string()),
        ("suburb", pa.string()),
        ("lga", pa.string()),
        ("region", pa.string()),
        ("description", pa.string()),
        ("headline", pa.string()),
        ("start_time", pa.timestamp("us", tz="UTC")),
        ("end_time", pa.timestamp("us", tz="UTC")),
        ("ended", pa.bool_()),
        ("last_updated", pa.timestamp("us", tz="UTC")),
        ("lanes_affected", pa.int32()),
        ("direction", pa.string()),
        ("attending_groups", pa.list_(pa.string())),
        ("source_url", pa.string()),
        ("collected_at", pa.timestamp("us", tz="UTC")),
        ("raw_payload", pa.string()),
    ])
    columns: dict[str, list[Any]] = {field.name: [] for field in schema}
    for rec in records:
        d = asdict(rec)
        for field in schema:
            columns[field.name].append(d.get(field.name))

    table = pa.Table.from_pydict(columns, schema=schema)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="zstd")
    s3_put_bytes(key, buf.getvalue(), content_type="application/vnd.apache.parquet")
    return key


# =============================================================================
# Helpers
# =============================================================================


def in_bbox(lon: float, lat: float, bbox: tuple[float, float, float, float]) -> bool:
    min_lon, min_lat, max_lon, max_lat = bbox
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


def first_coord(geom: dict | None) -> tuple[float, float] | None:
    """Extract a representative (lon, lat) from any GeoJSON geometry."""
    if not geom:
        return None
    t = geom.get("type")
    c = geom.get("coordinates")
    if c is None:
        if t == "GeometryCollection":
            for g in geom.get("geometries", []):
                out = first_coord(g)
                if out:
                    return out
        return None
    if t == "Point":
        return float(c[0]), float(c[1])
    if t == "LineString":
        return float(c[0][0]), float(c[0][1])
    if t == "MultiPoint":
        return float(c[0][0]), float(c[0][1])
    if t == "Polygon":
        return float(c[0][0][0]), float(c[0][0][1])
    if t == "MultiLineString":
        return float(c[0][0][0]), float(c[0][0][1])
    if t == "MultiPolygon":
        return float(c[0][0][0][0]), float(c[0][0][0][1])
    return None


def epoch_ms_to_utc(ms: Any) -> datetime | None:
    """TfNSW timestamps are epoch ms integers."""
    if ms is None or ms == -1 or ms == 0:
        return None
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def parse_iso(s: Any, tz_fallback=timezone.utc) -> datetime | None:
    """Parse an ISO 8601 string to a tz-aware UTC datetime.

    tz_fallback: timezone to assume when the string has no offset. QLD returns
    offset-aware strings so the default (UTC) is fine. DTP Vic returns naive
    local Melbourne time — pass _MEL_TZ for those calls.
    """
    if not s or not isinstance(s, str):
        return None
    try:
        dt = dtparser.isoparse(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz_fallback)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def safe_int(v: Any) -> int | None:
    try:
        if v is None or v == "":
            return None
        return int(v)
    except (ValueError, TypeError):
        return None


def safe_str(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        if not s or s.lower() == "null":
            return None
        return s
    return str(v)


# =============================================================================
# Source 1: TfNSW Live Hazards — Sydney
# =============================================================================


def fetch_tfnsw(fetched_at: datetime) -> tuple[dict, list[NormalizedIncident]]:
    if not TFNSW_API_KEY:
        raise RuntimeError("TFNSW_API_KEY not set")

    # /incident/all includes both Planned and Unplanned — we filter client-side
    url = "https://api.transport.nsw.gov.au/v1/live/hazards/incident/all"
    headers = {"Authorization": f"apikey {TFNSW_API_KEY}", "Accept": "application/geo+json"}
    r = http_get(url, headers=headers)
    r.raise_for_status()
    payload = r.json()

    records: list[NormalizedIncident] = []
    for feat in payload.get("features", []):
        p = feat.get("properties", {}) or {}

        # Filter: drop Planned items and non-relevant categories
        if p.get("incidentKind") == "Planned":
            continue
        main_cat = (p.get("mainCategory") or "").upper()
        if main_cat not in TFNSW_KEEP_CATEGORIES:
            continue

        coord = first_coord(feat.get("geometry"))
        if not coord:
            continue
        lon, lat = coord
        if not in_bbox(lon, lat, BBOX["sydney"]):
            continue

        roads = p.get("roads") or []
        road0 = roads[0] if roads else {}
        impacted = road0.get("impactedLanes") or []
        lanes_affected = len(impacted) if impacted else None

        # Event-type mapping (normalize to lower-case kebab stems)
        category_map = {
            "CRASH": "crash",
            "BREAKDOWN": "breakdown",
            "HAZARD": "hazard",
            "ADVERSE WEATHER": "hazard",
            "FLOOD": "flood",
            "FIRE": "fire",
            "TRAFFIC LIGHTS BLACKED OUT": "hazard",
            "TRAFFIC LIGHTS FLASHING YELLOW": "hazard",
            "EMERGENCY ROADWORK": "roadwork",
        }
        event_type = category_map.get(main_cat, "other")

        source_url = None
        web_links = p.get("webLinks") or []
        if web_links and isinstance(web_links, list):
            source_url = safe_str((web_links[0] or {}).get("linkURL"))
        if not source_url:
            source_url = safe_str(p.get("weblinkUrl"))

        records.append(NormalizedIncident(
            incident_id=f"tfnsw:{feat.get('id')}",
            source="tfnsw",
            city="sydney",
            event_type=event_type,
            event_subtype=safe_str(p.get("subCategoryA")) or safe_str(p.get("incidentKind")),
            severity="major" if p.get("isMajor") else "normal",
            latitude=lat,
            longitude=lon,
            road_name=safe_str(road0.get("mainStreet")),
            cross_street=safe_str(road0.get("crossStreet")),
            suburb=safe_str(road0.get("suburb")),
            lga=None,
            region=safe_str(road0.get("region")),
            description=safe_str(p.get("displayName")),
            headline=safe_str(p.get("headline")),
            start_time=epoch_ms_to_utc(p.get("start")) or epoch_ms_to_utc(p.get("created")),
            end_time=(epoch_ms_to_utc(p.get("end")) if not p.get("hideEndDate") else None),
            ended=bool(p.get("ended")),
            last_updated=epoch_ms_to_utc(p.get("lastUpdated")),
            lanes_affected=lanes_affected,
            direction=None,  # TfNSW buries direction in impactedLanes entries
            attending_groups=p.get("attendingGroups") if isinstance(p.get("attendingGroups"), list) else None,
            source_url=source_url,
            collected_at=fetched_at,
            raw_payload=json.dumps(feat, separators=(",", ":"), ensure_ascii=False),
        ))

    return payload, records


# =============================================================================
# Source 2: QLDTraffic — Brisbane
# =============================================================================


def fetch_qldtraffic(fetched_at: datetime) -> tuple[dict, list[NormalizedIncident]]:
    if not QLDTRAFFIC_API_KEY:
        raise RuntimeError("QLDTRAFFIC_API_KEY not set")

    # Hit both endpoints; dedupe by feature id. past-one-hour catches events
    # that resolved between polls.
    base = "https://api.qldtraffic.qld.gov.au/v2"
    combined: dict[Any, dict] = {}
    raw_payloads: list[dict] = []

    for path in ("/events", "/events/past-one-hour"):
        r = http_get(f"{base}{path}", params={"apikey": QLDTRAFFIC_API_KEY})
        if r.status_code != 200:
            log.warning("qld_non_200", extra={"path": path, "status": r.status_code})
            continue
        payload = r.json()
        raw_payloads.append(payload)
        for feat in payload.get("features", []):
            fid = (feat.get("properties") or {}).get("id")
            if fid is None:
                continue
            # Keep the latest version (events endpoint usually fresher)
            combined[fid] = feat

    records: list[NormalizedIncident] = []
    priority_map = {
        "Red Alert": "major", "High": "high", "Medium": "medium", "Low": "low",
    }
    type_map = {
        "Crash": "crash", "Hazard": "hazard", "Flooding": "flood",
        "Congestion": "congestion", "Roadworks": "roadwork", "Special event": "event",
    }

    for feat in combined.values():
        p = feat.get("properties", {}) or {}
        event_type_raw = p.get("event_type") or ""
        if event_type_raw not in QLD_KEEP_TYPES:
            continue

        coord = first_coord(feat.get("geometry"))
        if not coord:
            continue
        lon, lat = coord
        if not in_bbox(lon, lat, BBOX["brisbane"]):
            continue

        road_summary = p.get("road_summary") or {}
        duration = p.get("duration") or {}
        impact = p.get("impact") or {}
        source_obj = p.get("source") or {}

        records.append(NormalizedIncident(
            incident_id=f"qldtraffic:{p.get('id')}",
            source="qldtraffic",
            city="brisbane",
            event_type=type_map.get(event_type_raw, "other"),
            event_subtype=safe_str(p.get("event_subtype")),
            severity=priority_map.get(p.get("event_priority") or ""),
            latitude=lat,
            longitude=lon,
            road_name=safe_str(road_summary.get("road_name")),
            cross_street=None,
            suburb=safe_str(road_summary.get("locality")),
            lga=safe_str(road_summary.get("local_government_area")),
            region=safe_str(road_summary.get("district")),
            description=safe_str(p.get("description")),
            headline=safe_str(p.get("advice")) or safe_str(p.get("information")),
            start_time=parse_iso(duration.get("start")) or parse_iso(p.get("published")),
            end_time=parse_iso(duration.get("end")),
            ended=False,  # If it's in /events it's active; /past-one-hour may include resolved, but no explicit bool
            last_updated=parse_iso(p.get("last_updated")) or parse_iso(p.get("published")),
            lanes_affected=None,  # QLD doesn't expose a lane count — would need to parse impact_subtype text
            direction=safe_str(impact.get("direction")),
            attending_groups=None,
            source_url=safe_str(p.get("web_link") or p.get("url")),
            collected_at=fetched_at,
            raw_payload=json.dumps(feat, separators=(",", ":"), ensure_ascii=False),
        ))

    # Merge payloads for the raw snapshot (keep the freshest per feature id)
    merged = {
        "type": "FeatureCollection",
        "fetched_at": fetched_at.isoformat(),
        "features": list(combined.values()),
    }
    return merged, records


# =============================================================================
# Source 3: DTP Victoria — Melbourne (Unplanned Disruptions v2)
# =============================================================================


def fetch_dtpvic(fetched_at: datetime) -> tuple[dict, list[NormalizedIncident]]:
    if not DTPVIC_API_KEY:
        raise RuntimeError("DTPVIC_API_KEY not set")

    base = (
        "https://api.opendata.transport.vic.gov.au/opendata/roads/disruptions/unplanned/v2"
    )

    # Paginate: pages 1-9 × up to 500 items. In practice one page is enough,
    # but loop to be safe.
    all_features: list[dict] = []
    last_meta: dict = {}
    for page in range(1, 10):
        params = {"page": page, "limit": 500}

        # Empirically KeyID works; Ocp-Apim-Subscription-Key returns 401 for
        # keys generated via the portal. Try KeyID first, fall back to the
        # spec-documented header.
        r = http_get(base, headers={"KeyID": DTPVIC_API_KEY}, params=params)
        if r.status_code in (401, 403):
            log.info("vic_retry_subscription_key_header", extra={"status": r.status_code})
            r = http_get(
                base,
                headers={"Ocp-Apim-Subscription-Key": DTPVIC_API_KEY},
                params=params,
            )
        if r.status_code != 200:
            log.warning("vic_non_200", extra={"status": r.status_code, "page": page, "body": r.text[:500]})
            break
        payload = r.json()
        features = payload.get("features") or []
        all_features.extend(features)
        last_meta = payload.get("meta") or {}
        total = int(last_meta.get("total_records") or 0)
        if total <= len(all_features):
            break
        if not features:
            break

    records: list[NormalizedIncident] = []
    for feat in all_features:
        p = feat.get("properties", {}) or {}
        coord = first_coord(feat.get("geometry"))
        if not coord:
            continue
        lon, lat = coord
        if not in_bbox(lon, lat, BBOX["melbourne"]):
            continue

        # The v2 schema event_type is free-text ("Incident", "Unplanned", etc.);
        # classify mainly on eventSubType for crashes/hazards/breakdowns.
        et = (p.get("eventType") or p.get("event_type") or "").lower()
        subt = (p.get("eventSubType") or p.get("event_subtype") or "").lower()
        if "crash" in subt or "collision" in subt or "crash" in et:
            event_type = "crash"
        elif "breakdown" in subt or "stalled" in subt or "broken" in subt:
            event_type = "breakdown"
        elif "flood" in subt or "flood" in et:
            event_type = "flood"
        elif "fire" in subt or "fire" in et:
            event_type = "fire"
        elif "hazard" in subt or "debris" in subt or "spill" in subt or "animal" in subt:
            event_type = "hazard"
        elif et in ("roadwork", "roadworks") or "roadwork" in subt:
            event_type = "roadwork"
        else:
            event_type = "other"

        reference = p.get("reference") or {}
        source_obj = p.get("source") or {}
        impact = p.get("impact") or {}

        records.append(NormalizedIncident(
            incident_id=f"dtpvic:{p.get('id') or p.get('eventId') or p.get('impactId')}",
            source="dtpvic",
            city="melbourne",
            event_type=event_type,
            event_subtype=safe_str(p.get("eventSubType") or p.get("event_subtype")),
            severity=None,
            latitude=lat,
            longitude=lon,
            road_name=safe_str(p.get("closedRoadName") or p.get("declaredRoadName") or reference.get("localRoadName")),
            cross_street=safe_str(reference.get("startIntersectionRoadName")),
            suburb=safe_str(reference.get("startIntersectionLocality") or reference.get("endIntersectionLocality")),
            lga=safe_str(reference.get("localGovernmentArea")),
            region=safe_str(reference.get("closedRoadTransportRegion")),
            description=safe_str(p.get("description")),
            headline=None,
            start_time=parse_iso(p.get("created"), tz_fallback=_MEL_TZ),
            end_time=parse_iso(p.get("lastClosed"), tz_fallback=_MEL_TZ),
            ended=bool(p.get("lastClosed")),
            last_updated=parse_iso(p.get("lastUpdated") or p.get("lastActive"), tz_fallback=_MEL_TZ),
            lanes_affected=safe_int(p.get("numberLanesImpacted")),
            direction=safe_str(impact.get("direction")),
            attending_groups=None,
            source_url=safe_str(p.get("weblinkURL")),  # socialMedia is text, not a URL
            collected_at=fetched_at,
            raw_payload=json.dumps(feat, separators=(",", ":"), ensure_ascii=False),
        ))

    merged = {
        "type": "FeatureCollection",
        "fetched_at": fetched_at.isoformat(),
        "meta": last_meta,
        "features": all_features,
    }
    return merged, records


# =============================================================================
# Main
# =============================================================================


SOURCES: list[tuple[str, str, Callable[[datetime], tuple[dict, list[NormalizedIncident]]]]] = [
    ("tfnsw", "sydney", fetch_tfnsw),
    ("qldtraffic", "brisbane", fetch_qldtraffic),
    ("dtpvic", "melbourne", fetch_dtpvic),
]


def run() -> int:
    fetched_at = datetime.now(timezone.utc)
    log.info("poll_start", extra={"fetched_at": fetched_at.isoformat(), "bucket": S3_BUCKET})

    exit_code = 0
    for source, city, fetcher in SOURCES:
        try:
            t0 = time.monotonic()
            payload, records = fetcher(fetched_at)
            raw_key = write_raw_snapshot(source, payload, fetched_at)
            parquet_key = write_normalized_parquet(records, city, source, fetched_at)
            log.info(
                "poll_source_ok",
                extra={
                    "source": source,
                    "city": city,
                    "raw_features": len(payload.get("features") or []),
                    "normalized_records": len(records),
                    "raw_key": raw_key,
                    "parquet_key": parquet_key,
                    "elapsed_sec": round(time.monotonic() - t0, 2),
                },
            )
        except Exception as exc:
            log.error("poll_source_failed", extra={"source": source, "err": str(exc)}, exc_info=True)
            exit_code = 2  # partial failure

    log.info("poll_end", extra={"exit_code": exit_code})
    return exit_code


if __name__ == "__main__":
    sys.exit(run())
