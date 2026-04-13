import { Dataset, DatasetCategory, BucketStats, CATEGORY_COLORS } from "./types";

export const datasets: Dataset[] = [
  {
    id: "tfnsw",
    name: "TfNSW",
    category: "traffic",
    region: "NSW, Australia",
    stage: "raw",
    description:
      "Transport for NSW traffic volume and speed data across the state road network. Includes sensor counts, average speeds, and flow rates.",
    sizeBytes: 4_820_000_000,
    fileCount: 342,
    format: "Parquet",
    lastModified: "2025-03-15T10:00:00Z",
    bbox: [149.0, -37.5, 154.0, -28.0],
    maintainer: "Du Yin",
    s3Url: "s3://datacruiser-stdb/raw/traffic/tfnsw/",
    tags: ["traffic", "sensors", "speed", "volume"],
  },
  {
    id: "pems",
    name: "PeMS",
    category: "traffic",
    region: "LA, USA",
    stage: "raw",
    description:
      "Caltrans Performance Measurement System. Freeway performance data including flow, occupancy, and speed from loop detectors across Los Angeles.",
    sizeBytes: 8_150_000_000,
    fileCount: 1_205,
    format: "CSV",
    lastModified: "2025-02-28T08:00:00Z",
    bbox: [-119.0, 33.0, -117.0, 35.0],
    tags: ["traffic", "freeway", "loop-detectors", "flow"],
  },
  {
    id: "satellite-embeddings-sydney",
    name: "Overture + Satellite Embeddings H3 Res 8+9",
    category: "satellite",
    region: "Sydney",
    stage: "processed",
    timespan: "Overture — Feb 18th Snapshot. Satellite Embeddings — 2025",
    temporalRange: { start: "2025-02-18", end: null },
    license: "Alpha Earth — CC BY 4.0 (non-commercial download, register for commercial)",
    sourceUrl:
      "https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL#terms-of-use",
    description:
      "Google Alpha Earth satellite embedding vectors at H3 resolution 8 and 9, joined with Overture Maps Foundation data for Sydney. Captures land use, built environment, and vegetation patterns.",
    sizeBytes: 12_400_000_000,
    fileCount: 48,
    format: "Parquet",
    lastModified: "2025-03-01T12:00:00Z",
    bbox: [150.5, -34.2, 151.5, -33.5],
    maintainer: "Harry Tolley",
    s3Url: "s3://datacruiser-stdb/raw/satellite/overture-embeddings-sydney/",
    tags: ["satellite", "embeddings", "h3", "overture", "alpha-earth"],
  },
  {
    id: "satellite-embeddings-melbourne",
    name: "Overture + Satellite Embeddings H3 Res 8+9",
    category: "satellite",
    region: "Melbourne",
    stage: "processed",
    timespan: "Overture — Feb 18th Snapshot. Satellite Embeddings — 2025",
    temporalRange: { start: "2025-02-18", end: null },
    license: "Alpha Earth — CC BY 4.0 (non-commercial download, register for commercial)",
    sourceUrl:
      "https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL#terms-of-use",
    description:
      "Google Alpha Earth satellite embedding vectors at H3 resolution 8 and 9, joined with Overture Maps Foundation data for Melbourne. Captures land use, built environment, and vegetation patterns.",
    sizeBytes: 10_800_000_000,
    fileCount: 42,
    format: "Parquet",
    lastModified: "2025-03-01T12:00:00Z",
    bbox: [144.5, -38.2, 145.5, -37.5],
    maintainer: "Harry Tolley",
    s3Url: "s3://datacruiser-stdb/raw/satellite/overture-embeddings-melbourne/",
    tags: ["satellite", "embeddings", "h3", "overture", "alpha-earth"],
  },
  {
    id: "pricefm",
    name: "PriceFM",
    category: "energy",
    region: "24 European Countries (38 sub-regions)",
    stage: "raw",
    timespan: "2022-01-01 to 2026-01-01",
    temporalRange: { start: "2022-01-01", end: "2026-01-01" },
    license: "License not specified",
    sourceUrl:
      "https://openreview.net/attachment?id=t0fsGqGVVL&name=supplementary_material",
    description:
      "Energy demand and price forecasting dataset covering 24 European countries across 38 sub-regions. Includes day-ahead electricity prices, demand, and generation mix data.",
    sizeBytes: 2_340_000_000,
    fileCount: 76,
    format: "Parquet",
    lastModified: "2025-01-20T16:00:00Z",
    bbox: [-10.0, 35.0, 30.0, 72.0],
    maintainer: "Wilson Wongso",
    s3Url: "s3://datacruiser-stdb/raw/energy/pricefm/",
    tags: ["energy", "electricity", "prices", "demand", "european"],
  },
  {
    id: "barra-c2",
    name: "BARRA-C2",
    category: "weather",
    region: "Australia-wide",
    stage: "raw",
    timespan: "1970–2025 (exported 2020–2025)",
    temporalRange: { start: "2020-01-01", end: "2025-12-31" },
    license: "CC License",
    sourceUrl:
      "https://geonetwork.nci.org.au/geonetwork/srv/eng/catalog.search#/metadata/f9057_2475_0540_0329",
    description:
      "Bureau of Meteorology BARRA-C2 atmospheric high-resolution regional reanalysis for Australia. Convection-permitting (~2.2km) hindcast including temperature, wind, precipitation, humidity, and pressure fields.",
    sizeBytes: 48_500_000_000,
    fileCount: 2_190,
    format: "NetCDF",
    lastModified: "2025-03-10T06:00:00Z",
    bbox: [112.0, -44.0, 154.0, -10.0],
    maintainer: "Utkarsh Sharma",
    s3Url: "s3://datacruiser-stdb/raw/weather/barra-c2/",
    tags: ["weather", "reanalysis", "bom", "temperature", "precipitation", "wind"],
  },
];

// --- Accessor functions ---

export function getDatasets(): Dataset[] {
  return datasets;
}

export function getDatasetById(id: string): Dataset | undefined {
  return datasets.find((d) => d.id === id);
}

export function getBucketStats(): BucketStats {
  const totalSizeBytes = datasets.reduce((sum, d) => sum + d.sizeBytes, 0);
  const fileCountTotal = datasets.reduce((sum, d) => sum + (d.fileCount ?? 0), 0);
  const categories = new Set(datasets.map((d) => d.category));
  const regions = new Set(datasets.map((d) => d.region));
  const maintainers = new Set(datasets.filter((d) => d.maintainer).map((d) => d.maintainer));
  const sorted = [...datasets].sort(
    (a, b) => new Date(b.lastModified).getTime() - new Date(a.lastModified).getTime()
  );
  const processedPairIds = new Set(
    datasets.filter((d) => d.stage === "processed" && d.pairId).map((d) => d.pairId!)
  );
  const rawWithPairId = datasets.filter((d) => d.stage === "raw" && d.pairId);
  const rawWithProcessed = rawWithPairId.filter((d) => processedPairIds.has(d.pairId!)).length;
  return {
    totalSizeBytes,
    datasetCount: datasets.length,
    categoryCount: categories.size,
    regionCount: regions.size,
    maintainerCount: maintainers.size,
    lastUpdated: sorted[0]?.lastModified ?? new Date().toISOString(),
    fileCountTotal,
    pairCoverage: {
      rawWithProcessed,
      rawTotal: rawWithPairId.length,
    },
  };
}

export function getDatasetsByCategory(): Record<DatasetCategory, Dataset[]> {
  const grouped: Record<string, Dataset[]> = {};
  for (const d of datasets) {
    if (!grouped[d.category]) grouped[d.category] = [];
    grouped[d.category].push(d);
  }
  return grouped as Record<DatasetCategory, Dataset[]>;
}

export function getCategoryStats(): {
  category: DatasetCategory;
  label: string;
  count: number;
  sizeBytes: number;
  color: string;
}[] {
  const allCategories: { value: DatasetCategory; label: string }[] = [
    { value: "traffic", label: "Traffic" },
    { value: "eta", label: "ETA" },
    { value: "gps-trajectory", label: "GPS & Trajectory" },
    { value: "satellite", label: "Satellite" },
    { value: "energy", label: "Energy" },
    { value: "weather", label: "Weather" },
    { value: "demographics", label: "Demographics" },
  ];

  return allCategories.map(({ value, label }) => {
    const matching = datasets.filter((d) => d.category === value);
    return {
      category: value,
      label,
      count: matching.length,
      sizeBytes: matching.reduce((sum, d) => sum + d.sizeBytes, 0),
      color: CATEGORY_COLORS[value],
    };
  });
}

export function getRegionStats(): { region: string; count: number; sizeBytes: number }[] {
  const regionMap = new Map<string, { count: number; sizeBytes: number }>();
  for (const d of datasets) {
    const existing = regionMap.get(d.region) || { count: 0, sizeBytes: 0 };
    regionMap.set(d.region, {
      count: existing.count + 1,
      sizeBytes: existing.sizeBytes + d.sizeBytes,
    });
  }
  return Array.from(regionMap.entries())
    .sort(([, a], [, b]) => b.sizeBytes - a.sizeBytes)
    .map(([region, data]) => ({ region, ...data }));
}

export function getGrowthData(): {
  date: string;
  totalBytes: number;
  datasetName: string;
  category: DatasetCategory;
  sizeBytes: number;
}[] {
  const sorted = [...datasets].sort(
    (a, b) => new Date(a.lastModified).getTime() - new Date(b.lastModified).getTime()
  );

  // Anchor point one month before the first dataset
  const firstDate = new Date(sorted[0].lastModified);
  const anchor = new Date(firstDate);
  anchor.setMonth(anchor.getMonth() - 1);

  const points: {
    date: string;
    totalBytes: number;
    datasetName: string;
    category: DatasetCategory;
    sizeBytes: number;
  }[] = [
    {
      date: anchor.toISOString(),
      totalBytes: 0,
      datasetName: "",
      category: "traffic" as DatasetCategory,
      sizeBytes: 0,
    },
  ];

  let cumulative = 0;
  for (const d of sorted) {
    cumulative += d.sizeBytes;
    points.push({
      date: d.lastModified,
      totalBytes: cumulative,
      datasetName: d.name,
      category: d.category,
      sizeBytes: d.sizeBytes,
    });
  }

  return points;
}

export function getTimelineData(): {
  id: string;
  name: string;
  category: DatasetCategory;
  region: string;
  start: number;
  end: number;
  color: string;
}[] {
  return datasets
    .filter((d) => d.temporalRange)
    .map((d) => ({
      id: d.id,
      name: d.name,
      category: d.category,
      region: d.region,
      start: new Date(d.temporalRange!.start).getTime(),
      end: d.temporalRange!.end
        ? new Date(d.temporalRange!.end).getTime()
        : Date.now(),
      color: CATEGORY_COLORS[d.category],
    }));
}
