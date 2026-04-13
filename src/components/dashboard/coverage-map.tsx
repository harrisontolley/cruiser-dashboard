"use client";

import { useState, useMemo } from "react";
import dynamic from "next/dynamic";
import { Dataset, ALL_CATEGORIES, CATEGORY_BG_CLASSES } from "@/lib/data/types";
import { Badge } from "@/components/ui/badge";
import { DatasetDetailSheet } from "@/components/datasets/dataset-detail-sheet";

const MapInner = dynamic(() => import("./coverage-map-inner"), { ssr: false });

export function CoverageMap({ datasets }: { datasets: Dataset[] }) {
  const withBbox = useMemo(() => datasets.filter((d) => d.bbox), [datasets]);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const activeCategories = useMemo(
    () => [...new Set(withBbox.map((d) => d.category))],
    [withBbox]
  );

  const handleClick = (dataset: Dataset) => {
    setSelectedDataset(dataset);
    setSheetOpen(true);
  };

  return (
    <>
      <div className="relative rounded-xl overflow-hidden ring-1 ring-white/[0.06] map-glow">
        {/* Top bar */}
        <div className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-5 py-3 bg-gradient-to-b from-background/80 via-background/40 to-transparent backdrop-blur-sm">
          <div className="flex items-center gap-2.5">
            <div className="h-1.5 w-1.5 rounded-full bg-primary pulse-dot" />
            <span className="text-sm font-medium text-foreground">
              Coverage Map
            </span>
            <span className="text-xs font-mono text-muted-foreground">
              {withBbox.length} datasets
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {ALL_CATEGORIES.filter((c) => activeCategories.includes(c.value)).map((c) => (
              <Badge
                key={c.value}
                variant="outline"
                className={`text-[11px] border px-1.5 py-0 h-5 ${CATEGORY_BG_CLASSES[c.value]}`}
              >
                {c.label}
              </Badge>
            ))}
          </div>
        </div>

        {/* Map */}
        <div className="h-[420px] scan-line">
          <MapInner
            datasets={withBbox}
            hoveredId={hoveredId}
            onHover={setHoveredId}
            onClick={handleClick}
          />
        </div>

        {/* Bottom gradient fade */}
        <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-background/60 to-transparent pointer-events-none z-10" />

        {/* Subtle top glow line */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent z-20" />
      </div>

      <DatasetDetailSheet
        dataset={selectedDataset}
        open={sheetOpen}
        onOpenChange={setSheetOpen}
      />
    </>
  );
}
