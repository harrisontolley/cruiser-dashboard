#!/usr/bin/env python3
"""
Smoke test — hits all three sources once, prints feature counts and the first
normalized record from each. Useful for verifying your .env before enabling
the systemd timer on EC2.

Does NOT write to S3.

Usage:
  source .env
  python test_sources.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

# Make imports work when run directly from the scraper/ directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poll import (  # noqa: E402
    fetch_tfnsw,
    fetch_qldtraffic,
    fetch_dtpvic,
    NormalizedIncident,
)


def show(source: str, result: tuple[dict, list[NormalizedIncident]]) -> None:
    payload, records = result
    print(f"\n=== {source.upper()} ===")
    print(f"  raw features:        {len(payload.get('features') or [])}")
    print(f"  normalized records:  {len(records)}")
    if records:
        first = records[0]
        print("  first record:")
        d = {
            k: (v.isoformat() if hasattr(v, "isoformat") else v)
            for k, v in first.__dict__.items()
            if k != "raw_payload"
        }
        print(json.dumps(d, indent=2, default=str))


def main() -> int:
    fetched_at = datetime.now(timezone.utc)
    rc = 0

    for name, fn in [
        ("tfnsw", fetch_tfnsw),
        ("qldtraffic", fetch_qldtraffic),
        ("dtpvic", fetch_dtpvic),
    ]:
        try:
            show(name, fn(fetched_at))
        except Exception as e:
            print(f"\n=== {name.upper()} FAILED ===\n  {e}", file=sys.stderr)
            rc = 2

    return rc


if __name__ == "__main__":
    sys.exit(main())
