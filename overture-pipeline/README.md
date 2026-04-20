# Overture Maps Pipeline

Python pipeline that extracts Overture Maps layers for a given city, optionally
pulls Google Earth Engine satellite embeddings, aggregates to H3 hexes, and
uploads the results to `s3://unsw-cse-cruiser-overture` (override with
`--s3-bucket`).

## Setup

Fresh machine (Amazon Linux 2023 or Ubuntu/Debian):

```bash
./ec2-setup.sh
source .venv/bin/activate
```

## Usage

```bash
# Basic — extract + hex aggregation + upload
./run-pipeline.sh sydney 5750005 --hex-agg

# With satellite embeddings (needs GEE auth)
earthengine authenticate
./run-pipeline.sh melbourne 4246124 --satellite --ee-project datacruiser

# Or run the two Python entrypoints directly
python download_multi_release.py --city sydney --relation-id 5750005 --hex-agg
python upload_to_s3.py --city sydney --release 2026-02-18.0 --h3-resolution 9
```

`rerun-all-cities.sh` is a batch wrapper that re-runs Brisbane, Sydney, and
Melbourne in sequence on an EC2 box (use inside `tmux`).

## After a successful run

Update the dashboard metadata so the new dataset shows up:

```bash
cd ../dashboard
npm run scrape
```
