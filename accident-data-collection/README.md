# Traffic Data Collection

Research and planning documents for collecting Australian traffic events, incidents, and breakdowns data to overlay with CompassIoT vehicle trajectory data.

**Target window**: 1 March – 1 April 2026
**Coverage**: Sydney (NSW), Melbourne (VIC), Brisbane (QLD)

## Documents

| File | Description |
|------|-------------|
| [traffic-incident-data-collection.md](./traffic-incident-data-collection.md) | Master reference — all data sources, APIs, costs, architecture, timeline |
| [investigation-findings.md](./investigation-findings.md) | API investigation results — what's recoverable for March 2026 and what's not |
| [api-data-reference.md](./api-data-reference.md) | Actual data formats, sample payloads, and field descriptions for each API |
| [licensing-analysis.md](./licensing-analysis.md) | Legal analysis — CC-BY 4.0 permits commercial AI training, per-source verdict |
| [vicroads-email-draft.md](./vicroads-email-draft.md) | Ready-to-send emails for VicRoads (API token + data request) and TMR Queensland |

## Key Findings

- **NSW**: March 2026 data IS recoverable via TfNSW Historical API + jxeeno GitHub archive
- **QLD**: March 2026 data is NOT available from public APIs — contact TMR directly
- **VIC**: March 2026 data is NOT available from public APIs — contact VicRoads directly
- **TomTom/HERE**: Confirmed real-time only — no historical incident records exist as a product

## Immediate Actions

1. Register for TfNSW API key and run Historical API backfill (data expires ~June 2026)
2. Send VicRoads and TMR Queensland emails requesting March 2026 data extracts
3. Clone jxeeno/nsw-livetraffic-historical as backup NSW source
4. Set up 5-minute polling scraper for future data collection
