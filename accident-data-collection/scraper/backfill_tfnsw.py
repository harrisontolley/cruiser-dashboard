#!/usr/bin/env python3
"""
One-off NSW backfill via the TfNSW Historical Traffic Data API.

This API retains a rolling ~3-month window of incident history for NSW.
March 2026 data will age out around late June 2026, so run this ASAP.

Usage:
  python backfill_tfnsw.py \
      --start 2026-03-01T00:00:00+11:00 \
      --end   2026-04-01T00:00:00+11:00 \
      --lat -33.8688 --lon 151.2093 --radius 500

Writes the raw JSON response to:
  s3://{S3_BUCKET}/{S3_PREFIX}/source=tfnsw-historical/dt={YYYY-MM-DD}/backfill_{start}_{end}.json.gz
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
import requests
from dateutil import parser as dtparser


S3_BUCKET = os.environ.get("S3_BUCKET", "datacruiser-stdb")
S3_PREFIX = os.environ.get("S3_PREFIX", "raw/traffic-incidents").rstrip("/")
AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
TFNSW_API_KEY = os.environ.get("TFNSW_API_KEY", "").strip()

MAX_WINDOW_DAYS = 90  # API enforces a 90-day max per query


def query_window(start: datetime, end: datetime, lat: float, lon: float, radius: int) -> dict[str, Any]:
    url = "https://api.transport.nsw.gov.au/v1/traffic/historicaldata"
    body = {
        "latitude": lat,
        "longitude": lon,
        "radius": radius,
        "created": start.isoformat(),
        "end": end.isoformat(),
        "showHistory": True,
    }
    headers = {
        "Authorization": f"apikey {TFNSW_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    r = requests.post(url, headers=headers, json=body, timeout=120)
    r.raise_for_status()
    return r.json()


def write_snapshot(payload: dict[str, Any], start: datetime, end: datetime) -> str:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    dt = start.strftime("%Y-%m-%d")
    key = (
        f"{S3_PREFIX}/source=tfnsw-historical/dt={dt}/"
        f"backfill_{start.strftime('%Y%m%dT%H%M%SZ')}_{end.strftime('%Y%m%dT%H%M%SZ')}.json.gz"
    )
    body = gzip.compress(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
        compresslevel=6,
    )
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=body, ContentType="application/json", ContentEncoding="gzip")
    return key


def split_windows(start: datetime, end: datetime, max_days: int) -> list[tuple[datetime, datetime]]:
    out: list[tuple[datetime, datetime]] = []
    cur = start
    while cur < end:
        nxt = min(end, cur + timedelta(days=max_days))
        out.append((cur, nxt))
        cur = nxt
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="ISO 8601 start, e.g. 2026-03-01T00:00:00+11:00")
    ap.add_argument("--end", required=True, help="ISO 8601 end (exclusive)")
    ap.add_argument("--lat", type=float, default=-33.8688, help="Centre latitude")
    ap.add_argument("--lon", type=float, default=151.2093, help="Centre longitude")
    ap.add_argument("--radius", type=int, default=500, help="Radius in km (max 500)")
    args = ap.parse_args()

    if not TFNSW_API_KEY:
        print("ERROR: TFNSW_API_KEY env var not set", file=sys.stderr)
        return 1

    start = dtparser.isoparse(args.start)
    end = dtparser.isoparse(args.end)
    if start.tzinfo is None or end.tzinfo is None:
        print("ERROR: --start and --end must include a timezone offset", file=sys.stderr)
        return 1

    windows = split_windows(start, end, MAX_WINDOW_DAYS)
    print(f"Running {len(windows)} query window(s) at centre=({args.lat}, {args.lon}) radius={args.radius}km")

    for i, (w_start, w_end) in enumerate(windows, 1):
        print(f"  [{i}/{len(windows)}] {w_start.isoformat()} → {w_end.isoformat()}")
        payload = query_window(w_start, w_end, args.lat, args.lon, args.radius)
        n = len(payload.get("features") or payload.get("incidents") or [])
        key = write_snapshot(payload, w_start, w_end)
        print(f"    features={n} → s3://{S3_BUCKET}/{key}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
