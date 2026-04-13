// Real S3 metadata reader. All functions are async (return Promises).
// To revert to mock data, re-export from "@/lib/data/mock-datasets" instead.
export {
  getDatasets,
  getDatasetById,
  getBucketStats,
  getDatasetsByCategory,
  getCategoryStats,
  getRegionStats,
  getGrowthData,
  getTimelineData,
} from "./fetch-metadata";
