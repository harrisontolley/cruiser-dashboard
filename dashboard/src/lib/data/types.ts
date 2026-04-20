export type DatasetCategory =
  | "traffic"
  | "eta"
  | "gps-trajectory"
  | "satellite"
  | "energy"
  | "weather"
  | "demographics";

export type ViewMode = "all" | "raw" | "processed";

export interface Dataset {
  id: string;
  name: string;
  category: DatasetCategory;
  region: string;
  stage: "raw" | "processed";
  pairId?: string;
  timespan?: string;
  temporalRange?: { start: string; end: string | null };
  license?: string;
  sourceUrl?: string;
  s3Url?: string;
  maintainer?: string;

  sizeBytes: number;
  fileCount?: number;
  format?: string;
  lastModified: string;

  bbox?: [number, number, number, number]; // [west, south, east, north]
  description?: string;
  tags?: string[];
}

export interface CategoryStatEntry {
  category: DatasetCategory;
  label: string;
  count: number;
  sizeBytes: number;
  color: string;
}

export interface RegionStatEntry {
  region: string;
  count: number;
  sizeBytes: number;
}

export interface GrowthEntry {
  date: string;
  totalBytes: number;
  datasetName: string;
  category: DatasetCategory;
  sizeBytes: number;
}

export interface BucketStats {
  totalSizeBytes: number;
  datasetCount: number;
  categoryCount: number;
  regionCount: number;
  maintainerCount: number;
  lastUpdated: string;
  fileCountTotal: number;
  pairCoverage: {
    rawWithProcessed: number;
    rawTotal: number;
  };
}

export interface DatasetFilter {
  search: string;
  categories: DatasetCategory[];
  sortBy: "name" | "size" | "date" | "region";
  sortOrder: "asc" | "desc";
}

export const ALL_CATEGORIES: { value: DatasetCategory; label: string }[] = [
  { value: "traffic", label: "Traffic" },
  { value: "eta", label: "ETA" },
  { value: "gps-trajectory", label: "GPS & Trajectory" },
  { value: "satellite", label: "Satellite" },
  { value: "energy", label: "Energy" },
  { value: "weather", label: "Weather" },
  { value: "demographics", label: "Demographics" },
];

export const CATEGORY_COLORS: Record<DatasetCategory, string> = {
  traffic: "oklch(0.72 0.17 165)",
  eta: "oklch(0.70 0.15 60)",
  "gps-trajectory": "oklch(0.65 0.18 30)",
  satellite: "oklch(0.68 0.18 290)",
  energy: "oklch(0.75 0.16 85)",
  weather: "oklch(0.72 0.15 230)",
  demographics: "oklch(0.68 0.14 340)",
};

export const CATEGORY_BG_CLASSES: Record<DatasetCategory, string> = {
  traffic: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  eta: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
  "gps-trajectory": "bg-orange-500/15 text-orange-400 border-orange-500/30",
  satellite: "bg-violet-500/15 text-violet-400 border-violet-500/30",
  energy: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  weather: "bg-sky-500/15 text-sky-400 border-sky-500/30",
  demographics: "bg-pink-500/15 text-pink-400 border-pink-500/30",
};
