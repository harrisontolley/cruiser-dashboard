"use client";

import { Dataset, CATEGORY_BG_CLASSES } from "@/lib/data/types";
import { formatBytes } from "@/lib/utils";
import { ArrowLeftRight, Layers, ArrowUpRight } from "lucide-react";

interface RelatedDatasetsProps {
  siblings: Dataset[];
  categorySiblings: Dataset[];
  onSelect: (dataset: Dataset) => void;
}

function RelatedRow({
  dataset,
  onSelect,
}: {
  dataset: Dataset;
  onSelect: (d: Dataset) => void;
}) {
  return (
    <button
      onClick={() => onSelect(dataset)}
      className="group flex w-full items-center justify-between gap-3 rounded-md border border-white/[0.04] bg-background/30 px-3 py-2 text-left transition-all hover:border-white/[0.12] hover:bg-white/[0.02]"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 mb-0.5">
          <span
            className={`font-mono text-[9px] uppercase tracking-wider rounded px-1 py-px ${
              dataset.stage === "raw"
                ? "bg-orange-500/15 text-orange-400"
                : "bg-emerald-500/15 text-emerald-400"
            }`}
          >
            {dataset.stage === "raw" ? "RAW" : "PROC"}
          </span>
          <span className={`text-[10px] px-1 py-px rounded ${CATEGORY_BG_CLASSES[dataset.category]}`}>
            {dataset.category}
          </span>
        </div>
        <div className="text-xs text-foreground truncate">{dataset.name}</div>
        <div className="text-[10px] text-muted-foreground font-mono tabular-nums">
          {formatBytes(dataset.sizeBytes)}
          {dataset.fileCount != null && ` · ${dataset.fileCount.toLocaleString()} files`}
        </div>
      </div>
      <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground group-hover:text-foreground transition-colors shrink-0" />
    </button>
  );
}

export function RelatedDatasets({
  siblings,
  categorySiblings,
  onSelect,
}: RelatedDatasetsProps) {
  const trimmedCategory = categorySiblings.slice(0, 3);
  if (siblings.length === 0 && trimmedCategory.length === 0) return null;

  return (
    <div className="space-y-4">
      {siblings.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-1.5">
            <ArrowLeftRight className="h-3 w-3 text-primary" />
            <span className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
              Pair siblings
            </span>
            <span className="text-[10px] text-muted-foreground/60 font-mono">
              ({siblings.length})
            </span>
          </div>
          <div className="space-y-1.5">
            {siblings.map((s) => (
              <RelatedRow key={s.id} dataset={s} onSelect={onSelect} />
            ))}
          </div>
        </div>
      )}

      {trimmedCategory.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-1.5">
            <Layers className="h-3 w-3 text-muted-foreground" />
            <span className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
              Same category
            </span>
            <span className="text-[10px] text-muted-foreground/60 font-mono">
              ({categorySiblings.length})
            </span>
          </div>
          <div className="space-y-1.5">
            {trimmedCategory.map((s) => (
              <RelatedRow key={s.id} dataset={s} onSelect={onSelect} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
