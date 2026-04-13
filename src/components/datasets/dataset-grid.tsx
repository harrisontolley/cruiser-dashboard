"use client";

import { Dataset, DatasetFilter, DatasetCategory } from "@/lib/data/types";
import { DatasetFilters } from "./dataset-filters";
import { DatasetCard } from "./dataset-card";
import { AnimatedCard } from "@/components/motion/animated-container";

interface DatasetGridProps {
  datasets: Dataset[];
  filter: DatasetFilter;
  totalCount: number;
  setSearch: (s: string) => void;
  setCategories: (c: DatasetCategory[]) => void;
  setSortBy: (s: DatasetFilter["sortBy"]) => void;
  toggleSortOrder: () => void;
  getSiblings: (d: Dataset) => Dataset[];
  onCardClick: (d: Dataset) => void;
}

export function DatasetGrid({
  datasets,
  filter,
  totalCount,
  setSearch,
  setCategories,
  setSortBy,
  toggleSortOrder,
  getSiblings,
  onCardClick,
}: DatasetGridProps) {
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
              <DatasetCard
                dataset={dataset}
                siblings={getSiblings(dataset)}
                onClick={() => onCardClick(dataset)}
              />
            </AnimatedCard>
          ))}
        </div>
      )}
    </div>
  );
}
