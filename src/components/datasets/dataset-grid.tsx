"use client";

import { useState } from "react";
import { Dataset } from "@/lib/data/types";
import { useDatasets } from "@/hooks/use-datasets";
import { DatasetFilters } from "./dataset-filters";
import { DatasetCard } from "./dataset-card";
import { DatasetDetailSheet } from "./dataset-detail-sheet";
import { AnimatedCard } from "@/components/motion/animated-container";

export function DatasetGrid({ datasets: allDatasets }: { datasets: Dataset[] }) {
  const {
    datasets,
    filter,
    setSearch,
    setCategories,
    setSortBy,
    toggleSortOrder,
    totalCount,
  } = useDatasets(allDatasets);

  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const handleCardClick = (dataset: Dataset) => {
    setSelectedDataset(dataset);
    setSheetOpen(true);
  };

  return (
    <div className="space-y-6">
      <DatasetFilters
        filter={filter}
        onSearchChange={setSearch}
        onCategoriesChange={setCategories}
        onSortByChange={setSortBy}
        onToggleSortOrder={toggleSortOrder}
        resultCount={datasets.length}
        totalCount={totalCount}
      />

      {datasets.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-16">
          <p className="text-sm text-muted-foreground">No datasets match your filters</p>
          <button
            onClick={() => {
              setSearch("");
              setCategories([]);
            }}
            className="mt-2 text-xs text-primary hover:underline"
          >
            Clear filters
          </button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {datasets.map((dataset, i) => (
            <AnimatedCard key={dataset.id} index={i}>
              <DatasetCard dataset={dataset} onClick={() => handleCardClick(dataset)} />
            </AnimatedCard>
          ))}
        </div>
      )}

      <DatasetDetailSheet
        dataset={selectedDataset}
        open={sheetOpen}
        onOpenChange={setSheetOpen}
      />
    </div>
  );
}
