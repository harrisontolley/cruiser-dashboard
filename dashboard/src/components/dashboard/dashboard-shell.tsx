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
import { useDatasets } from "@/hooks/use-datasets";
import { Header } from "@/components/layout/header";
import { CommandPalette } from "@/components/layout/command-palette";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { CoverageMap } from "@/components/dashboard/coverage-map";
import { TemporalTimeline } from "@/components/dashboard/temporal-timeline";
import { CategoryChart } from "@/components/dashboard/category-chart";
import { RegionChart } from "@/components/dashboard/region-chart";
import { GrowthChart } from "@/components/dashboard/growth-chart";
import { ProcessingImpact } from "@/components/dashboard/processing-impact";
import { DatasetGrid } from "@/components/datasets/dataset-grid";
import { DatasetDetailSheet } from "@/components/datasets/dataset-detail-sheet";
import { AnimatedSection } from "@/components/motion/animated-container";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";

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
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [analyticsOpen, setAnalyticsOpen] = useState(true);

  const filteredByViewMode = useMemo(() => {
    if (viewMode === "all") return allDatasets;
    return allDatasets.filter((d) => d.stage === viewMode);
  }, [allDatasets, viewMode]);

  // Grid filter state now lives at shell level so command palette and
  // detail sheet (tag clicks) can drive it.
  const {
    datasets: gridDatasets,
    filter,
    setSearch,
    setCategories,
    setSortBy,
    toggleSortOrder,
    totalCount,
  } = useDatasets(filteredByViewMode);

  const bucketStats = useMemo(
    () => (viewMode === "all" ? allBucketStats : computeBucketStats(filteredByViewMode)),
    [viewMode, allBucketStats, filteredByViewMode]
  );

  const categoryStats = useMemo(
    () => (viewMode === "all" ? allCategoryStats : computeCategoryStats(filteredByViewMode)),
    [viewMode, allCategoryStats, filteredByViewMode]
  );

  const regionStats = useMemo(
    () => (viewMode === "all" ? allRegionStats : computeRegionStats(filteredByViewMode)),
    [viewMode, allRegionStats, filteredByViewMode]
  );

  const growthData = useMemo(
    () => (viewMode === "all" ? allGrowthData : computeGrowthData(filteredByViewMode)),
    [viewMode, allGrowthData, filteredByViewMode]
  );

  const siblingsByPair = useMemo(() => {
    const map = new Map<string, Dataset[]>();
    for (const d of allDatasets) {
      if (d.pairId) {
        if (!map.has(d.pairId)) map.set(d.pairId, []);
        map.get(d.pairId)!.push(d);
      }
    }
    return map;
  }, [allDatasets]);

  const getSiblings = (d: Dataset): Dataset[] => {
    if (!d.pairId) return [];
    return (siblingsByPair.get(d.pairId) ?? []).filter((s) => s.id !== d.id);
  };

  const categorySiblings = useMemo(() => {
    if (!selectedDataset) return [];
    return allDatasets.filter(
      (d) => d.category === selectedDataset.category && d.id !== selectedDataset.id
    );
  }, [selectedDataset, allDatasets]);

  const handleCardClick = (dataset: Dataset) => {
    setSelectedDataset(dataset);
    setSheetOpen(true);
  };

  const handleTagClick = (tag: string) => {
    setSearch(tag);
    setCategories([]);
    setSheetOpen(false);
    window.setTimeout(() => {
      document
        .getElementById("section-grid")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 250);
  };

  const handleRelatedClick = (dataset: Dataset) => {
    setSelectedDataset(dataset);
  };

  return (
    <div className="flex min-h-screen flex-col">
      <Header
        datasetCount={filteredByViewMode.length}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onCommandOpen={() => setCommandOpen(true)}
      />
      <main className="flex-1">
        <div className="mx-auto max-w-[1400px] space-y-6 px-6 py-6">
          {/* Stats Overview */}
          <AnimatedSection delay={0}>
            <section id="section-stats" aria-label="Stats overview">
              <StatsCards stats={bucketStats} />
            </section>
          </AnimatedSection>

          {/* Hero: Coverage Map */}
          <AnimatedSection delay={0.1}>
            <section id="section-map" aria-label="Coverage map">
              <CoverageMap
                datasets={filteredByViewMode}
                onDatasetClick={handleCardClick}
              />
            </section>
          </AnimatedSection>

          {/* Dataset Listing (moved up for internal users) */}
          <AnimatedSection delay={0.15}>
            <section id="section-grid" aria-label="All datasets">
              <div className="mb-5">
                <h2 className="text-sm font-semibold tracking-tight font-display">
                  All Datasets
                </h2>
                <p className="text-xs text-muted-foreground mt-1">
                  Search, filter, and open any dataset for full details
                </p>
              </div>
              <DatasetGrid
                datasets={gridDatasets}
                filter={filter}
                totalCount={totalCount}
                setSearch={setSearch}
                setCategories={setCategories}
                setSortBy={setSortBy}
                toggleSortOrder={toggleSortOrder}
                getSiblings={getSiblings}
                onCardClick={handleCardClick}
              />
            </section>
          </AnimatedSection>

          {/* Analytics — collapsible */}
          <AnimatedSection delay={0.25}>
            <section id="section-analytics" aria-label="Analytics">
              <button
                onClick={() => setAnalyticsOpen((v) => !v)}
                className="w-full flex items-center justify-between gap-3 rounded-xl bg-card/60 ring-1 ring-white/[0.06] px-5 py-3 hover:ring-white/[0.1] transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="h-7 w-px bg-primary/40" />
                  <div className="text-left">
                    <h2 className="text-sm font-semibold tracking-tight font-display">
                      Analytics
                    </h2>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      Timeline, category mix, region breakdown, storage growth, processing impact
                    </p>
                  </div>
                </div>
                <motion.div
                  animate={{ rotate: analyticsOpen ? 180 : 0 }}
                  transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                >
                  <ChevronDown className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                </motion.div>
              </button>

              <AnimatePresence initial={false}>
                {analyticsOpen && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                    className="overflow-hidden"
                  >
                    <div className="pt-6 space-y-6">
                      <div className="grid gap-6 lg:grid-cols-2">
                        <TemporalTimeline datasets={filteredByViewMode} />
                        <div className="grid gap-6">
                          <CategoryChart data={categoryStats} />
                          <RegionChart data={regionStats} />
                        </div>
                      </div>
                      <GrowthChart data={growthData} />
                      <ProcessingImpact datasets={allDatasets} />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </section>
          </AnimatedSection>
        </div>
      </main>

      {/* Detail sheet — shell-owned so palette, cards, and related-clicks can drive it */}
      <DatasetDetailSheet
        dataset={selectedDataset}
        siblings={selectedDataset ? getSiblings(selectedDataset) : []}
        categorySiblings={categorySiblings}
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        onTagClick={handleTagClick}
        onRelatedClick={handleRelatedClick}
      />

      {/* Command palette — global */}
      <CommandPalette
        open={commandOpen}
        setOpen={setCommandOpen}
        datasets={allDatasets}
        onDatasetSelect={handleCardClick}
      />
    </div>
  );
}
