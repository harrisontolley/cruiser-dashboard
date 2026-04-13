"use client";

import { Search, ArrowUpDown } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DatasetCategory,
  DatasetFilter,
  ALL_CATEGORIES,
  CATEGORY_BG_CLASSES,
} from "@/lib/data/types";

interface DatasetFiltersProps {
  filter: DatasetFilter;
  onSearchChange: (search: string) => void;
  onCategoriesChange: (categories: DatasetCategory[]) => void;
  onSortByChange: (sortBy: DatasetFilter["sortBy"]) => void;
  onToggleSortOrder: () => void;
  resultCount: number;
  totalCount: number;
}

export function DatasetFilters({
  filter,
  onSearchChange,
  onCategoriesChange,
  onSortByChange,
  onToggleSortOrder,
  resultCount,
  totalCount,
}: DatasetFiltersProps) {
  const toggleCategory = (cat: DatasetCategory) => {
    if (filter.categories.includes(cat)) {
      onCategoriesChange(filter.categories.filter((c) => c !== cat));
    } else {
      onCategoriesChange([...filter.categories, cat]);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search datasets, regions, maintainers..."
            value={filter.search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-9 h-9 bg-card ring-1 ring-white/[0.06] border-0 text-sm placeholder:text-muted-foreground"
          />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground font-mono tabular-nums">
            {resultCount}/{totalCount}
          </span>
          <select
            value={filter.sortBy}
            onChange={(e) =>
              onSortByChange(e.target.value as DatasetFilter["sortBy"])
            }
            className="h-8 rounded-lg ring-1 ring-white/[0.06] bg-card border-0 px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/30"
          >
            <option value="date">Date</option>
            <option value="name">Name</option>
            <option value="size">Size</option>
            <option value="region">Region</option>
          </select>
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleSortOrder}
            className="h-8 w-8 rounded-lg"
          >
            <ArrowUpDown className="h-3 w-3 text-muted-foreground" />
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {ALL_CATEGORIES.map((cat) => {
          const isActive = filter.categories.includes(cat.value);
          return (
            <Badge
              key={cat.value}
              variant="outline"
              className={`cursor-pointer select-none text-xs px-2 py-0.5 transition-all duration-200 ${
                isActive
                  ? `${CATEGORY_BG_CLASSES[cat.value]} border`
                  : "text-muted-foreground border-white/[0.04] hover:border-white/[0.1] hover:text-muted-foreground"
              }`}
              onClick={() => toggleCategory(cat.value)}
            >
              {cat.label}
            </Badge>
          );
        })}
        {filter.categories.length > 0 && (
          <Badge
            variant="outline"
            className="cursor-pointer select-none text-xs text-muted-foreground border-white/[0.04] hover:text-muted-foreground transition-colors"
            onClick={() => onCategoriesChange([])}
          >
            Clear
          </Badge>
        )}
      </div>
    </div>
  );
}
