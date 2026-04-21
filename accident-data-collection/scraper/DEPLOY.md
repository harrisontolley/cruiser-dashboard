# Traffic Scraper — Deploy Runbook

Everything you need to stand up the scraper on EC2, from a cold laptop.
For deeper detail on the schema / normalization / ops, see `README.md`.

---

## What this scraper does

Every 5 minutes it polls **three** open-data traffic APIs, writes both the
raw response and a normalized Parquet snapshot to S3:

| Source | City | Endpoint |
|--------|------|----------|
| TfNSW | Sydney | `GET /v1/live/hazards/incident/all` |
| QLDTraffic | Brisbane | `GET /v2/events` + `GET /v2/events/past-one-hour` |
| DTP Victoria | Melbourne | `GET /opendata/roads/disruptions/unplanned/v2` |

All three are CC BY 4.0. Commercial AI training permitted per the separate
`licensing-analysis.md`.

---

## S3 layout

Raw snapshots (exact API bytes, gzipped):
```
s3://datacruiser-stdb/raw/traffic-incidents/source={src}/dt={YYYY-MM-DD}/hour={HH}/{TS}.geojson.gz
```

Normalized Parquet (filtered + common schema, Hive-partitioned):
```
s3://datacruiser-stdb/processed/traffic-incidents/dt={YYYY-MM-DD}/city={city}/source={src}/{TS}.parquet
```

---

## Normalized schema (one row = one incident at snapshot time)

| Column | Type | Notes |
|--------|------|-------|
| `incident_id` | string | `{source}:{native_id}` — stable dedup key |
| `source` | string | `tfnsw` / `qldtraffic` / `dtpvic` |
| `city` | string | `sydney` / `brisbane` / `melbourne` |
| `event_type` | string | `crash` / `breakdown` / `hazard` / `flood` / `fire` / `congestion` / `roadwork` / `event` / `other` |
| `event_subtype` | string | Source-native sub-category |
| `severity` | string | `major` / `high` / `medium` / `low` / `normal` / null |
| `latitude`, `longitude` | float64 | WGS84 |
| `road_name`, `cross_street`, `suburb`, `lga`, `region` | string | |
| `description`, `headline` | string | |
| `start_time`, `end_time`, `last_updated` | timestamp[us, UTC] | Epoch-ms / ISO normalized to UTC |
| `ended` | bool | `true` once resolved |
| `lanes_affected` | int32 | |
| `direction` | string | `Northbound`, etc. |
| `attending_groups` | list<string> | TfNSW only |
| `source_url` | string | Deep link |
| `collected_at` | timestamp[us, UTC] | Poll time |
| `raw_payload` | string | Original JSON feature, preserved |

### Filters applied before writing Parquet

| Source | Event types kept | Bbox |
|--------|------------------|------|
| TfNSW | `CRASH`, `BREAKDOWN`, `HAZARD`, `ADVERSE WEATHER`, `FLOOD`, `FIRE`, `EMERGENCY ROADWORK`, `TRAFFIC LIGHTS *`. Drops everything with `incidentKind="Planned"`. | Sydney `[150.5, -34.2, 151.5, -33.5]` |
| QLDTraffic | `Crash`, `Hazard`, `Flooding`, `Congestion` | Brisbane `[152.7, -27.8, 153.3, -27.2]` |
| DTP Vic | Classified from `eventSubType` regex (crash/collision/breakdown/stalled/flood/fire/hazard/debris/spill/animal) | Melbourne `[144.5, -38.1, 145.5, -37.5]` |

Raw snapshots are **not** filtered — re-normalize later without re-calling the API.

---

## Files in this folder

```
scraper/
├── DEPLOY.md              ← this file
├── README.md              ← full reference (schema, ops, troubleshooting)
├── .env.example           ← copy to .env on the box, fill in keys
├── requirements.txt       ← 4 deps
├── poll.py                ← main scraper (systemd invokes this)
├── backfill_tfnsw.py      ← one-off NSW historical backfill
├── test_sources.py        ← smoke test (no S3 writes)
└── deploy/
    ├── ec2-setup.sh                   ← idempotent EC2 bootstrap
    ├── traffic-scraper.service        ← systemd unit
    ├── traffic-scraper.timer          ← OnCalendar=*:0/5
    └── iam-policy.json                ← minimal S3 write IAM policy
```

---

## Before you SSH: get the three API keys ready

1. **TfNSW** — register at https://opendata.transport.nsw.gov.au/ → create an app → copy the API key. Free, instant.
2. **DTP Victoria** — create an account at https://opendata.transport.vic.gov.au/, click **Subscribe** on the *Unplanned Disruptions – Road* product, copy the primary key from your profile. Free, instant.
3. **QLDTraffic** — the public key `3e83add325cbb69ac4d8e5bf433d770b` (100 req/min shared global) works out of the box. For a dedicated key, email `qldtraffic@tmr.qld.gov.au`.

---

## Step-by-step deploy (30 min)

### 1 — Launch the EC2 box

- AMI: Amazon Linux 2023 *or* Ubuntu 24.04 (both work)
- Instance type: **t4g.nano** (2 vCPU, 0.5 GB — free-tier eligible)
- Storage: 10 GB gp3
- Security group: egress `443/tcp` to `0.0.0.0/0`. No inbound ports needed.
- **IAM role**: create/attach a role with the policy in `deploy/iam-policy.json` (S3 write on the `traffic-incidents` prefix only).

### 2 — SSH in and bootstrap

```bash
# Install git
sudo dnf -y install git         # Amazon Linux
# — or —
sudo apt-get install -y git     # Ubuntu

# Clone
git clone https://github.com/<you>/cruiser-dashboard.git
cd cruiser-dashboard/accident-data-collection/scraper

# Run the bootstrap (installs Python venv, copies code, installs systemd units)
chmod +x deploy/ec2-setup.sh
sudo deploy/ec2-setup.sh
```

This creates `/opt/traffic-scraper/` with the venv, copies the scripts,
installs + **enables** the timer (doesn't start polling yet).

### 3 — Fill in API keys

```bash
sudoedit /opt/traffic-scraper/.env
```

Set `TFNSW_API_KEY`, `DTPVIC_API_KEY`, and (optionally) replace
`QLDTRAFFIC_API_KEY` with your registered key.

### 4 — Smoke test (no S3 writes)

```bash
sudo -u ubuntu bash -c '
  cd /opt/traffic-scraper
  set -a; source .env; set +a
  .venv/bin/python test_sources.py
'
```

Expected output: non-zero feature counts for all 3 sources and one
normalized sample record printed per source.

### 5 — One-shot real run

```bash
sudo systemctl start traffic-scraper.service
journalctl -u traffic-scraper.service -n 50 --no-pager
```

Verify the S3 drop-off:
```bash
aws s3 ls s3://datacruiser-stdb/raw/traffic-incidents/ --recursive | tail
aws s3 ls s3://datacruiser-stdb/processed/traffic-incidents/ --recursive | tail
```

### 6 — Start the 5-min timer

```bash
sudo systemctl start traffic-scraper.timer
systemctl list-timers | grep traffic-scraper
```

### 7 — Tail logs

```bash
journalctl -u traffic-scraper.service -f
```

Look for `poll_source_ok` lines with feature counts, `poll_end exit_code=0`.

---

## NSW historical backfill — do this today, not tomorrow

TfNSW's Historical API has a rolling ~3-month retention. March 2026 data
ages out around late June 2026. Run once from the EC2 box:

```bash
cd /opt/traffic-scraper
set -a; source .env; set +a
.venv/bin/python backfill_tfnsw.py \
  --start 2026-03-01T00:00:00+11:00 \
  --end   2026-04-02T00:00:00+11:00 \
  --lat -33.8688 --lon 151.2093 --radius 500
```

Writes to:
```
s3://datacruiser-stdb/raw/traffic-incidents/source=tfnsw-historical/dt=2026-03-01/backfill_*.json.gz
```

---

## Querying the normalized data

### Local DuckDB

```python
import duckdb
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs; SET s3_region='ap-southeast-2';")
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

### Athena

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

(If `city` / `source` inside the Parquet schema clash with partition
names, rename the partition keys or query the physical path directly.)

---

## Day-to-day ops

| Task | Command |
|------|---------|
| Tail logs live | `journalctl -u traffic-scraper.service -f` |
| Last 24 h outcomes | `journalctl -u traffic-scraper.service --since "24 hours ago" \| jq -r .msg \| sort \| uniq -c` |
| Run once manually | `sudo systemctl start traffic-scraper.service` |
| Pause polling | `sudo systemctl stop traffic-scraper.timer` |
| Disable across reboots | `sudo systemctl disable traffic-scraper.timer` |
| Rotate API keys | `sudoedit /opt/traffic-scraper/.env` (no restart — next firing picks up) |
| Pull code updates | `git pull && sudo cp poll.py backfill_tfnsw.py test_sources.py requirements.txt /opt/traffic-scraper/ && sudo -u ubuntu /opt/traffic-scraper/.venv/bin/pip install -r /opt/traffic-scraper/requirements.txt` |
| Change poll cadence | `sudo systemctl edit --full traffic-scraper.timer` → edit `OnCalendar=` → `sudo systemctl daemon-reload && sudo systemctl restart traffic-scraper.timer` |

---

## Troubleshooting quick reference

| Symptom | Cause / Fix |
|---------|-------------|
| `401` from TfNSW | Header must be `Authorization: apikey <key>` — not `Bearer`. Check `.env`. |
| `401/403` from DTP Vic | Code tries `Ocp-Apim-Subscription-Key` first, falls back to `KeyID`. If both fail, you probably haven't **Subscribed** to the Unplanned Disruptions product on the portal. Go click Subscribe. |
| `429` from QLD | Public key is globally shared (100 req/min across all users). Transient; will clear. Switch to a registered key if it's frequent. |
| `poll_source_failed` in journal | One source failed; the other two still ran. Exit code 2 (partial). Next 5-min tick retries. Check the `err` field in the JSON log line. |
| No Parquet landing | `write_normalized_parquet` returns None when 0 records pass the bbox/event-type filter. Check raw GeoJSON → confirm features returned → verify the filter matches your expectation. |
| systemd timer not firing | `systemctl list-timers \| grep traffic`; if absent, `sudo systemctl daemon-reload && sudo systemctl enable --now traffic-scraper.timer`. |
| Boto S3 `AccessDenied` | IAM role not attached or policy missing the processed/raw prefix. Re-check `deploy/iam-policy.json` matches the attached role. |

---

## Cost

| Item | Estimate |
|------|----------|
| EC2 t4g.nano on-demand | ~USD $3/month (or free-tier) |
| S3 storage (~30 MB/month) | <$0.01 |
| S3 PUTs (3 sources × 2 files × 12 polls/hr × 24 × 30) | ~$0.25 |
| Data egress (same-region S3) | $0 |
| **Total** | **< USD $5/month** |

---

## Checklist for tomorrow

- [ ] Have all 3 API keys in hand (TfNSW, DTPVIC, optional QLD registered)
- [ ] Launch t4g.nano with IAM role attached (policy: `deploy/iam-policy.json`)
- [ ] `sudo deploy/ec2-setup.sh` from cloned repo
- [ ] `sudoedit /opt/traffic-scraper/.env` — fill in keys
- [ ] `test_sources.py` — non-zero counts for all 3
- [ ] `sudo systemctl start traffic-scraper.service` — verify S3 drop-off
- [ ] `sudo systemctl start traffic-scraper.timer` — kick off 5-min loop
- [ ] Run `backfill_tfnsw.py` for March 2026 Sydney (don't skip — expires June)
- [ ] Set a CloudWatch Logs subscription or a cron `journalctl` alert on `poll_source_failed` (optional, recommended)
