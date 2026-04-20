"use client";

import { useState, useMemo } from "react";
import dynamic from "next/dynamic";
import { Dataset, ALL_CATEGORIES, CATEGORY_BG_CLASSES } from "@/lib/data/types";
import { Badge } from "@/components/ui/badge";

const MapInner = dynamic(() => import("./coverage-map-inner"), { ssr: false });

interface CoverageMapProps {
  datasets: Dataset[];
  onDatasetClick?: (dataset: Dataset) => void;
}

export function CoverageMap({ datasets, onDatasetClick }: CoverageMapProps) {
  const withBbox = useMemo(() => datasets.filter((d) => d.bbox), [datasets]);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const activeCategories = useMemo(
    () => [...new Set(withBbox.map((d) => d.category))],
    [withBbox]
  );

  return (
    <div className="relative rounded-xl overflow-hidden ring-1 ring-white/[0.06] map-glow coord-graticule">
      {/* Top bar */}
      <div className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-5 py-3 bg-gradient-to-b from-background/80 via-background/40 to-transparent backdrop-blur-sm">
        <div className="flex items-center gap-2.5">
          <div className="h-1.5 w-1.5 rounded-full bg-primary pulse-dot" />
          <span className="text-sm font-medium text-foreground font-display">
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
      <div className="h-[420px] radar-sweep">
        <MapInner
          datasets={withBbox}
          hoveredId={hoveredId}
          onHover={setHoveredId}
          onClick={onDatasetClick ?? (() => {})}
        />
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-background/60 to-transparent pointer-events-none z-10" />

      {/* Subtle top glow line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent z-20" />
    </div>
  );
}
