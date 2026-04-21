# API Data Reference: What You Actually Get From Each Source

> **Purpose**: Shows the actual data structure, fields, and sample payloads from each API so you know what to expect before writing collection code.

---

## 1. TfNSW Live Hazards API — Response Format

> **Verified 20 April 2026** against the live response captured in the
> jxeeno archive
> ([`raw.githubusercontent.com/jxeeno/nsw-livetraffic-historical/data/data/incident.geojson`](https://raw.githubusercontent.com/jxeeno/nsw-livetraffic-historical/data/data/incident.geojson)),
> which commits the exact bytes returned by this endpoint every 15 minutes.
> The previous version of this section was synthesised from narrative docs
> and contained several wrong field names and types — it has been replaced.
> Cross-checked against the TfNSW Swagger definition listing this endpoint
> as `AllTrafficIncidents` with content-type `application/vnd.geo+json`.

**Endpoint**: `GET https://api.transport.nsw.gov.au/v1/live/hazards/incident/all`
**Auth**: `Authorization: apikey YOUR_KEY` (header)
**Format**: GeoJSON FeatureCollection (`application/vnd.geo+json`)
**Schema applies to**: sibling endpoints `/roadwork/all`, `/fire/all`,
`/flood/all`, `/alpine/all`, `/majorevent/all` all return the same Feature
shape with different `mainCategory` values. The `/incident/all` endpoint
includes **both planned and unplanned** items — filter client-side on
`incidentKind` (see Behavioural quirks below).

### Sample Feature (real response, incident id 212927, Mamre Road)

```json
{
  "type": "Feature",
  "id": 212927,
  "geometry": {
    "type": "Point",
    "coordinates": [150.7698515, -33.7913423],
    "collections": []
  },
  "properties": {
    "webLinks": [
      {
        "linkText": "Mamre Road upgrade",
        "linkURL": "https://www.transport.nsw.gov.au/projects/current-projects/mamre-road-upgrade-between-m4-motorway-st-clair-and-erskine-park-road"
      }
    ],
    "headline": "",
    "periods": [],
    "speedLimit": -1,
    "weblinkUrl": null,
    "expectedDelay": -1,
    "ended": false,
    "isNewIncident": false,
    "publicTransport": "",
    "impactingNetwork": true,
    "subCategoryB": null,
    "arrangementAttachments": [],
    "isInitialReport": false,
    "created": 1730435174000,
    "isMajor": false,
    "name": null,
    "subCategoryA": "null",
    "adviceA": "Check signage",
    "adviceB": "Exercise caution",
    "adviceC": " ",
    "end": 1845985500000,
    "incidentKind": "Planned",
    "mainCategory": "CHANGED TRAFFIC CONDITIONS",
    "lastUpdated": 1731039229940,
    "otherAdvice": "<p>Changed traffic conditions … will be in place at various times along Mamre Rd …</p>",
    "arrangementElements": [],
    "diversions": "",
    "additionalInfo": [],
    "weblinkName": null,
    "attendingGroups": null,
    "encodedPolylines": [],
    "duration": null,
    "start": 1730407620000,
    "displayName": "CHANGED TRAFFIC CONDITIONS Mamre Road upgrade",
    "roads": [
      {
        "conditionTendency": "",
        "crossStreet": "M4 Motorway",
        "delay": "",
        "impactedLanes": [],
        "locationQualifier": "between",
        "mainStreet": "Mamre Road",
        "quadrant": "",
        "queueLength": 0,
        "region": "Sydney",
        "secondLocation": "Erskine Park Road",
        "suburb": "St Clair to Erskine Park",
        "trafficVolume": ""
      }
    ],
    "isLocalRoad": "State road",
    "CategoryIcon": "ChangedConditions"
  }
}
```

### Property field reference (verbatim field names, types, semantics)

| Field | Type | Notes |
|-------|------|-------|
| `webLinks` | `Array<{linkText: string, linkURL: string}>` | Preferred URL source; replaces deprecated `weblinkUrl` |
| `headline` | string | Short one-line summary; may be empty |
| `periods` | array | Recurrence periods; usually empty |
| `speedLimit` | number | `-1` = not applicable; otherwise km/h |
| `weblinkUrl` | string \| null | **Deprecated** — almost always null in real data; use `webLinks` |
| `expectedDelay` | number | Minutes. `-1` = unknown |
| `ended` | **boolean** | `true` = resolved, `false` = active. NOT a timestamp |
| `isNewIncident` | boolean | (was documented as `isNew` — wrong) |
| `publicTransport` | **string** | Free-text. NOT a `{affectedBusRoutes, affectedTrainLines}` object |
| `impactingNetwork` | boolean | (was documented as `isImpactNetwork` — wrong) |
| `subCategoryB` | string \| null | Observed: always null in current snapshot |
| `arrangementAttachments` | array | |
| `isInitialReport` | boolean | |
| `created` | **number (epoch ms)** | e.g. `1730435174000` — NOT ISO 8601 |
| `isMajor` | boolean | |
| `name` | null | Always null in observed data |
| `subCategoryA` | string | Can be the literal string `"null"` (4 chars) as well as real values |
| `adviceA`, `adviceB`, `adviceC` | string | Three advice slots (previously documented as only two) |
| `end` | **number (epoch ms)** | Resolved-at timestamp (distinct from `ended` bool flag) |
| `incidentKind` | string | `"Planned"` or `"Unplanned"` (observed enum) |
| `mainCategory` | string (UPPERCASE) | Open enum — see table below |
| `lastUpdated` | **number (epoch ms)** | |
| `otherAdvice` | string (HTML) | May contain `<p>`, `<a>` etc. |
| `arrangementElements` | array | |
| `diversions` | string | May be HTML |
| `additionalInfo` | array | |
| `weblinkName` | string \| null | |
| `attendingGroups` | `Array<string>` \| null | e.g. `["NSW Police", "Fire & Rescue"]` |
| `encodedPolylines` | `Array<string>` | Google-encoded polylines for affected segments |
| `duration` | string \| null | Human-readable, e.g. `"02h 15m"` |
| `start` | **number (epoch ms)** | |
| `displayName` | string | Typically `${mainCategory} ${description}` |
| `roads` | `Array<Road>` | See Road shape below |
| `isLocalRoad` | **string** | `"State road"` or `"Local road"` — NOT a boolean |
| `CategoryIcon` | string | UI hint, parallels `mainCategory` |
| `hideEndDate` | boolean | When `true`, treat `end` as not-yet-known even if a value is present (for open-ended items) |

### Road shape (`properties.roads[]`)

```ts
{
  region: string,              // e.g. "Sydney", "SYD_MET"
  mainStreet: string,          // "Mamre Road"
  crossStreet: string,         // "M4 Motorway"
  secondLocation: string,      // Used when locationQualifier = "between"
  locationQualifier: string,   // "at" | "between" | "near"
  suburb: string,              // e.g. "St Clair to Erskine Park"
  conditionTendency: string,   // "deteriorating" | "improving" | ""
  quadrant: string,
  trafficVolume: string,
  queueLength: number,
  delay: string,
  impactedLanes: Array<ImpactedLane>,
}
```

### ImpactedLane shape (`properties.roads[].impactedLanes[]`)

```ts
{
  affectedDirection: string,   // e.g. "Both directions", "Northbound"
  closedLanes: string,         // free-text, e.g. "1 of 3 lanes closed" — may be ""
  description: string,         // advisory text — may be ""
  extent: string,              // e.g. "Affected", "Closed"
  numberOfLanes: string,       // string not number — may be ""
  roadType: string,            // may be ""
}
```

### Observed enum values

| Field | Observed values (open enum — treat as extensible) |
|-------|---------------------------------------------------|
| `mainCategory` | `CRASH`, `BREAKDOWN`, `HAZARD`, `ROADWORK`, `EMERGENCY ROADWORK`, `FLOOD`, `FIRE`, `ALPINE`, `MAJOREVENT`, `CHANGED TRAFFIC CONDITIONS`, `ADVERSE WEATHER`, `TRAFFIC LIGHTS BLACKED OUT`, `TRAFFIC LIGHTS FLASHING YELLOW` |
| `incidentKind` | `Planned`, `Unplanned` |
| `subCategoryA` | `"null"` (literal string), `"Road damage"`, `"Landslide"`, plus incident-specific values like `"Multi-vehicle"`, `"Stalled vehicle"`, etc. |
| `CategoryIcon` | `Crash`, `Hazard`, `Breakdown`, `Roadwork`, `Flood`, `Fire`, `Alpine`, `MajorEvent`, `ChangedConditions`, `AdverseWeather` (usually tracks `mainCategory` case-folded) |
| `isLocalRoad` | `"State road"`, `"Local road"` |

### Behavioural quirks (these affect scraper design)

1. **`/incident/all` returns Planned items too.** Filter client-side on
   `incidentKind != "Planned"` AND `mainCategory in {CRASH, BREAKDOWN,
   HAZARD}` to isolate genuine unplanned disruptions (crashes, breakdowns,
   debris/animals/spills). Weather and traffic-conditions changes also
   appear here.
2. **Timestamps are epoch milliseconds**, not ISO 8601. Convert with
   `datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone(ZoneInfo("Australia/Sydney"))`.
3. **Missing numeric data uses `-1`** (`speedLimit`, `expectedDelay`). Don't
   treat `-1` as a valid 0 km/h or 0 min.
4. **`subCategoryA` can be the string `"null"`** — guard against it alongside
   real null.
5. **`ended` (boolean) is the resolved flag; `end` (number) is the resolved
   timestamp** — two different fields with overlapping names.
6. **Dedup key**: `Feature.id` at the top level (not `properties.id`).
   Stable across updates to the same incident.
7. **Non-standard GeoJSON extension**: `geometry.collections: []` appears
   on every Point. Harmless but may trigger strict validators — prefer a
   lenient GeoJSON parser.

---

## 2. TfNSW Historical Traffic API — Response Format

**Endpoint**: `POST https://api.transport.nsw.gov.au/v1/traffic/historicaldata`
**Auth**: `Authorization: apikey YOUR_KEY`
**Format**: JSON — feature shape per §1 above, returned with all the same
fields (epoch-ms timestamps, `ended` boolean flag, `webLinks[]`, etc.). The
Historical API is the same feature envelope with date-range querying.

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
