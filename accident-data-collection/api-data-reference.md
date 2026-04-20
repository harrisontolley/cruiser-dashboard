# API Data Reference: What You Actually Get From Each Source

> **Purpose**: Shows the actual data structure, fields, and sample payloads from each API so you know what to expect before writing collection code.

---

## 1. TfNSW Live Hazards API — Response Format

**Endpoint**: `GET https://api.transport.nsw.gov.au/v1/live/hazards/incident/all`
**Auth**: `Authorization: apikey YOUR_KEY`
**Format**: GeoJSON FeatureCollection

### Sample Incident Feature

```json
{
  "type": "Feature",
  "id": 1234567,
  "geometry": {
    "type": "Point",
    "coordinates": [151.2093, -33.8688]
  },
  "properties": {
    "mainCategory": "CRASH",
    "created": "2026-03-15T08:30:00+11:00",
    "lastUpdated": "2026-03-15T09:15:00+11:00",
    "ended": "2026-03-15T10:45:00+11:00",
    "isMajor": false,
    "isEnded": true,
    "isNew": false,
    "isImpactNetwork": true,
    "displayName": "Crash on Parramatta Rd at Burwood",
    "headline": "CRASH - Parramatta Rd, Burwood",
    "roads": [
      {
        "region": "SYD_MET",
        "suburb": "Burwood",
        "mainStreet": "Parramatta Road",
        "crossStreet": "Burwood Road",
        "locationQualifier": "at",
        "conditionTendency": "deteriorating",
        "conditionDirection": "both",
        "impactedLanes": [
          {
            "affectedDirection": "Both directions",
            "closedLanes": "1 of 3 lanes closed",
            "description": "Use caution"
          }
        ]
      }
    ],
    "publicTransport": {
      "affectedBusRoutes": ["461", "480"],
      "affectedTrainLines": []
    },
    "adviceA": "Exercise caution",
    "adviceB": "Allow extra travel time",
    "otherAdvice": "Emergency services on scene",
    "incidentKind": "Collision",
    "subCategoryA": "Multi-vehicle",
    "subCategoryB": "2 vehicles",
    "duration": "02h 15m",
    "start": "2026-03-15T08:30:00+11:00",
    "end": "2026-03-15T10:45:00+11:00",
    "periods": [],
    "attendingGroups": ["NSW Police", "Fire & Rescue"],
    "media": null,
    "weblinkUrl": "https://www.livetraffic.com/incident/1234567"
  }
}
```

### Main Category Values

| mainCategory | Description |
|-------------|-------------|
| `CRASH` | Vehicle crashes / collisions |
| `BREAKDOWN` | Vehicle breakdowns |
| `HAZARD` | Road hazards (debris, animals, spills) |
| `ROADWORK` | Planned and emergency roadworks |
| `FLOOD` | Flooding on roads |
| `FIRE` | Bush/structure fires affecting roads |
| `ALPINE` | Alpine road conditions |
| `MAJOREVENT` | Major events affecting traffic |

### Key Fields for Analysis

| Field | Type | Notes |
|-------|------|-------|
| `mainCategory` | string | Incident type — the key classifier |
| `created` | ISO 8601 | When the incident was first reported |
| `ended` | ISO 8601 / null | When the incident was resolved (null if ongoing) |
| `geometry.coordinates` | [lon, lat] | GPS location |
| `roads[].suburb` | string | Suburb name |
| `roads[].mainStreet` | string | Road name |
| `roads[].impactedLanes` | array | Lane closure details |
| `duration` | string | Human-readable duration |
| `incidentKind` | string | Sub-type (e.g., "Collision", "Stalled vehicle") |
| `subCategoryA` / `subCategoryB` | string | Further classification |
| `isMajor` | boolean | Major incident flag |

---

## 2. TfNSW Historical Traffic API — Response Format

**Endpoint**: `POST https://api.transport.nsw.gov.au/v1/traffic/historicaldata`
**Auth**: `Authorization: apikey YOUR_KEY`
**Format**: JSON (similar structure to live hazards but with historical records)

The Historical API uses the same incident schema as the live API but supports date-range queries. The response format includes the same GeoJSON-style features with all the fields listed above.

**Query parameters** (POST body):
```json
{
  "latitude": -33.8688,
  "longitude": 151.2093,
  "radius": 500,
  "created": "2026-03-01T00:00:00+11:00",
  "end": "2026-04-01T00:00:00+11:00",
  "showHistory": true
}
```

**90-day query limit**: A single query can span at most 90 days. March 1–April 1 is 31 days — fits in one query.

---

## 3. QLDTraffic API — Response Format

> Cross-checked against the official [QLDTraffic API specification v1.10
> (19 Feb 2025)](https://qldtraffic.qld.gov.au/media/moreDevelopers-and-Data/qldtraffic-website-api-specification-v1-10.pdf).

**Endpoint**: `GET https://api.qldtraffic.qld.gov.au/v2/events?apikey={KEY}`
**Auth**: API key as URL **query parameter** `apikey` (not a header). Public
key published in the spec: `apikey=3e83add325cbb69ac4d8e5bf433d770b`
(100 requests/minute **global** limit). Invalid keys return HTTP 403; keys
over their quota return HTTP 429.
**License**: CC BY 4.0 Australia (CC BY 4.0 AU) — note the Australia variant.
**Format**: GeoJSON FeatureCollection

### Sample Event Feature

```json
{
  "type": "Feature",
  "geometry": {
    "type": "GeometryCollection",
    "geometries": [
      {"type": "LineString", "coordinates": [[153.0259, -27.3400], [153.0260, -27.3402]]}
    ]
  },
  "properties": {
    "id": 155,
    "status": "Published",
    "published": "2026-03-15T08:30:00+10:00",
    "source": {
      "source_name": "EPS",
      "source_id": null,
      "account": null,
      "provided_by": null,
      "provided_by_url": "Department of Transport and Main Roads"
    },
    "url": "http://api.qldtraffic.qld.gov.au/v1/events/155",
    "event_type": "Crash",
    "event_subtype": "Multi-vehicle",
    "event_due_to": "N/A",
    "impact": {
      "direction": "Northbound",
      "towards": "Caboolture",
      "impact_type": "Lanes blocked",
      "impact_subtype": "Two lanes blocked",
      "delay": "Long delays expected"
    },
    "duration": {
      "start": "2026-03-15T08:30:00+10:00",
      "end": null,
      "active_days": [],
      "recurrences": []
    },
    "event_priority": "High",
    "description": "Crash on Bruce Hwy, northbound, Caboolture",
    "advice": "Use alternative route",
    "information": null,
    "road_summary": {
      "road_name": "Bruce Highway",
      "locality": "Caboolture",
      "postcode": "4510",
      "local_government_area": "MORETON BAY",
      "district": "Metropolitan"
    },
    "last_updated": "2026-03-15T08:45:00+10:00",
    "next_inspection": null,
    "web_link": "https://qldtraffic.qld.gov.au/",
    "area_alert": false,
    "alert_message": null
  }
}
```

### `event_type` values

Exactly one of: `Hazard`, `Crash`, `Congestion`, `Roadworks`, `Special event`,
`Flooding`. `event_subtype` is a second categorical axis (e.g. `Multi-vehicle`,
`Debris on road`, `Flash flooding`) and `event_due_to` a third (e.g. `Fog`,
`Heavy rain`, `Spill`).

### `status` values

Only `Published` or `Reopened`. There is no `Archived` value in the active
endpoint's response — archived events leave `/v2/events` and appear instead
in `/v2/events/past-one-hour` for ≤ 60 minutes.

### Endpoints (per spec §5)

| Endpoint | Returns |
|----------|---------|
| `https://api.qldtraffic.qld.gov.au/v1/` | Historical-format path for pre-v2 clients (no area alerts) |
| `https://api.qldtraffic.qld.gov.au/v2/events` | All currently active (`Published` / `Reopened`) events |
| `https://api.qldtraffic.qld.gov.au/v2/events/past-one-hour` | Events created/updated/archived/reopened in the past 60 minutes of system time |
| `https://api.qldtraffic.qld.gov.au/v1/webcams` | Traffic web camera metadata + image URLs |
| `https://api.qldtraffic.qld.gov.au/v1/floodcams` | Flood camera metadata + image URLs |

The former `/v1/highriskcrashzones` product was **removed** from the API (see
spec v1.7, 24 Apr 2024 — the corresponding section is struck through in v1.10).

**Critical limitation**: no date parameters, no status filter. `/v2/events`
returns only currently active events. Closed/archived events are purged from
`/v2/events` and appear in `/v2/events/past-one-hour` for at most 60 minutes
before permanent removal.

---

## 4. DTP Victoria Unplanned Disruptions API — Response Format

> **Audit correction (20 Apr 2026)**: legacy VicRoads platforms were
> decommissioned 30 September 2025. Use the Transport Victoria Open Data
> Portal and the `Ocp-Apim-Subscription-Key` header (auto-generated when you
> sign up for an account at `opendata.transport.vic.gov.au`). The auth-header
> name `KeyID` previously documented here is obsolete. Fields below were
> cross-checked against the current `unplanned_road_disruptions.openapi.json`.

**Endpoint**: `GET https://api.opendata.transport.vic.gov.au/opendata/roads/disruptions/unplanned/v2`
**Auth**: `Ocp-Apim-Subscription-Key: YOUR_KEY` header (or `subscription-key` query param)
**Format**: GeoJSON FeatureCollection
**Rate limit**: 10 calls/minute

### Sample Disruption Feature

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [144.9631, -37.8136]
  },
  "properties": {
    "id": "DIS-2026-04-001234",
    "impactId": "IMP-2026-04-001234-01",
    "status": "Active",
    "eventType": "Incident",
    "eventSubType": "Multi-vehicle collision",
    "eventId": "EVT-2026-04-001234",
    "description": "Multi-vehicle collision — emergency services on scene",
    "closedRoadName": "Monash Freeway",
    "declaredRoadName": "M1",
    "melway": "58 F7",
    "socialMedia": null,
    "roadAccessType": "Restricted",
    "eventLocationStatus": "On-road",
    "numberLanesImpacted": "2",
    "created": "2026-04-16T08:00:00+10:00",
    "lastUpdated": "2026-04-16T08:30:00+10:00",
    "lastActive": "2026-04-16T08:30:00+10:00",
    "lastClosed": null,
    "vcsd": null,
    "weblinkURL": null,
    "reference": {
      "localRoadName": "Monash Freeway",
      "roadAuthority": "DTP",
      "declaredRoadNumber": "M1",
      "startIntersectionRoadName": "Toorak Rd",
      "startIntersectionLocality": "South Yarra",
      "endIntersectionRoadName": "Burke Rd",
      "endIntersectionLocality": "Camberwell",
      "localGovernmentArea": "Stonnington",
      "srns": null,
      "closedRoadSESRegion": "Southern Metro",
      "closedRoadTransportRegion": "Metro",
      "rmaClass": "Freeway",
      "closedRoadBusRoute": "605",
      "closedRoadTramRoute": null
    },
    "source": {
      "sourceName": "VicRoads RCIS",
      "sourceId": "RCIS-12345"
    },
    "impact": {
      "direction": "Outbound",
      "impactType": "Lane closure"
    }
  }
}
```

**Top-level response**: a GeoJSON `FeatureCollection` with `type`, `features`,
`meta` (`total_records`, `page`, `limit`, `count`), and `links[]`
(pagination). Each feature uses the shape above.

### Query Parameters (v2 API)

| Parameter | Default | Allowed values |
|-----------|---------|----------------|
| `page` | 1 | 1–9 |
| `limit` | 0 | 0, 100, 200, 300, 400, 500 |

**That's it.** No date, status, or location filters. Returns only the current active set.

---

## 5. VicEmergency Feed — Response Format

**Endpoint**: `GET https://data.emergency.vic.gov.au/Show?pageId=getIncidentJSON`
**Auth**: None
**Format**: JSON

### Sample Incident

```json
{
  "id": "CFA-2026-001234",
  "feedType": "incident",
  "status": "Under Control",
  "category1": "Fire",
  "category2": "Grass & Scrub Fire",
  "sourceOrg": "CFA",
  "sourceFeed": "cfa_incidents",
  "sourceTitle": "CFA Incidents",
  "location": "LILYDALE",
  "created": "2026-03-15T14:00:00+11:00",
  "updated": "2026-03-16T08:00:00+11:00",
  "lat": -37.755,
  "lng": 145.355,
  "resources": 5,
  "size": "0.5 ha",
  "origin": "Lilydale-Monbulk Rd"
}
```

**Coverage**: Fires, hazmat, rescue, road accidents attended by CFA/SES. Not a dedicated traffic feed — captures only incidents that involve emergency services.

**Retention**: Retains active/under-control incidents. Once fully resolved, incidents are purged within days to weeks. March 2026 traffic incidents are already gone.

---

## 6. TomTom Traffic Incidents API — Confirmed Real-Time Only

**Endpoint**: `GET https://api.tomtom.com/traffic/services/5/incidentDetails`
**Auth**: `key` query parameter
**Format**: GeoJSON

### Confirmed Limitations

- Traffic Model ID updates every minute, expires after 2 minutes
- `timeValidityFilter` only accepts `"present"` or `"future"` — no `"past"`
- No date-range query parameters whatsoever
- Serves only current incidents and planned future events

### TomTom Historical Products (MOVE / Traffic Stats)

| Product | Data Type | Historical? | Incidents? |
|---------|-----------|-------------|------------|
| Traffic Stats API | Speed, travel time, density | Yes (17+ years) | **No** — speed only |
| O/D Analysis | Origin-destination flows | Yes | No |
| Route Monitoring | Route travel times | Yes | No |
| Junction Analytics | Intersection performance | Yes | No |
| Historical Traffic Volumes | Traffic counts | Yes | No |

**Verdict**: No TomTom product provides historical individual incident records. Historical products are exclusively speed/flow analytics.

---

## 7. HERE Traffic API — Confirmed Real-Time Only

**Endpoint**: `GET https://data.traffic.hereapi.com/v7/incidents`
**Auth**: `apiKey` query parameter
**Format**: JSON

### HERE Historical Products

| Product | Data Type | Incidents? |
|---------|-----------|------------|
| Speed Data | Speed observations (5/15/60-min) | **No** |
| Traffic Patterns | Average speeds by day-of-week | No |

**Verdict**: Same as TomTom. Real-time incidents only. Historical products cover speed data, not individual incidents.

---

## 8. jxeeno GitHub Archive — Data Format

**Repository**: https://github.com/jxeeno/nsw-livetraffic-historical
**Branch**: `data`
**Format**: GeoJSON snapshots committed every 15 minutes

### File Structure (on `data` branch)

```
data/
  incident.geojson      # Current snapshot of /live/hazards/incident/all
  roadwork.geojson      # Current snapshot of /live/hazards/roadwork/all
  fire.geojson          # Current snapshot of /live/hazards/fire/all
  flood.geojson         # Current snapshot of /live/hazards/flood/all
  alpine.geojson        # Current snapshot of /live/hazards/alpine/all
  majorevent.geojson    # Current snapshot of /live/hazards/majorevent/all
```

Each file is a GeoJSON FeatureCollection with the same schema as the TfNSW live hazards API (see Section 1 above).

**To extract March 2026 data**: Use `git log` on the `data` branch to find all commits between March 1–31, 2026, then reconstruct the full incident set by deduplicating across all snapshots.

---

## Summary: Data Completeness by Source

| Source | Incidents | Breakdowns | Hazards | Roadworks | Floods/Fires | Events | GPS Coords | Duration |
|--------|-----------|------------|---------|-----------|-------------|--------|------------|----------|
| TfNSW Live/Historical | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| QLDTraffic | Yes | Partial | Yes | Yes | Yes | Yes | Yes | Partial |
| VicRoads | Yes | Yes | Yes | No (separate feed) | No | No | Yes | Yes |
| VicEmergency | Partial | No | Partial | No | Yes | No | Yes | No |
| TomTom | Yes | No | Yes | Yes | No | No | Yes | Partial |
| HERE | Yes | No | Yes | Yes | No | No | Yes | Partial |
| jxeeno Archive | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
