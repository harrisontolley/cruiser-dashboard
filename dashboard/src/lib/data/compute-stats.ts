import {
  Dataset,
  DatasetCategory,
  BucketStats,
  CategoryStatEntry,
  RegionStatEntry,
  GrowthEntry,
  CATEGORY_COLORS,
  ALL_CATEGORIES,
} from "./types";

export function computeBucketStats(datasets: Dataset[]): BucketStats {
  const totalSizeBytes = datasets.reduce((sum, d) => sum + d.sizeBytes, 0);
  const fileCountTotal = datasets.reduce((sum, d) => sum + (d.fileCount ?? 0), 0);
  const categories = new Set(datasets.map((d) => d.category));
  const regions = new Set(datasets.map((d) => d.region));
  const maintainers = new Set(
    datasets.filter((d) => d.maintainer).map((d) => d.maintainer)
  );
  const sorted = [...datasets].sort(
    (a, b) =>
      new Date(b.lastModified).getTime() - new Date(a.lastModified).getTime()
  );

  // Pair coverage: count raw datasets whose pairId has at least one processed sibling
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

export function computeCategoryStats(
  datasets: Dataset[]
): CategoryStatEntry[] {
  return ALL_CATEGORIES.map(({ value, label }) => {
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

export function computeRegionStats(datasets: Dataset[]): RegionStatEntry[] {
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

export function computeGrowthData(datasets: Dataset[]): GrowthEntry[] {
  const sorted = [...datasets].sort(
    (a, b) =>
      new Date(a.lastModified).getTime() - new Date(b.lastModified).getTime()
  );

  if (sorted.length === 0) return [];

  const firstDate = new Date(sorted[0].lastModified);
  const anchor = new Date(firstDate);
  anchor.setMonth(anchor.getMonth() - 1);

  const points: GrowthEntry[] = [
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
