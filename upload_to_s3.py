#!/usr/bin/env python3
"""Upload Overture pipeline outputs to S3.

Maps local data/{city}/overture_releases/{release}/ files to the
datacruiser-stdb bucket following raw/ vs processed/ conventions:

  raw/overture/{city}/{release}/          ← 11 layer parquets + metadata JSON
  processed/overture/{city}/{release}/    ← hex features + combined parquets
  processed/overture_ggearth/{city}/      ← satellite embeddings

Usage::

    # Upload after pipeline run (sydney, default release)
    python upload_to_s3.py --city sydney --release 2026-02-18.0 --h3-resolution 9

    # Include satellite embeddings
    python upload_to_s3.py --city sydney --release 2026-02-18.0 --h3-resolution 9 \\
        --include-satellite

    # Custom data directory and bucket
    python upload_to_s3.py --city sydney --release 2026-02-18.0 --h3-resolution 9 \\
        --data-dir /mnt/data --bucket my-bucket
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import boto3
from boto3.s3.transfer import TransferConfig

logger = logging.getLogger("upload_to_s3")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BUCKET_DEFAULT = "unsw-cse-cruiser-overture"
REGION_DEFAULT = "ap-southeast-2"
DATA_DIR_DEFAULT = Path.cwd() / "data"

# The 11 raw Overture layer files (+ division sub-files)
RAW_LAYER_FILES = {
    "roads.parquet",
    "pois.parquet",
    "buildings.parquet",
    "landuse.parquet",
    "addresses.parquet",
    "infrastructure.parquet",
    "land_cover.parquet",
    "connectors.parquet",
    "building_parts.parquet",
    "divisions.parquet",
    "division_areas.parquet",
    "division_boundaries.parquet",
    "bathymetry.parquet",
    "extraction_metadata.json",
}

# Multipart upload config for large parquet files
TRANSFER_CONFIG = TransferConfig(
    multipart_threshold=100 * 1024 * 1024,   # 100 MB
    multipart_chunksize=50 * 1024 * 1024,    # 50 MB chunks
    max_concurrency=4,
)

# ---------------------------------------------------------------------------
# Upload logic
# ---------------------------------------------------------------------------


def _content_type(filename: str) -> str:
    """Return Content-Type for a file based on extension."""
    if filename.endswith(".json"):
        return "application/json"
    if filename.endswith(".parquet"):
        return "application/octet-stream"
    return "application/octet-stream"


def upload_city_to_s3(
    city: str,
    release: str,
    h3_resolution: int,
    bucket: str = BUCKET_DEFAULT,
    region: str = REGION_DEFAULT,
    include_satellite: bool = False,
    data_dir: Path = DATA_DIR_DEFAULT,
) -> dict[str, str]:
    """Upload pipeline outputs to S3.

    Returns a dict mapping local file paths to S3 keys for all
    successfully uploaded files.
    """
    s3 = boto3.client("s3", region_name=region)
    uploaded: dict[str, str] = {}

    release_dir = data_dir / city / "overture_releases" / release
    if not release_dir.exists():
        logger.error("Release directory does not exist: %s", release_dir)
        return uploaded

    res_tag = f"res{h3_resolution:02d}"

    # ------------------------------------------------------------------
    # 1. Raw layer files → raw/overture/{city}/{release}/
    # ------------------------------------------------------------------
    raw_prefix = f"raw/overture/{city}/{release}"
    for filename in sorted(RAW_LAYER_FILES):
        local_path = release_dir / filename
        if not local_path.exists():
            logger.debug("Skipping (not found): %s", local_path)
            continue

        s3_key = f"{raw_prefix}/{filename}"
        _upload_file(s3, bucket, local_path, s3_key)
        uploaded[str(local_path)] = s3_key

    # ------------------------------------------------------------------
    # 2. Processed hex features → processed/overture/{city}/{release}/
    # ------------------------------------------------------------------
    processed_prefix = f"processed/overture/{city}/{release}"
    processed_patterns = [
        f"hex_features_raw_{res_tag}.parquet",
        f"hex_features_{res_tag}.parquet",
        f"combined_{res_tag}.parquet",
    ]
    for filename in processed_patterns:
        local_path = release_dir / filename
        if not local_path.exists():
            logger.debug("Skipping (not found): %s", local_path)
            continue

        s3_key = f"{processed_prefix}/{filename}"
        _upload_file(s3, bucket, local_path, s3_key)
        uploaded[str(local_path)] = s3_key

    # ------------------------------------------------------------------
    # 3. Satellite embeddings → processed/overture_ggearth/{city}/
    # ------------------------------------------------------------------
    if include_satellite:
        sat_dir = data_dir / city / "satellite"
        sat_filename = f"satellite_hex_embeddings_{res_tag}.parquet"
        sat_path = sat_dir / sat_filename

        if sat_path.exists():
            s3_key = f"processed/overture_ggearth/{city}/{sat_filename}"
            _upload_file(s3, bucket, sat_path, s3_key)
            uploaded[str(sat_path)] = s3_key
        else:
            logger.warning("Satellite file not found: %s", sat_path)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    total_bytes = sum(Path(p).stat().st_size for p in uploaded)
    logger.info(
        "Upload complete: %d files, %.1f MB total → s3://%s/",
        len(uploaded),
        total_bytes / (1024 * 1024),
        bucket,
    )

    return uploaded


def _upload_file(
    s3_client: object,
    bucket: str,
    local_path: Path,
    s3_key: str,
) -> None:
    """Upload a single file to S3 with logging and multipart support."""
    size_mb = local_path.stat().st_size / (1024 * 1024)
    logger.info("Uploading %s (%.1f MB) → s3://%s/%s", local_path.name, size_mb, bucket, s3_key)

    s3_client.upload_file(
        str(local_path),
        bucket,
        s3_key,
        Config=TRANSFER_CONFIG,
        ExtraArgs={"ContentType": _content_type(local_path.name)},
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


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
        description="Upload Overture pipeline outputs to S3."
    )
    parser.add_argument(
        "--city", required=True, help="City name (e.g., sydney)."
    )
    parser.add_argument(
        "--release", default="2026-02-18.0",
        help="Overture release tag (default: 2026-02-18.0).",
    )
    parser.add_argument(
        "--h3-resolution", type=int, default=9,
        help="H3 resolution used in pipeline (default: 9).",
    )
    parser.add_argument(
        "--include-satellite", action="store_true",
        help="Also upload satellite embeddings.",
    )
    parser.add_argument(
        "--bucket", default=BUCKET_DEFAULT,
        help=f"S3 bucket name (default: {BUCKET_DEFAULT}).",
    )
    parser.add_argument(
        "--region", default=REGION_DEFAULT,
        help=f"AWS region (default: {REGION_DEFAULT}).",
    )
    parser.add_argument(
        "--data-dir", default=str(DATA_DIR_DEFAULT),
        help=f"Local data directory (default: {DATA_DIR_DEFAULT}).",
    )

    args = parser.parse_args()

    _setup_logging()

    logger.info(
        "Uploading %s/%s (res %d) to s3://%s/",
        args.city, args.release, args.h3_resolution, args.bucket,
    )

    uploaded = upload_city_to_s3(
        city=args.city,
        release=args.release,
        h3_resolution=args.h3_resolution,
        bucket=args.bucket,
        region=args.region,
        include_satellite=args.include_satellite,
        data_dir=Path(args.data_dir),
    )

    if not uploaded:
        logger.warning("No files were uploaded. Check that the pipeline has run for this city/release.")
        sys.exit(1)

    print(f"\nUploaded {len(uploaded)} files:")
    for local_path, s3_key in uploaded.items():
        print(f"  {Path(local_path).name} → s3://{args.bucket}/{s3_key}")


if __name__ == "__main__":
    main()
