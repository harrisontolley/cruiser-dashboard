import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import {
  getDatasets,
  getBucketStats,
  getCategoryStats,
  getRegionStats,
  getGrowthData,
} from "@/lib/s3/client";

export default async function DashboardPage() {
  const [datasets, bucketStats, categoryStats, regionStats, growthData] =
    await Promise.all([
      getDatasets(),
      getBucketStats(),
      getCategoryStats(),
      getRegionStats(),
      getGrowthData(),
    ]);

  return (
    <DashboardShell
      allDatasets={datasets}
      allBucketStats={bucketStats}
      allCategoryStats={categoryStats}
      allRegionStats={regionStats}
      allGrowthData={growthData}
    />
  );
}
