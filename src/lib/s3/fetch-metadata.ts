import "server-only";

import datasetsJson from "@/lib/data/datasets.json";
import {
  Dataset,
  DatasetCategory,
  BucketStats,
  CategoryStatEntry,
  RegionStatEntry,
  GrowthEntry,
  CATEGORY_COLORS,
} from "@/lib/data/types";
import {
  computeBucketStats,
  computeCategoryStats,
  computeRegionStats,
  computeGrowthData,
} from "@/lib/data/compute-stats";

const datasets = (datasetsJson as unknown as { datasets: Dataset[] }).datasets;

export async function getDatasets(): Promise<Dataset[]> {
  return datasets;
}

export async function getDatasetById(
  id: string
): Promise<Dataset | undefined> {
  return datasets.find((d) => d.id === id);
}

export async function getBucketStats(): Promise<BucketStats> {
  return computeBucketStats(datasets);
}

export async function getDatasetsByCategory(): Promise<
  Record<DatasetCategory, Dataset[]>
> {
  const grouped: Record<string, Dataset[]> = {};
  for (const d of datasets) {
    if (!grouped[d.category]) grouped[d.category] = [];
    grouped[d.category].push(d);
  }
  return grouped as Record<DatasetCategory, Dataset[]>;
}

export async function getCategoryStats(): Promise<CategoryStatEntry[]> {
  return computeCategoryStats(datasets);
}

export async function getRegionStats(): Promise<RegionStatEntry[]> {
  return computeRegionStats(datasets);
}

export async function getGrowthData(): Promise<GrowthEntry[]> {
  return computeGrowthData(datasets);
}

export async function getTimelineData(): Promise<
  {
    id: string;
    name: string;
    category: DatasetCategory;
    region: string;
    start: number;
    end: number;
    color: string;
  }[]
> {
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
