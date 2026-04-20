"use client";

import { Dataset, ALL_CATEGORIES, CATEGORY_BG_CLASSES, CATEGORY_COLORS } from "@/lib/data/types";
import { formatBytes, formatNumber, formatTimespan, daysSince, cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { BboxMiniMap } from "./bbox-mini-map";
import { useCopyToClipboard } from "@/hooks/use-copy-to-clipboard";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Car,
  Navigation,
  Route,
  Satellite,
  Zap,
  Cloud,
  UsersRound,
  ArrowLeftRight,
  Copy,
  Check,
  Clock,
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
  siblings?: Dataset[];
  onClick: () => void;
}

export function DatasetCard({ dataset, siblings = [], onClick }: DatasetCardProps) {
  const categoryLabel =
    ALL_CATEGORIES.find((c) => c.value === dataset.category)?.label ??
    dataset.category;
  const color = CATEGORY_COLORS[dataset.category];
  const age = daysSince(dataset.lastModified);
  const recency: "fresh" | "stale" | null =
    age <= 30 ? "fresh" : age > 180 ? "stale" : null;
  const timespanLabel = formatTimespan(dataset);
  const hasTimespan = timespanLabel !== "—";
  const tags = dataset.tags ?? [];
  const visibleTags = tags.slice(0, 3);
  const hiddenTagCount = Math.max(0, tags.length - visibleTags.length);

  const hasPair = Boolean(dataset.pairId && siblings.length > 0);
  const { copied, copy } = useCopyToClipboard();

  const handleCopyS3 = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (dataset.s3Url) copy(dataset.s3Url);
  };

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

      {/* Top-right: bbox mini-map + hover copy-s3 */}
      <div className="absolute right-4 top-4 flex items-center gap-1.5">
        {dataset.s3Url && (
          <Tooltip>
            <TooltipTrigger
              render={
                <span
                  role="button"
                  tabIndex={-1}
                  aria-label="Copy S3 path"
                  onClick={handleCopyS3}
                  className={cn(
                    "flex h-6 w-6 items-center justify-center rounded-md bg-card/90 ring-1 ring-white/[0.1] backdrop-blur-sm",
                    "text-muted-foreground hover:text-foreground hover:bg-white/[0.05]",
                    "opacity-0 group-hover:opacity-100 transition-all duration-200 cursor-pointer"
                  )}
                />
              }
            >
              {copied ? (
                <Check className="h-3 w-3 text-emerald-400" />
              ) : (
                <Copy className="h-3 w-3" />
              )}
            </TooltipTrigger>
            <TooltipContent className="text-xs">
              {copied ? "Copied!" : "Copy S3 path"}
            </TooltipContent>
          </Tooltip>
        )}
        {dataset.bbox && (
          <Tooltip>
            <TooltipTrigger
              render={
                <span className="block rounded-md p-0.5 ring-1 ring-white/[0.06] bg-background/40">
                  <BboxMiniMap bbox={dataset.bbox} color={color} width={40} height={26} />
                </span>
              }
            />
            <TooltipContent className="text-xs">
              Coverage bbox within Australia
            </TooltipContent>
          </Tooltip>
        )}
      </div>

      {/* Badges row */}
      <div className="flex flex-wrap items-center gap-1.5 mb-3 pr-20">
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
        {hasPair && (
          <Tooltip>
            <TooltipTrigger
              render={
                <Badge
                  variant="outline"
                  className="shrink-0 text-[10px] uppercase tracking-wider border px-1.5 py-0 h-5 gap-1 bg-primary/10 text-primary border-primary/25"
                >
                  <ArrowLeftRight className="h-2.5 w-2.5" />
                  Pair
                </Badge>
              }
            />
            <TooltipContent className="text-xs max-w-[240px]">
              <div className="font-medium mb-1">Paired with:</div>
              <ul className="space-y-0.5">
                {siblings.map((s) => (
                  <li key={s.id} className="text-muted-foreground">
                    <span className="font-mono uppercase tracking-wider text-[10px]">
                      {s.stage === "raw" ? "RAW" : "PROC"}
                    </span>{" "}
                    {s.name}
                  </li>
                ))}
              </ul>
            </TooltipContent>
          </Tooltip>
        )}
        {recency === "fresh" && (
          <Badge
            variant="outline"
            className="shrink-0 text-[10px] uppercase tracking-wider border px-1.5 py-0 h-5 bg-emerald-500/10 text-emerald-400/90 border-emerald-500/25"
          >
            Fresh
          </Badge>
        )}
        {recency === "stale" && (
          <Badge
            variant="outline"
            className="shrink-0 text-[10px] uppercase tracking-wider border px-1.5 py-0 h-5 bg-white/[0.03] text-muted-foreground border-white/[0.08]"
          >
            Stale
          </Badge>
        )}
      </div>

      {/* Name */}
      <h3 className="text-sm font-medium text-foreground mb-1 line-clamp-1 pr-20">
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

      {/* Stats row: Size | Files | Format */}
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
            Files
          </div>
          <div className="font-mono text-xs text-foreground tabular-nums">
            {dataset.fileCount != null ? formatNumber(dataset.fileCount) : "—"}
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

      {/* Optional timespan ghost row */}
      {hasTimespan && (
        <div className="mt-3 flex items-center gap-1.5 text-[11px] text-muted-foreground font-mono">
          <Clock className="h-3 w-3" />
          <span className="tabular-nums">{timespanLabel}</span>
        </div>
      )}

      {/* Tag strip + maintainer */}
      {(visibleTags.length > 0 || dataset.maintainer) && (
        <div className="mt-3 pt-2.5 border-t border-white/[0.03] flex items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1 min-w-0">
            {visibleTags.map((tag) => (
              <span
                key={tag}
                className="font-mono text-[10px] text-muted-foreground bg-white/[0.03] px-1.5 py-0.5 rounded"
              >
                {tag}
              </span>
            ))}
            {hiddenTagCount > 0 && (
              <span className="font-mono text-[10px] text-muted-foreground/70">
                +{hiddenTagCount}
              </span>
            )}
          </div>
          {dataset.maintainer && (
            <span className="text-[11px] text-muted-foreground shrink-0">
              @{dataset.maintainer}
            </span>
          )}
        </div>
      )}
    </button>
  );
}
