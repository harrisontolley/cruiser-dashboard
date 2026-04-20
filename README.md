# cruiser-dashboard

Monorepo for the DataCruiser project — a Next.js data-catalogue dashboard backed by S3,
plus the data pipelines that populate it.

## Layout

| Folder | What's in it |
|--------|--------------|
| [`dashboard/`](./dashboard) | Next.js 16 dashboard (App Router, Tailwind v4, shadcn). `cd dashboard && npm install && npm run dev`. |
| [`overture-pipeline/`](./overture-pipeline) | Python pipeline that extracts Overture Maps layers for a city and uploads the outputs to S3. `cd overture-pipeline && ./run-pipeline.sh sydney 5750005 --hex-agg`. |
| [`accident-data-collection/`](./accident-data-collection) | Research + plans for acquiring Australian traffic events / incidents / breakdowns data to overlay on CompassIoT trajectories. Currently markdown only — see its [README](./accident-data-collection/README.md). |

## Per-folder workflows

Each subfolder is self-contained. Open a terminal in the folder you're working in —
commands, dependencies, and virtualenvs are all scoped locally.

- **Dashboard dev loop**: `cd dashboard && npm run dev` → http://localhost:3000
- **Dashboard metadata refresh** (after uploading a new dataset to S3): `cd dashboard && npm run scrape`
- **Overture pipeline (fresh machine)**: `cd overture-pipeline && ./ec2-setup.sh` then `./run-pipeline.sh <city> <relation-id>`
- **Accident data collection**: `accident-data-collection/README.md` has the current plan and action items.
