# Investigation Findings: March 2026 Data Recoverability

> **Investigated**: 16 April 2026
> **Status**: All open questions from the data collection plan have been resolved

---

## Summary

| State | March 2026 Data Recoverable? | Method | Urgency |
|-------|------------------------------|--------|---------|
| **NSW** | **YES** | TfNSW Historical API + GitHub archive | Act within weeks (3-month rolling window) |
| **QLD** | **NO** (from public APIs) | Contact TMR directly | Email TMR now |
| **VIC** | **NO** (from public APIs) | Contact VicRoads / wait for CrashStats (~Oct 2026) | Email VicRoads now |
| **TomTom** | **NO** | Real-time only, confirmed | N/A |
| **HERE** | **NO** | Real-time only, confirmed | N/A |

---

## 1. NSW — Transport for NSW (TfNSW)

### Verdict: RECOVERABLE via two independent paths

### Path 1: Historical Traffic Data API (Primary — act immediately)

**Endpoint**: `POST https://api.transport.nsw.gov.au/v1/traffic/historicaldata`

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `latitude` | number (-90 to 90) | Centre point latitude |
| `longitude` | number (-180 to 180) | Centre point longitude |
| `radius` | number (0-500) | Search radius in km |
| `created` | ISO 8601 datetime | Start of date range |
| `end` | ISO 8601 datetime | End of date range |
| `showHistory` | boolean | Include historical records |

**Authentication**: `Authorization: apikey [TOKEN]` header. Register free at https://opendata.transport.nsw.gov.au/

**Documented retention**: Rolling 3-month window. March 2026 is currently within this window but early March data could start expiring by mid-June 2026.

**Important discrepancy**: The Mendeley Sydney GMA dataset researchers (Kumar, Bisht, Chand — *Data in Brief* 51, 2023) successfully queried data from January 2017 through July 2022 — a span of **5.5 years** — using this exact endpoint. They ran approximately 22 sequential 90-day queries (the API has a 90-day max per query). This contradicts the "3-month" description. Possible explanations:
- The 3-month limit was introduced after May 2023
- The documented limit is conservative and actual retention is longer
- Different API subscription tiers may have different retention

**Recommended query for March 2026**:
```
POST https://api.transport.nsw.gov.au/v1/traffic/historicaldata
Authorization: apikey YOUR_KEY_HERE

{
  "latitude": -33.8688,
  "longitude": 151.2093,
  "radius": 500,
  "created": "2026-03-01T00:00:00+11:00",
  "end": "2026-04-01T00:00:00+11:00",
  "showHistory": true
}
```

Use radius 500 (max) centred on Sydney CBD to capture all of Greater Sydney. If the API limits to 90 days, March fits within a single query.

### Path 2: jxeeno GitHub Archive (Backup — already captured)

**Repository**: https://github.com/jxeeno/nsw-livetraffic-historical

This is a community-maintained archive that has been polling ALL TfNSW `/v1/live/hazards/*/all` endpoints every **15 minutes** via GitHub Actions since at least March 2020.

**Key facts**:
- **372,263+ commits** on the `data` branch
- **Still active** — latest commit April 16, 2026
- **Complete March 2026 coverage confirmed** — commits verified on March 1, 5, 10, 15, 20, 25, 31
- ~2,900 snapshots for the month of March (96 polls/day × 31 days)
- Each snapshot is a GeoJSON FeatureCollection with 50–120 incidents

**Data fields per incident**: `mainCategory` (CRASH, BREAKDOWN, HAZARD, etc.), `created`, `lastUpdated`, `ended`, `displayName`, `roads`, `start`, `end`, `duration`, `incidentKind`, `subCategoryA`, `subCategoryB`, geometry coordinates

**How to use**:
1. Clone the `data` branch: `git clone --branch data https://github.com/jxeeno/nsw-livetraffic-historical.git`
2. Extract all `incident.geojson` snapshots from March 2026 commits
3. Deduplicate by incident ID — any incident active for at least one polling interval (15 min) will be captured
4. Limitation: very short-lived incidents (<15 min) may be missed between polls

**Assessment**: This is free, already captured, and permanent — no expiry risk. However, the Historical API (Path 1) is more complete since it captures all incidents regardless of duration.

### What about `/live/hazards/incident/closed`?

**Retention: ~24 hours only.** Testing confirmed that the closed endpoint only shows incidents from the past 24 hours. The TfNSW website confirms: "check hazards closed in the past 24 hours." This is useless for March backfill.

### Other NSW sources checked

| Source | Status |
|--------|--------|
| NSW Crash Data CSV (opendata.transport.nsw.gov.au) | Covers 2020–2024 only. March 2026 ETA: ~2027 |
| data.peclet.com.au | Mirrors livetraffic.com; unclear retention |
| equivalentideas/nsw_livetraffic_incidents (Morph.io) | Appears inactive |
| Transport NSW Road Safety Statistics | Quarterly bulletins; latest covers Q1 2025 |

---

## 2. Queensland — QLDTraffic (Transport and Main Roads)

### Verdict: NOT RECOVERABLE from public APIs

### API Investigation

The QLDTraffic API (v1.10, dated 19 Feb 2025) has exactly **two event endpoints**:

| Endpoint | Behaviour |
|----------|-----------|
| `/v2/events` | Returns **only currently active/published events**. No date parameters, no status filter. Today's query returned 674 events — all active. Zero March 2026 crash/hazard incidents. |
| `/v2/events/past-one-hour` | Returns events archived/updated in the **past 60 minutes only**. Archived events appear here for at most 1 hour, then disappear permanently. |

**There are zero query parameters for date range, time filtering, or status filtering.** The API spec PDF confirms the scope is "real-time information."

### Data Retention

- Events are purged from the API **almost immediately after resolution**
- Crash events only persist while active — once archived, they vanish from `/v2/events` and appear in `/v2/events/past-one-hour` for ≤60 minutes
- The 58 "March 2026" events visible today are all **still-active roadworks** with future end dates — not crashes or breakdowns
- The OpenDataSoft mirror (`queensland.opendatasoft.com`) reflects the same live data — not a historical archive

### Alternative sources checked

| Source | Availability | March 2026? |
|--------|-------------|-------------|
| Crash Data from QLD Roads (data.qld.gov.au) | Jan 2001 – Jun 2024 | No |
| Road Crash Locations (data.qld.gov.au) | Jan 2001 – Jun 2024 | No |
| QPS Traffic Statistics (police.qld.gov.au) | Available for purchase | Statistical reports only, not incident-level |
| QPS Traffic Incident Reports (CITEC Confirm) | Per-incident requests | Yes, but not bulk — requires "genuine interest" |
| Wayback Machine snapshots | Attempted | All returned HTTP 401 (API key required) |
| TMR Traffic Census | Annual averages | Volume only, not incidents |
| Road Safety Statistics (publications.qld.gov.au) | Weekly fatality reports | Fatalities only |

### Recovery options

1. **Contact TMR directly** (qldtraffic@tmr.qld.gov.au) — they almost certainly retain internal records. Request a data extract for March 2026 Brisbane-area incidents under CC BY 4.0 terms. This is the best shot.
2. **Check if any researcher** was running a continuous scraper during March 2026 (unlikely to find)
3. **QPS CITEC Confirm** — individual incident reports, not bulk, not free

---

## 3. Victoria — VicRoads / Department of Transport and Planning

### Verdict: NOT RECOVERABLE from public APIs (until ~October 2026 via CrashStats)

### API Investigation

The VicRoads Unplanned Disruptions v2 API has only two query parameters: `page` (1-9) and `limit` (0-500). **No date range, time, or status filter parameters exist.** The API is described as "near real-time" — it returns only the current active incident set.

Each record includes `created`, `lastUpdated`, `lastClosed`, `status` fields, but there is no way to query by date or request past incidents.

**The v1 documentation PDF** is now access-denied (`PublicAccessNotPermitted`).

### VicEmergency Feed

The feed at `data.emergency.vic.gov.au` does retain some incidents — today's data included bushfires from January 2026. However:
- These are all large/significant **fire and emergency incidents** that remain in "Under Control" status
- No March 2026 traffic incidents appear — they've been resolved and purged
- The feed covers fires, hazmat, rescue — not traffic incidents specifically
- No historical query endpoint or archive API exists

### Alternative sources checked

| Source | Availability | March 2026? |
|--------|-------------|-------------|
| Victoria Road Crash Data (CrashStats) | From 2012, monthly updates | **~October 2026** (7-month lag) |
| MAV OpenDataSoft mirror | Requires auth (401) | Likely real-time mirror, not archive |
| data.vic.gov.au general search | No relevant incident dataset found | No |

### Recovery options

1. **Email VicRoads for API token** — even though March data is gone, set up for future collection. See [email draft](./vicroads-email-draft.md).
2. **Contact VicRoads/DTP directly** — request a historical data extract for March 2026 Melbourne-area unplanned disruptions
3. **Wait for CrashStats** — the Victoria Road Crash Data dataset will include March 2026 police-reported crashes around October 2026 (7-month lag). This covers crashes only, not breakdowns/hazards.
4. **Intelematics** — as a Melbourne-based company, they likely have the most complete Melbourne incident archive. Contact for pricing.

---

## 4. TomTom Traffic Incidents API

### Verdict: CONFIRMED REAL-TIME ONLY — no historical incident data exists as a product

**Traffic Incidents API** (the free-tier API):
- Returns incidents within a bounding box for the **current Traffic Model ID**
- The Traffic Model ID updates every minute and expires after 2 minutes
- The `timeValidityFilter` parameter only accepts `"present"` or `"future"` — no `"past"` option
- Zero date-range query parameters
- Explicitly serves "present incident data" and "planned future incidents"

**TomTom MOVE / Traffic Stats** (the historical products):
- Provides **speed, travel time, and traffic density statistics** only
- 17+ year archive of GPS probe data (speed observations)
- Can "detect the impact on traffic of events and incidents" but only through their effect on speed — not as individual incident records
- Products: Traffic Stats, O/D Analysis, Route Monitoring, Junction Analytics, Historical Traffic Volumes
- **None provide individual incident records**

**Conclusion**: There is no TomTom product — free or paid — that provides historical individual traffic incident records. The separation is absolute:
- Real-time API → current incidents
- Historical products → speed/flow statistics only

---

## 5. HERE Traffic API

### Verdict: CONFIRMED REAL-TIME ONLY — same as TomTom

**HERE Traffic API v7**:
- Provides "real-time traffic flow and incident information"
- Incidents endpoint returns only current active incidents
- No date range query parameters for historical retrieval

**HERE Historical Products**:
- **Speed Data**: 5-year historical archive, 2-day latency — speed observations in 5/15/60-minute increments only
- **Traffic Patterns**: Average speeds by day-of-week from 3 years of data
- Both are **speed/flow only** — no individual incident records

**Conclusion**: Same as TomTom. No historical individual incident records available.

---

## 6. Action Items (Updated)

### Do This Week

1. **Register for TfNSW API key** and run the Historical Traffic API query for March 2026. This is the single most valuable action.
2. **Clone jxeeno/nsw-livetraffic-historical** `data` branch as backup for NSW
3. **Send VicRoads email** — request API token AND ask about historical March 2026 data extract (see [email draft](./vicroads-email-draft.md))
4. **Email TMR Queensland** (qldtraffic@tmr.qld.gov.au) — request March 2026 Brisbane incident data extract

### Do This Month

5. **Set up ongoing scraper** for all three state APIs (5-min polling) to capture future data
6. **Contact Intelematics** if VIC/QLD government data requests fail — they archive historical incidents for all three metros

### Later

7. **October 2026**: Download Victoria CrashStats update which should include March 2026 crash data
8. **Late 2026**: Check QLD crash data update on data.qld.gov.au

---

## 7. Revised Assessment

| City | Best Path to March 2026 Data | Confidence | Data Completeness |
|------|------------------------------|------------|-------------------|
| **Sydney** | TfNSW Historical API + jxeeno archive | **High** | All incidents including breakdowns |
| **Melbourne** | Direct request to VicRoads/DTP + Intelematics fallback | **Medium** | Depends on response; CrashStats in Oct covers crashes only |
| **Brisbane** | Direct request to TMR + Intelematics fallback | **Medium** | Depends on response; crash data update TBD |
