"use client";

import { useState, useMemo } from "react";
import {
  Dataset,
  BucketStats,
  CategoryStatEntry,
  RegionStatEntry,
  GrowthEntry,
  ViewMode,
} from "@/lib/data/types";
import {
  computeBucketStats,
  computeCategoryStats,
  computeRegionStats,
  computeGrowthData,
} from "@/lib/data/compute-stats";
import { Header } from "@/components/layout/header";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { CoverageMap } from "@/components/dashboard/coverage-map";
import { TemporalTimeline } from "@/components/dashboard/temporal-timeline";
import { CategoryChart } from "@/components/dashboard/category-chart";
import { RegionChart } from "@/components/dashboard/region-chart";
import { GrowthChart } from "@/components/dashboard/growth-chart";
import { ProcessingImpact } from "@/components/dashboard/processing-impact";
import { DatasetGrid } from "@/components/datasets/dataset-grid";
import { AnimatedSection } from "@/components/motion/animated-container";

interface DashboardShellProps {
  allDatasets: Dataset[];
  allBucketStats: BucketStats;
  allCategoryStats: CategoryStatEntry[];
  allRegionStats: RegionStatEntry[];
  allGrowthData: GrowthEntry[];
}

export function DashboardShell({
  allDatasets,
  allBucketStats,
  allCategoryStats,
  allRegionStats,
  allGrowthData,
}: DashboardShellProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("all");

  const filteredDatasets = useMemo(() => {
    if (viewMode === "all") return allDatasets;
    return allDatasets.filter((d) => d.stage === viewMode);
  }, [allDatasets, viewMode]);

  const bucketStats = useMemo(
    () => (viewMode === "all" ? allBucketStats : computeBucketStats(filteredDatasets)),
    [viewMode, allBucketStats, filteredDatasets]
  );

  const categoryStats = useMemo(
    () => (viewMode === "all" ? allCategoryStats : computeCategoryStats(filteredDatasets)),
    [viewMode, allCategoryStats, filteredDatasets]
  );

  const regionStats = useMemo(
    () => (viewMode === "all" ? allRegionStats : computeRegionStats(filteredDatasets)),
    [viewMode, allRegionStats, filteredDatasets]
  );

  const growthData = useMemo(
    () => (viewMode === "all" ? allGrowthData : computeGrowthData(filteredDatasets)),
    [viewMode, allGrowthData, filteredDatasets]
  );

  return (
    <div className="flex min-h-screen flex-col">
      <Header
        datasetCount={filteredDatasets.length}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />
      <main className="flex-1">
        <div className="mx-auto max-w-[1400px] space-y-6 px-6 py-6">
          {/* Stats Overview */}
          <AnimatedSection delay={0}>
            <StatsCards stats={bucketStats} />
          </AnimatedSection>

          {/* Hero: Coverage Map */}
          <AnimatedSection delay={0.1}>
            <CoverageMap datasets={filteredDatasets} />
          </AnimatedSection>

          {/* Charts Row: Timeline + Category + Region */}
          <AnimatedSection delay={0.2}>
            <div className="grid gap-6 lg:grid-cols-2">
              <TemporalTimeline datasets={filteredDatasets} />
              <div className="grid gap-6">
                <CategoryChart data={categoryStats} />
                <RegionChart data={regionStats} />
              </div>
            </div>
          </AnimatedSection>

          {/* Storage Growth */}
          <AnimatedSection delay={0.25}>
            <GrowthChart data={growthData} />
          </AnimatedSection>

          {/* Processing Impact — always receives ALL datasets for comparison */}
          <AnimatedSection delay={0.3}>
            <ProcessingImpact datasets={allDatasets} />
          </AnimatedSection>

          {/* Dataset Listing */}
          <AnimatedSection delay={0.35}>
            <section>
              <div className="mb-5">
                <h2 className="text-sm font-semibold tracking-tight">All Datasets</h2>
                <p className="text-xs text-muted-foreground mt-1">
                  Click any dataset to view detailed information
                </p>
              </div>
              <DatasetGrid datasets={filteredDatasets} />
            </section>
          </AnimatedSection>
        </div>
      </main>
    </div>
  );
}
