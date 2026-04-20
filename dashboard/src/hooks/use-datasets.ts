"use client";

import { useMemo, useState } from "react";
import { Dataset, DatasetCategory, DatasetFilter } from "@/lib/data/types";

const DEFAULT_FILTER: DatasetFilter = {
  search: "",
  categories: [],
  sortBy: "date",
  sortOrder: "desc",
};

export function useDatasets(allDatasets: Dataset[]) {
  const [filter, setFilter] = useState<DatasetFilter>(DEFAULT_FILTER);

  const filtered = useMemo(() => {
    let result = [...allDatasets];

    if (filter.search) {
      const q = filter.search.toLowerCase();
      result = result.filter(
        (d) =>
          d.name.toLowerCase().includes(q) ||
          d.description?.toLowerCase().includes(q) ||
          d.region.toLowerCase().includes(q) ||
          d.maintainer?.toLowerCase().includes(q) ||
          d.tags?.some((t) => t.toLowerCase().includes(q))
      );
    }

    if (filter.categories.length > 0) {
      result = result.filter((d) => filter.categories.includes(d.category));
    }

    result.sort((a, b) => {
      const dir = filter.sortOrder === "asc" ? 1 : -1;
      switch (filter.sortBy) {
        case "name":
          return dir * a.name.localeCompare(b.name);
        case "size":
          return dir * (a.sizeBytes - b.sizeBytes);
        case "date":
          return dir * (new Date(a.lastModified).getTime() - new Date(b.lastModified).getTime());
        case "region":
          return dir * a.region.localeCompare(b.region);
        default:
          return 0;
      }
    });

    return result;
  }, [allDatasets, filter]);

  const setSearch = (search: string) => setFilter((f) => ({ ...f, search }));
  const setCategories = (categories: DatasetCategory[]) =>
    setFilter((f) => ({ ...f, categories }));
  const setSortBy = (sortBy: DatasetFilter["sortBy"]) => setFilter((f) => ({ ...f, sortBy }));
  const toggleSortOrder = () =>
    setFilter((f) => ({ ...f, sortOrder: f.sortOrder === "asc" ? "desc" : "asc" }));

  return {
    datasets: filtered,
    filter,
    setSearch,
    setCategories,
    setSortBy,
    toggleSortOrder,
    totalCount: allDatasets.length,
  };
}
