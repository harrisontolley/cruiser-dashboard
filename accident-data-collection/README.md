# Accident Data Collection

Research and planning documents for collecting Australian traffic events,
incidents, and breakdowns data to overlay with CompassIoT vehicle trajectory
data.

**Target window**: 1 March – 1 April 2026
**Coverage**: Sydney (NSW), Melbourne (VIC), Brisbane (QLD)
**Last audit**: 20 April 2026

## Documents

| File | Description |
|------|-------------|
| [traffic-incident-data-collection.md](./traffic-incident-data-collection.md) | Master reference — all data sources, APIs, costs, architecture, timeline |
| [investigation-findings.md](./investigation-findings.md) | API investigation results — what's recoverable for March 2026 and what's not |
| [api-data-reference.md](./api-data-reference.md) | Actual data formats, sample payloads, and field descriptions for each API |
| [licensing-analysis.md](./licensing-analysis.md) | Legal analysis — CC BY 4.0 permits commercial AI training, per-source verdict |

## Key Findings

- **NSW**: March 2026 data IS recoverable via TfNSW Historical API + the jxeeno GitHub archive
- **QLD**: March 2026 data is NOT available from public APIs — email `qldtraffic@tmr.qld.gov.au` for an extract (confirmed via QLDTraffic API spec v1.10, 19 Feb 2025)
- **VIC**: March 2026 data is NOT available from public APIs — email `PTdataprogram@transport.vic.gov.au` for an extract
- **TomTom/HERE**: confirmed real-time only — no historical incident records exist as a product

## Important 2025-audit corrections (applied 20 Apr 2026)

- The legacy VicRoads platforms (`api.vicroads.vic.gov.au` and the Data Exchange Platform `data-exchange.vicroads.vic.gov.au`) were **decommissioned 30 September 2025**. The old `traffic_requests@vicroads.vic.gov.au` mailbox no longer serves API-token requests. API keys are now self-serve at `opendata.transport.vic.gov.au`; historical-extract requests go to `PTdataprogram@transport.vic.gov.au`.
- The DTP Victoria v2 API uses auth header `Ocp-Apim-Subscription-Key` (not `KeyID`), base URL `https://api.opendata.transport.vic.gov.au/opendata/roads/disruptions/unplanned/v2`, and a rate limit of **10 calls/minute**.
- QLDTraffic is licensed as **CC BY 4.0 Australia** (the spec stamps the "AU" variant) — substantively identical to CC BY 4.0 International for commercial AI training.
- QLDTraffic `apikey` is a **URL query parameter**, not a header. The spec publishes a global public key (`3e83add325cbb69ac4d8e5bf433d770b`, 100 req/min global limit) for unregistered use.

## Immediate Actions

1. **Register for TfNSW API key** and run the Historical API backfill (data ages out of the rolling 3-month window around June 2026)
2. **Register on Transport Victoria Open Data Portal** (`opendata.transport.vic.gov.au`) — self-serve, API key auto-generated
3. **Historical-data-request emails sent** to `PTdataprogram@transport.vic.gov.au` (VIC) and `qldtraffic@tmr.qld.gov.au` (QLD) — awaiting response
4. **Clone `jxeeno/nsw-livetraffic-historical`** (`data` branch) as the NSW backup
5. **Stand up a 5-minute polling scraper** now so forward windows are covered regardless of email outcomes
