# Traffic Incident Scraper

Polls TfNSW (Sydney), QLDTraffic (Brisbane), and DTP Victoria (Melbourne) every
5 minutes, writes raw GeoJSON snapshots and a normalized Parquet partition to
S3. Designed to run as a systemd timer on a small EC2 instance.

## What you get

Per poll (every 5 min), per source, two artefacts land in S3:

**Raw snapshots** — exact bytes the API returned, gzipped:
```
s3://{bucket}/raw/traffic-incidents/source={src}/dt={YYYY-MM-DD}/hour={HH}/{TS}.geojson.gz
```

**Normalized Parquet** — filtered to the city bbox, mapped to the schema below:
```
s3://{bucket}/processed/traffic-incidents/dt={YYYY-MM-DD}/city={city}/source={src}/{TS}.parquet
```

Hive-style partitioning (`dt=…/city=…/source=…`) is Athena- and DuckDB-native —
you can `SELECT * FROM read_parquet(...)` with no glue job.

## Normalized schema

All three sources map to one `NormalizedIncident` record (see `poll.py`):

| Column | Type | Notes |
|--------|------|-------|
| `incident_id` | string | `{source}:{native_id}` — stable dedup key |
| `source` | string | `tfnsw` \| `qldtraffic` \| `dtpvic` |
| `city` | string | `sydney` \| `brisbane` \| `melbourne` |
| `event_type` | string | `crash` \| `breakdown` \| `hazard` \| `flood` \| `fire` \| `congestion` \| `roadwork` \| `event` \| `other` |
| `event_subtype` | string | Source-native sub-category (e.g. `"Multi-vehicle"`, `"Stalled vehicle"`) |
| `severity` | string | `major` \| `high` \| `medium` \| `low` \| `normal` \| `null` |
| `latitude` / `longitude` | float64 | WGS84, representative point |
| `road_name`, `cross_street`, `suburb`, `lga`, `region` | string | |
| `description`, `headline` | string | |
| `start_time`, `end_time`, `last_updated` | timestamp[us, UTC] | Epoch-ms / ISO normalized to UTC |
| `ended` | bool | `true` once resolved |
| `lanes_affected` | int32 | |
| `direction` | string | e.g. `Northbound` |
| `attending_groups` | list<string> | e.g. `["NSW Police", "Fire & Rescue"]` (TfNSW only) |
| `source_url` | string | Deep link into the source portal |
| `collected_at` | timestamp[us, UTC] | Poll timestamp |
| `raw_payload` | string | JSON-encoded original feature, preserved for re-processing |

## Source filters applied

| Source | Event types kept | Bbox |
|--------|------------------|------|
| TfNSW | `CRASH`, `BREAKDOWN`, `HAZARD`, `ADVERSE WEATHER`, `FLOOD`, `FIRE`, `EMERGENCY ROADWORK`, `TRAFFIC LIGHTS BLACKED OUT / FLASHING YELLOW`. Drops all `incidentKind="Planned"` items. | Sydney `[150.5, -34.2, 151.5, -33.5]` |
| QLDTraffic | `Crash`, `Hazard`, `Flooding`, `Congestion` | Brisbane `[152.7, -27.8, 153.3, -27.2]` |
| DTP Vic | Classification by `eventSubType` regex (crash/collision/breakdown/stalled/flood/fire/hazard/debris/spill/animal) | Melbourne `[144.5, -38.1, 145.5, -37.5]` |

Raw snapshots are NOT filtered — they're the full API response. Filtering
only applies to the normalized Parquet so you can re-classify later without
re-calling the API.

## Deploy to EC2 (first-time setup)

### 1. Launch the box

- AMI: Amazon Linux 2023 or Ubuntu 24.04
- Instance: `t4g.nano` is plenty (scraper is I/O-bound, <50 MB RSS)
- Storage: 10 GB gp3
- Security group: egress 443 to `0.0.0.0/0` (no inbound ports needed)
- **IAM role**: attach a role with the policy in `deploy/iam-policy.json`

### 2. Clone + bootstrap

```bash
sudo dnf -y install git     # or: sudo apt-get install -y git
git clone https://github.com/<your-org>/cruiser-dashboard.git
cd cruiser-dashboard/accident-data-collection/scraper
chmod +x deploy/ec2-setup.sh
sudo deploy/ec2-setup.sh
```

`ec2-setup.sh` installs OS deps, creates `/opt/traffic-scraper/.venv`,
copies the scripts, installs the systemd unit + timer, and enables the timer.

### 3. Fill in API keys

```bash
sudoedit /opt/traffic-scraper/.env
```

Required:
- `TFNSW_API_KEY` — register at https://opendata.transport.nsw.gov.au/
- `DTPVIC_API_KEY` — register at https://opendata.transport.vic.gov.au/ and subscribe to **Unplanned Disruptions – Road**
- `QLDTRAFFIC_API_KEY` — the default public key (`3e83add325cbb69ac4d8e5bf433d770b`) works out of the box; replace with your registered key once TMR emails you one

### 4. Smoke-test (no S3 writes)

```bash
sudo -u ubuntu bash -c '
  cd /opt/traffic-scraper
  set -a; source .env; set +a
  .venv/bin/python test_sources.py
'
```

You should see non-zero feature counts for each source and one normalized
sample record printed.

### 5. One-shot production run

```bash
sudo systemctl start traffic-scraper.service
journalctl -u traffic-scraper.service -n 50 --no-pager
```

Logs are JSON lines — grep `poll_source_ok` / `poll_source_failed`.

Verify the S3 drop-off:
```bash
aws s3 ls s3://datacruiser-stdb/raw/traffic-incidents/ --recursive | tail -10
aws s3 ls s3://datacruiser-stdb/processed/traffic-incidents/ --recursive | tail -10
```

### 6. Enable the 5-minute timer

```bash
sudo systemctl start traffic-scraper.timer
systemctl list-timers | grep traffic-scraper
```

### 7. Observe

```bash
# Live log tail
journalctl -u traffic-scraper.service -f

# Last 24 h of outcomes, success/fail counts
journalctl -u traffic-scraper.service --since "24 hours ago" \
  | jq -r '.msg' | sort | uniq -c
```

## TfNSW historical backfill (one-off, do this now)

NSW offers a Historical Traffic Data API with a rolling ~3-month window.
March 2026 data will age out around late June 2026. Run this once from any
machine with the `TFNSW_API_KEY` set:

```bash
# From your laptop or the EC2 box
cd /opt/traffic-scraper
set -a; source .env; set +a
.venv/bin/python backfill_tfnsw.py \
  --start 2026-03-01T00:00:00+11:00 \
  --end   2026-04-02T00:00:00+11:00 \
  --lat -33.8688 --lon 151.2093 --radius 500
```

Writes the raw response(s) to:
```
s3://{bucket}/raw/traffic-incidents/source=tfnsw-historical/dt=2026-03-01/backfill_*.json.gz
```

The 500 km radius around the Sydney CBD covers all CompassIoT-relevant
Sydney territory. Queries longer than 90 days are auto-split.

## Querying the normalized data (Athena / DuckDB)

DuckDB locally:
```python
import duckdb
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
con.execute("SET s3_region='ap-southeast-2';")
con.sql("""
  SELECT city, event_type, COUNT(*) AS n
  FROM read_parquet(
    's3://datacruiser-stdb/processed/traffic-incidents/dt=2026-04-*/city=*/source=*/*.parquet',
    hive_partitioning=1
  )
  GROUP BY city, event_type
  ORDER BY city, n DESC
""").show()
```

Athena:
```sql
CREATE EXTERNAL TABLE traffic_incidents (
  incident_id string, source string, city string,
  event_type string, event_subtype string, severity string,
  latitude double, longitude double,
  road_name string, cross_street string, suburb string, lga string, region string,
  description string, headline string,
  start_time timestamp, end_time timestamp, ended boolean, last_updated timestamp,
  lanes_affected int, direction string, attending_groups array<string>,
  source_url string, collected_at timestamp, raw_payload string
)
PARTITIONED BY (dt string, city_p string, source_p string)
STORED AS PARQUET
LOCATION 's3://datacruiser-stdb/processed/traffic-incidents/';

MSCK REPAIR TABLE traffic_incidents;
```

(Rename `city`/`source` inside the Parquet schema if you clash with the
partition names — or just query the physical file path directly.)

## Operations

### Changing poll frequency

Edit the timer: `OnCalendar=*:0/5` → `*:0/2` for 2 min.
```bash
sudo systemctl edit --full traffic-scraper.timer
sudo systemctl daemon-reload
sudo systemctl restart traffic-scraper.timer
```

### Pausing collection

```bash
sudo systemctl stop traffic-scraper.timer        # temporary
sudo systemctl disable traffic-scraper.timer     # survive reboots
```

### Upgrading code

```bash
cd ~/cruiser-dashboard && git pull
cd accident-data-collection/scraper
sudo cp poll.py backfill_tfnsw.py test_sources.py requirements.txt /opt/traffic-scraper/
sudo -u ubuntu /opt/traffic-scraper/.venv/bin/pip install -r /opt/traffic-scraper/requirements.txt
# Timer picks up the new code on the next firing automatically.
```

### Rotating API keys

```bash
sudoedit /opt/traffic-scraper/.env
# Next timer firing uses the new value — no restart required.
```

## Cost

- EC2 `t4g.nano` on-demand ≈ USD $3/month (or free tier)
- S3 storage: incident data is tiny — expect ~30 MB/month across all three sources
- S3 PUTs: 3 sources × 2 files × 12 polls/hour × 24 × 30 ≈ 52k PUTs/month ≈ USD $0.25/month
- Data egress: zero (S3 is in the same region)

Total: **< USD $5/month** including S3.

## Troubleshooting

**401 from TfNSW** — the `apikey` prefix in the `Authorization` header is required: `Authorization: apikey <key>`. Not `Bearer`.

**401/403 from DTP Vic** — the header name conflicts between docs. `poll.py` tries `Ocp-Apim-Subscription-Key` first and falls back to `KeyID`. If both fail, your subscription on the portal probably isn't authorised for the Unplanned Disruptions product — go back to the portal and click **Subscribe** on the product page.

**Empty QLD response** — the public key is shared across everyone. When it's throttled you get 429 briefly. Get your own key by emailing `qldtraffic@tmr.qld.gov.au`.

**`poll_source_failed` in logs** — the other two sources still ran. The exit code is 2 (partial), which systemd records but doesn't retry within the same firing. The next 5-min tick will try again.

**No Parquet files appearing** — `write_normalized_parquet` returns `None` when there are zero records after filtering. Check the raw GeoJSON in S3 to confirm the source actually returned features, then compare against the bbox / event-type filter.
