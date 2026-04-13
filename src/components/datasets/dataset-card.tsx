"use client";

import { Dataset, ALL_CATEGORIES, CATEGORY_BG_CLASSES, CATEGORY_COLORS } from "@/lib/data/types";
import { formatBytes } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  Car,
  Navigation,
  Route,
  Satellite,
  Zap,
  Cloud,
  UsersRound,
  ExternalLink,
} from "lucide-react";

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  traffic: <Car className="h-3 w-3" />,
  eta: <Navigation className="h-3 w-3" />,
  "gps-trajectory": <Route className="h-3 w-3" />,
  satellite: <Satellite className="h-3 w-3" />,
  energy: <Zap className="h-3 w-3" />,
  weather: <Cloud className="h-3 w-3" />,
  demographics: <UsersRound className="h-3 w-3" />,
};

interface DatasetCardProps {
  dataset: Dataset;
  onClick: () => void;
}

export function DatasetCard({ dataset, onClick }: DatasetCardProps) {
  const categoryLabel =
    ALL_CATEGORIES.find((c) => c.value === dataset.category)?.label ??
    dataset.category;
  const color = CATEGORY_COLORS[dataset.category];

  return (
    <button
      onClick={onClick}
      className="group relative w-full overflow-hidden rounded-xl ring-1 ring-white/[0.06] bg-card p-5 text-left transition-all duration-300 hover:ring-white/[0.12] hover:bg-card/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {/* Top accent line */}
      <div
        className="absolute top-0 left-4 right-4 h-px opacity-0 group-hover:opacity-50 transition-opacity duration-300"
        style={{
          background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
        }}
      />

      {/* Category + source */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-1.5">
          <Badge
            variant="outline"
            className={`shrink-0 text-[11px] gap-1 border px-1.5 py-0 h-5 ${CATEGORY_BG_CLASSES[dataset.category]}`}
          >
            {CATEGORY_ICONS[dataset.category]}
            {categoryLabel}
          </Badge>
          <Badge
            variant="outline"
            className={`shrink-0 text-[10px] font-mono uppercase tracking-wider border px-1.5 py-0 h-5 ${
              dataset.stage === "raw"
                ? "bg-orange-500/15 text-orange-400 border-orange-500/30"
                : "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
            }`}
          >
            {dataset.stage === "raw" ? "RAW" : "PROC"}
          </Badge>
        </div>
        {dataset.sourceUrl && (
          <ExternalLink className="h-3 w-3 text-muted-foreground group-hover:text-muted-foreground transition-colors shrink-0" />
        )}
      </div>

      {/* Name */}
      <h3 className="text-sm font-medium text-foreground mb-1 line-clamp-1 group-hover:text-foreground transition-colors">
        {dataset.name}
      </h3>

      {/* Region */}
      <p className="text-xs text-muted-foreground mb-3">{dataset.region}</p>

      {/* Description */}
      {dataset.description && (
        <p className="mb-4 text-xs text-muted-foreground line-clamp-2 leading-relaxed">
          {dataset.description}
        </p>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3 border-t border-white/[0.04] pt-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground mb-0.5">
            Size
          </div>
          <div className="font-mono text-xs text-foreground tabular-nums">
            {formatBytes(dataset.sizeBytes)}
          </div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground mb-0.5">
            Timespan
          </div>
          <div className="font-mono text-xs text-foreground tabular-nums">
            {dataset.timespan ? dataset.timespan.split(" ")[0] : "—"}
          </div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground mb-0.5">
            Format
          </div>
          <div className="font-mono text-xs text-foreground tabular-nums">
            {dataset.format ?? "—"}
          </div>
        </div>
      </div>

      {/* Maintainer */}
      {dataset.maintainer && (
        <div className="mt-3 pt-2.5 border-t border-white/[0.03]">
          <span className="text-xs text-muted-foreground">
            @{dataset.maintainer}
          </span>
        </div>
      )}
    </button>
  );
}
