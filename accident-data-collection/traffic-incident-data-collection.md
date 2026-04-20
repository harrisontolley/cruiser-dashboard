# Australian Traffic Events, Incidents & Breakdowns — Data Collection Plan

> **Prepared**: 16 April 2026
> **Target window**: 1 March – 1 April 2026
> **Coverage**: Sydney (NSW), Melbourne (VIC), Brisbane (QLD)
> **Purpose**: Overlay incident/event/breakdown data on CompassIoT vehicle trajectories

---

## Executive Summary

We need traffic events, incidents, and breakdowns data for Sydney, Melbourne, and Brisbane during March 2026 to correlate with CompassIoT GPS/trajectory data already in the DataCruiser S3 bucket. No pre-built dataset exists for this (confirmed by Wilson Wongso). The March window has **already passed**, so the strategy is **historical backfill first, then ongoing collection for future windows**.

**Urgency**: The TfNSW Historical API retains only 3 months of data. March 2026 incidents will expire from this API around **June 2026**. Action is needed immediately.

### Recommended Approach

1. **This week**: Register for API keys (TfNSW, VicRoads, QLDTraffic) and backfill March data from government APIs that retain closed/historical incidents
2. **This week**: Set up a recurring scraper (5-minute polling) to capture ongoing data for any future windows
3. **This month**: Download supplementary historical datasets (Mendeley, state crash archives) for context
4. **If gaps remain**: Contact Intelematics (SUNA) for commercial historical data — they archive 200K+ incidents

---

## Table of Contents

1. [Backfill Strategy — Recovering March 2026 Data](#1-backfill-strategy--recovering-march-2026-data)
2. [Data Sources — Government APIs (Free, CC-BY)](#2-data-sources--government-apis-free-cc-by)
3. [Data Sources — Commercial APIs (Free Tier)](#3-data-sources--commercial-apis-free-tier)
4. [Data Sources — Historical Archives](#4-data-sources--historical-archives)
5. [Data Sources — Insurance & CTP](#5-data-sources--insurance--ctp)
6. [Data Sources — Breakdowns & Roadside Assistance](#6-data-sources--breakdowns--roadside-assistance)
7. [Data Sources — Enterprise / Paid](#7-data-sources--enterprise--paid)
8. [Data Sources — Social Media & News](#8-data-sources--social-media--news)
9. [Recommended Collection Architecture](#9-recommended-collection-architecture)
10. [Implementation Timeline](#10-implementation-timeline)
11. [Cost Summary](#11-cost-summary)
12. [Legal Considerations](#12-legal-considerations)

---

## 1. Backfill Strategy — Recovering March 2026 Data

Since the target window has passed, sources are ranked by **what data is still recoverable**:

### Priority 1: Government APIs with Historical Retention

| Source | Retention | March 2026 Available Until | Action |
|--------|-----------|---------------------------|--------|
| TfNSW Historical Traffic API | 3 months rolling | ~June 2026 | **Query immediately** |
| TfNSW `/live/hazards/*/closed` | Unknown (weeks–months) | **Check ASAP** | Test endpoint for March data |
| QLDTraffic `/v2/events` | Unknown — may include past events | **Check ASAP** | Query with date filters |
| VicRoads Unplanned Disruptions | Unknown — closed incidents may persist | **Check ASAP** | Request API token, then test |

### Priority 2: Emergency / Aggregator Feeds

| Source | Notes |
|--------|-------|
| VicEmergency JSON feed | May retain recent closed incidents |
| EmergencyAPI.com | Aggregator — test if historical queries are supported |

### Priority 3: Data That Won't Have March 2026 Yet

| Source | Expected Availability |
|--------|----------------------|
| NSW crash data CSV (opendata.transport.nsw.gov.au) | ~2027 (annual updates) |
| VIC road crash data CSV (discover.data.vic.gov.au) | ~October 2026 (7-month lag) |
| QLD crash data CSV (data.qld.gov.au) | ~Late 2026 (periodic updates) |
| Insurance/CTP claims data | 6–12 month lag |

### Priority 4: Commercial Fallback

| Source | Historical? | Cost |
|--------|-------------|------|
| Intelematics SUNA/INSIGHT | Yes — archives 200K+ incidents | Contact for pricing |
| INRIX | Yes — from 2014 | Enterprise pricing |
| TomTom / HERE | **No** — real-time only, March data is lost | N/A |

---

## 2. Data Sources — Government APIs (Free, CC-BY)

All Australian state government traffic APIs use **Creative Commons Attribution 4.0** licensing — free to use, including commercially, with attribution.

### 2.1 NSW — Transport for NSW (TfNSW) Open Data Hub

| Field | Detail |
|-------|--------|
| **Portal** | https://opendata.transport.nsw.gov.au/ |
| **API Base** | `https://api.transport.nsw.gov.au/v1/live/` |
| **Auth** | OAuth 2.0 — register free at portal for client ID/secret |
| **License** | CC-BY 4.0 |
| **Format** | GeoJSON |
| **Coverage** | All of NSW (Sydney primary) |
| **Cost** | Free |
| **Rate Limit** | Not explicitly stated; 5-min polling recommended |
| **Developer Guide** | [PDF](https://opendata.transport.nsw.gov.au/sites/default/files/2024-10/Live%20Traffic%20NSW%20Developer%20Guide%202023-10%20v1.9_opendata.pdf) |

**Live Hazard Endpoints** (all support `open`, `closed`, `all` suffixes):

| Endpoint | Description |
|----------|-------------|
| `/live/hazards/incident/{status}` | Traffic incidents (crashes, breakdowns, obstructions) |
| `/live/hazards/roadwork/{status}` | Roadworks and lane closures |
| `/live/hazards/majorevent/{status}` | Major events affecting traffic |
| `/live/hazards/fire/{status}` | Fires near roads |
| `/live/hazards/flood/{status}` | Flooding events |
| `/live/hazards/alpine/{status}` | Alpine road conditions |

**Additional Endpoints**:

| Endpoint | Description |
|----------|-------------|
| `/live/cameras` | Traffic camera locations and images |
| `/ttds/route` | Travel time prediction |
| `/ttds/events` | Acceleration/deceleration events |

**Historical Traffic API**: Provides incident data for the last **3 months**. This is the primary backfill mechanism for March 2026 NSW data.

**Assessment**: **Best overall source.** Most comprehensive, well-documented, includes breakdowns + crashes + all hazard types with GPS coordinates. The Mendeley Sydney GMA dataset (85K incidents) was built by scraping this exact API, validating the approach.

---

### 2.2 Victoria — VicRoads / Department of Transport and Planning

| Field | Detail |
|-------|--------|
| **Portal** | https://data-exchange.vicroads.vic.gov.au/ |
| **Open Data** | https://discover.data.vic.gov.au/dataset/unplanned-disruptions-road |
| **Auth** | Email `traffic_requests@vicroads.vic.gov.au` with subject "API Token Request" — token in `KeyID` header |
| **Rate Limit** | 20 calls per 60 seconds |
| **Update Frequency** | Every 60 seconds |
| **License** | CC-BY 4.0 |
| **Format** | JSON (OpenAPI spec available) |
| **Coverage** | Melbourne Controlled Area + DTP roads statewide |
| **Cost** | Free |

**Data Model**: Parent-child structure (Incident -> Location Impact). Includes:
- Unplanned disruptions (crashes, breakdowns, hazards)
- Lane closures
- Tow allocations in Melbourne Controlled Area

**OpenAPI Spec**: https://opendata.transport.vic.gov.au/dataset/af595015-e191-45e5-ab89-6ebca7257e54/resource/e49bbb1b-4764-4736-a629-02c339ebaab1/download/unplanned_road_disruptions.openapi.json

**Action Required**: Email for API token ASAP — manual approval process, may take days.

**Assessment**: Good real-time data but manual token request is a friction point. The 60-second update frequency makes this the most granular source.

---

### 2.3 Queensland — QLDTraffic (Transport and Main Roads)

| Field | Detail |
|-------|--------|
| **Portal** | https://qldtraffic.qld.gov.au/more/Developers-and-Data/ |
| **API Base** | `https://api.qldtraffic.qld.gov.au/v2/` |
| **Key Endpoint** | `https://api.qldtraffic.qld.gov.au/v2/events?apikey={KEY}` |
| **Auth** | Public API key available (no signup), or register for dedicated key |
| **Rate Limit** | 100 requests/min (public key, global limit) |
| **License** | CC-BY 4.0 |
| **Format** | GeoJSON (FeatureCollection) |
| **Coverage** | All Queensland (Brisbane primary) |
| **Cost** | Free |
| **API Spec** | [PDF](https://qldtraffic.qld.gov.au/media/moreDevelopers-and-Data/qldtraffic-website-api-specification-v1-10.pdf) |

**Available Feeds**: Hazards, Crashes, Congestion, Flooding, Roadworks, Special Events, Web Cameras

**Assessment**: Excellent. Public API key means **instant access with zero signup**. Best source for quick testing.

---

### 2.4 VicEmergency (Supplementary for Victoria)

| Field | Detail |
|-------|--------|
| **URL** | `https://data.emergency.vic.gov.au/Show?pageId=getIncidentJSON` |
| **Auth** | None required |
| **Update** | Every 60 seconds |
| **Format** | JSON |
| **Coverage** | All Victoria emergency incidents |
| **Cost** | Free |

Covers fires, crashes, hazards, and other emergencies. No signup needed.

---

### 2.5 Other States (for completeness)

#### Western Australia — Main Roads WA
- **ArcGIS REST**: `https://services2.arcgis.com/cHGEnmsJ165IBJRM/arcgis/rest/services/WebEoc_RoadIncidents/FeatureServer/1`
- **ArcGIS Hub**: https://portal-mainroads.opendata.arcgis.com/datasets/mainroads::webeoc-road-incidents-1
- **Auth**: None required
- **Formats**: ArcGIS REST, CSV, GeoJSON, Shapefile, KML
- **License**: CC-BY 4.0

#### South Australia — Traffic SA
- **Roadworks/Incidents**: `https://maps.sa.gov.au/arcgis/rest/services/DPTIExtTransport/TrafficSAOpenData/MapServer/0`
- **Road Closures**: `https://maps.sa.gov.au/arcgis/rest/services/DPTIExtTransport/TrafficSAOpenData/MapServer/1`
- **Auth**: None
- **Coverage**: Metropolitan Adelaide only

#### Tasmania, Northern Territory, ACT
No dedicated real-time traffic incident APIs found. The **National Freight Data Hub** (https://datahub.freightaustralia.gov.au/) aggregates some state data nationally.

---

## 3. Data Sources — Commercial APIs (Free Tier)

These provide cross-city coverage from a single API but **do not retain historical data** — useful only for ongoing collection, not March backfill.

### 3.1 TomTom Traffic Incidents API

| Field | Detail |
|-------|--------|
| **Base URL** | `https://api.tomtom.com/traffic/services/5/incidentDetails` |
| **Auth** | API key as `key` query parameter |
| **Free Tier** | 2,500 non-tile requests/day (no credit card) |
| **Paid** | $0.75/1,000 requests |
| **Bounding Box Max** | 10,000 km² per request |
| **Format** | GeoJSON |
| **Coverage** | Australia confirmed |
| **Historical** | **No** — real-time only |

At 5-minute polling for 3 cities = ~864 requests/day, well within free tier.

### 3.2 HERE Traffic API v7

| Field | Detail |
|-------|--------|
| **Base URL** | `https://data.traffic.hereapi.com/v7/incidents` |
| **Auth** | `apiKey` query parameter or Bearer token |
| **Free Tier** | 1,000 requests/day (Limited Plan); 30,000/month (Base, requires CC) |
| **Paid** | $0.83/1,000 requests (up to 5M) |
| **Format** | JSON |
| **Coverage** | Australia confirmed |
| **Historical** | **No** — real-time only |

### 3.3 EmergencyAPI.com

| Field | Detail |
|-------|--------|
| **URL** | https://emergencyapi.com/ |
| **Free Tier** | 500 requests/day |
| **Format** | GeoJSON |
| **Coverage** | Aggregates all 8 Australian states |
| **Historical** | Unknown — test if past queries work |

---

## 4. Data Sources — Historical Archives

These provide long-term historical context but **will not have March 2026 data for months** due to publication lag.

### 4.1 Sydney GMA Road Traffic Incident Dataset (Mendeley)

| Field | Detail |
|-------|--------|
| **URL** | https://data.mendeley.com/datasets/cgnx2cs665/5 |
| **Period** | January 2017 – July 2022 (5.5 years) |
| **Records** | 85,611 incidents (39,165 crashes + 46,085 breakdowns) |
| **Coverage** | 333 zones in Sydney Greater Metropolitan Area |
| **License** | CC-BY 4.0 |
| **Format** | Excel, CSV, ESRI Shapefiles |

**Fields include**: Incident ID, category, geo-location, start/end times, duration, street/suburb, vehicles, traffic conditions, advisories, plus 49 road network variables, bus transit data, socioeconomic data, land use.

**Key insight**: This dataset was built by scraping the TfNSW Open Data Hub API — it validates our scraping approach and provides a schema reference.

### 4.2 NSW Historical Crash Data

| Field | Detail |
|-------|--------|
| **URL** | https://opendata.transport.nsw.gov.au/ (search "crash data") |
| **Period** | 2020–2024 (annual updates) |
| **Format** | CSV |
| **March 2026 ETA** | ~2027 |

### 4.3 Victoria Road Crash Data

| Field | Detail |
|-------|--------|
| **URL** | https://discover.data.vic.gov.au/ (search "road crash") |
| **Period** | From 2012, monthly updates |
| **Lag** | **7 months** |
| **Format** | CSV |
| **March 2026 ETA** | ~October 2026 |

### 4.4 Queensland Crash Data

| Field | Detail |
|-------|--------|
| **URL** | https://www.data.qld.gov.au/dataset/crash-data-from-queensland-roads |
| **Period** | January 2001 – December 2024 (23 years) |
| **Content** | All crashes reported to police (fatal and non-fatal) |
| **Format** | CSV |

### 4.5 BITRE Australian Road Deaths Database

| Field | Detail |
|-------|--------|
| **URL** | https://catalogue.data.infrastructure.gov.au/organization/road-safety |
| **Coverage** | National fatalities only |
| **Frequency** | Monthly/quarterly updates |

### 4.6 Kaggle Datasets (for benchmarking/prototyping)

- **Australia & NZ Road Crash**: https://www.kaggle.com/datasets/mgray39/australia-new-zealand-road-crash-dataset
- **Australian Fatal Road Accident 1989–2021**: https://www.kaggle.com/datasets/deepcontractor/australian-fatal-car-accident-data-19892021

### 4.7 AURIN (Australian Urban Research Infrastructure Network)

- **URL**: https://data.aurin.org.au/
- Thousands of multidisciplinary datasets including transport
- Useful for cross-referencing traffic data with urban planning / socioeconomic data
- Some restricted access requiring application

### 4.8 National Road Safety Data Hub

- **URL**: https://datahub.roadsafety.gov.au/
- Monthly road deaths, hospitalised injuries

### 4.9 Office of Road Safety Data Catalogue

- **URL**: https://www.officeofroadsafety.gov.au/data-hub/data-catalogue
- National crash statistics portal

---

## 5. Data Sources — Insurance & CTP

These sources provide scheme-level or aggregated data — useful for context but not individual incident records with GPS coordinates.

### 5.1 SIRA NSW CTP Open Data

| Field | Detail |
|-------|--------|
| **URL** | https://www.sira.nsw.gov.au/open-data |
| **Content** | Daily claims/payments updates |
| **Limitation** | Scheme-level metrics, not individual crash locations |

### 5.2 TAC Victoria

| Field | Detail |
|-------|--------|
| **URL** | https://www.tac.vic.gov.au/road-safety/statistics/online-crash-database |
| **Coverage** | Searchable crash database from 2000 |
| **Limitation** | 6-month lag on hospitalisation claims |

### 5.3 MAIC Queensland CTP

| Field | Detail |
|-------|--------|
| **URL** | https://data.qld.gov.au/ (search "MAIC") |
| **Content** | Semi-annual statistics |
| **Format** | CSV/JSON/XML |

### 5.4 AAMI Crash Index

- Annual PDF reports with city-level crash hotspot rankings
- Aggregated, annual frequency only

---

## 6. Data Sources — Breakdowns & Roadside Assistance

No raw data APIs are available from NRMA (NSW), RACV (VIC), or RACQ (QLD). However:

- **TfNSW API includes breakdowns** as a category alongside crashes — confirmed by the Mendeley dataset which contains **46,085 breakdown records** out of 85,611 total incidents
- **QLDTraffic API** includes hazards which encompass breakdowns and obstructions
- **RACQ** publishes aggregate stats (740,303 roadside calls in FY24) in press releases but no raw data
- **Best approach**: Capture breakdowns from the government traffic APIs — they already include this data

---

## 7. Data Sources — Enterprise / Paid

If free sources have gaps (especially for Victoria where API access is slower to obtain), these commercial providers archive historical incident data:

### 7.1 Intelematics (SUNA/INSIGHT)

| Field | Detail |
|-------|--------|
| **Product** | SUNA Traffic Channel / INSIGHT Platform |
| **Coverage** | Sydney, Melbourne, Brisbane (all three metros) |
| **Historical** | Yes — archives 200,000+ incidents |
| **Granularity** | Per-second frequency |
| **Cost** | Contact for pricing (likely $1,000+/month enterprise) |
| **Website** | https://www.intelematics.com/ |

**Assessment**: Best fallback if government APIs can't backfill March data. They likely have the exact window we need.

### 7.2 INRIX

| Field | Detail |
|-------|--------|
| **Coverage** | National |
| **Historical** | From 2014 |
| **Cost** | Enterprise pricing |
| **Notes** | Powers Google Maps traffic layer |

### 7.3 Waze for Cities (Connected Citizens Program)

| Field | Detail |
|-------|--------|
| **Cost** | Free |
| **Restriction** | **Government agencies only** — transport departments, emergency services, road operators |
| **Data** | Traffic Alerts, Accidents, Irregularities (2-min refresh) |
| **Integration** | Google Cloud BigQuery |
| **Partners** | 600+ in 50+ countries |

Not available to private entities or researchers directly. Could potentially be accessed through a university partnership with a transport agency.

---

## 8. Data Sources — Social Media & News

### Twitter/X Traffic Accounts
- **@LiveTrafficSyd** / **@LiveTrafficNSW** (NSW)
- **@MelbTraffic** (VIC)
- **@QLDTrafficMetro** (QLD)

X/Twitter API costs $100+/month minimum. Historical tweet access requires the Academic Research tier or a commercial data provider like Brandwatch.

### News / RSS
- State traffic websites may expose RSS feeds for incident alerts
- Local media outlets report major incidents but coverage is selective and unstructured

**Assessment**: Low priority. The government APIs provide the same data in structured form.

---

## 9. Recommended Collection Architecture

### For Backfill (March 2026)

```
One-off Python script:
  1. Authenticate with TfNSW Historical API
  2. Query all incidents for date range 2026-03-01 to 2026-04-01
  3. Filter to Sydney bounding box [150.5, -34.2, 151.5, -33.5]
  4. Repeat for VicRoads (Melbourne) and QLDTraffic (Brisbane)
  5. Normalize to common schema
  6. Store raw GeoJSON + normalized Parquet to S3
```

### For Ongoing Collection (Future Windows)

```
AWS EventBridge Schedule (every 5 minutes)
  -> Lambda (Python 3.12)
    -> Parallel fetch: TfNSW, VicRoads, QLDTraffic, TomTom, HERE
    -> Validate & normalize (pydantic)
    -> Deduplicate (incident_id + source)
    -> Upload to S3:
        Raw:       s3://datacruiser-stdb/raw/traffic-incidents/{source}/{date}/
        Processed: s3://datacruiser-stdb/processed/traffic-incidents/
```

**Alternative**: Simple cron job on EC2 or local machine:
```
*/5 * * * * python3 /opt/scrapers/collect_incidents.py
```

### Normalized Data Schema

```json
{
  "incident_id": "string (source-specific unique ID)",
  "source": "tfnsw | vicroads | qldtraffic | tomtom | here | vicemergency",
  "city": "sydney | melbourne | brisbane",
  "type": "crash | breakdown | hazard | roadwork | flood | fire | event | congestion",
  "severity": "minor | moderate | major | severe",
  "latitude": -33.8688,
  "longitude": 151.2093,
  "road_name": "string",
  "suburb": "string",
  "description": "string",
  "start_time": "2026-03-15T08:30:00+11:00",
  "end_time": "2026-03-15T09:45:00+11:00",
  "duration_minutes": 75,
  "lanes_affected": 2,
  "vehicles_involved": 3,
  "raw_payload": {},
  "collected_at": "2026-04-16T14:00:00+10:00"
}
```

### S3 Storage Strategy

Aligns with existing DataCruiser bucket structure:
- **Raw**: `s3://datacruiser-stdb/raw/traffic-incidents/{source}/{YYYY-MM-DD}/incidents.geojson`
- **Processed**: `s3://datacruiser-stdb/processed/traffic-incidents/` — Parquet, partitioned by `date` and `city`

### Recommended Python Libraries

| Library | Purpose |
|---------|---------|
| `httpx` or `aiohttp` | Async HTTP for parallel API calls |
| `pydantic` | Response validation and normalization |
| `tenacity` | Retry with exponential backoff |
| `boto3` | S3 upload |
| `pyarrow` | Parquet conversion |
| `geopandas` | Spatial filtering by bounding box |

---

## 10. Implementation Timeline

### Week 1 — Urgent: Backfill & API Access (do this week)

- [ ] **Register for TfNSW API key** — free, instant approval
- [ ] **Email VicRoads** (`traffic_requests@vicroads.vic.gov.au`, subject: "API Token Request") — manual approval, may take days
- [ ] **Test QLDTraffic public API key** — instant, no signup
- [ ] **Register for TomTom API key** — free, instant
- [ ] **Register for HERE API key** — free, instant
- [ ] **Run TfNSW Historical API backfill** for March 2026 NSW data
- [ ] **Test VicRoads and QLDTraffic** for closed/past incident retrieval
- [ ] **Test VicEmergency and EmergencyAPI** for historical queries

### Week 2 — Validate & Supplement

- [ ] Verify data quality and completeness from each backfill source
- [ ] Identify gaps in coverage (especially VIC if API token is delayed)
- [ ] Download Mendeley Sydney GMA dataset for schema reference
- [ ] Download QLD crash data archive for historical context
- [ ] If VIC data has gaps: contact Intelematics for Melbourne historical data

### Week 3 — Normalize & Store

- [ ] Normalize all collected data to common schema
- [ ] Convert to Parquet, partition by date and city
- [ ] Upload to S3 bucket (`s3://datacruiser-stdb/raw/traffic-incidents/` and `processed/`)
- [ ] Update `scripts/catalogue.json` to include new dataset
- [ ] Run `scripts/scrape-s3.ts` to refresh dashboard metadata

### Ongoing — Future Collection

- [ ] Deploy Lambda or cron scraper for 5-minute polling
- [ ] Set up monitoring/alerting for scraper failures
- [ ] Review data volume and adjust deduplication logic

---

## 11. Cost Summary

### Free Sources (sufficient for most needs)

| Source | Cost | Notes |
|--------|------|-------|
| TfNSW | Free | CC-BY 4.0, best data |
| VicRoads | Free | CC-BY 4.0, manual token request |
| QLDTraffic | Free | CC-BY 4.0, instant public key |
| VicEmergency | Free | No auth needed |
| TomTom | Free | 2,500 req/day free tier |
| HERE | Free | 1,000 req/day free tier |
| EmergencyAPI | Free | 500 req/day free tier |
| AWS Lambda | ~$0/mo | Within free tier at this volume |
| S3 Storage | ~$0.50/mo | Incident data is small (MBs) |

### Paid Fallbacks (if needed)

| Source | Cost | When to use |
|--------|------|-------------|
| TomTom (over free tier) | $0.75/1,000 requests | Only if polling >2,500x/day |
| HERE (over free tier) | $0.83/1,000 requests | Only if polling >1,000x/day |
| Intelematics SUNA | Contact for pricing (~$1K+/mo est.) | If VIC backfill has gaps |
| INRIX | Enterprise pricing | If comprehensive national historical needed |
| X/Twitter API | $100+/month | Only if social media angle is critical |

**Expected total cost for March 2026 backfill: $0** (all primary sources are free)

---

## 12. Legal Considerations

### Licensing

All major Australian state government traffic APIs use **Creative Commons Attribution 4.0 International** (CC-BY 4.0). This grants:
- Freedom to share and adapt for any purpose, including commercial
- Only requirement: provide attribution to the source

### API Usage

Using official APIs with registered keys is **explicitly sanctioned** by all state transport agencies — these APIs exist specifically for developer consumption. This is unambiguously legal.

### Web Scraping (if needed as fallback)

- Data scraping is generally legal in Australia under the Copyright Act 1968 (Cth)
- The Australian government has not created a specific text/data mining copyright exception
- However, scraping terms of service violations could create contractual (not criminal) liability
- **Recommendation**: Always use official APIs over HTML scraping. Attribute sources as required by CC-BY. Respect rate limits.

### FOI (Freedom of Information)

If a specific dataset is not publicly available (e.g., detailed VIC incident data for a specific period), a formal FOI request to the relevant state transport department is an option. Processing times are typically 30+ days.

---

## Appendix A: Bounding Boxes for Spatial Filtering

| City | Min Lon | Min Lat | Max Lon | Max Lat |
|------|---------|---------|---------|---------|
| Sydney | 150.5 | -34.2 | 151.5 | -33.5 |
| Melbourne | 144.5 | -38.1 | 145.5 | -37.5 |
| Brisbane | 152.7 | -27.8 | 153.3 | -27.2 |

These align with the CompassIoT spatial coverage areas from the Dataset Catalogue.

## Appendix B: API Authentication Quick Reference

| Source | Method | How to Get |
|--------|--------|-----------|
| TfNSW | OAuth 2.0 (client_credentials) | Register at https://opendata.transport.nsw.gov.au/ |
| VicRoads | `KeyID` header | Email traffic_requests@vicroads.vic.gov.au |
| QLDTraffic | `apikey` query param | Public key available; or register at portal |
| VicEmergency | None | Open access |
| TomTom | `key` query param | Register at https://developer.tomtom.com/ |
| HERE | `apiKey` query param | Register at https://developer.here.com/ |
| EmergencyAPI | API key | Register at https://emergencyapi.com/ |
| Main Roads WA | None | Open access (ArcGIS) |

## Appendix C: Related Existing Datasets in DataCruiser

| Dataset | S3 Path | Relevance |
|---------|---------|-----------|
| CompassIoT Raw | `s3://datacruiser-stdb/raw/compass-iot/` | Vehicle trajectories to overlay with incidents |
| CompassIoT Processed | `s3://datacruiser-stdb/processed/compass-iot/` | Iceberg parquet, partitioned by StartDate |
| TfNSW Traffic Prediction | `s3://datacruiser-stdb/raw/du_tfnsw_prediction/` | Volume/speed forecasts for context |
| Overture + Earth Embeddings | `s3://datacruiser-stdb/processed/overture_ggearth/` | H3 hex spatial context for Sydney/Melbourne |
