"use client";

import { Dataset, ALL_CATEGORIES, CATEGORY_BG_CLASSES, CATEGORY_COLORS } from "@/lib/data/types";
import { formatBytes, formatDate, timeAgo, daysSince, cn } from "@/lib/utils";
import { useCopyToClipboard } from "@/hooks/use-copy-to-clipboard";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { BboxMiniMap } from "./bbox-mini-map";
import { AccessSnippets } from "./access-snippets";
import { RelatedDatasets } from "./related-datasets";
import { motion } from "framer-motion";
import { Copy, Check, ExternalLink } from "lucide-react";

interface DatasetDetailSheetProps {
  dataset: Dataset | null;
  siblings?: Dataset[];
  categorySiblings?: Dataset[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTagClick?: (tag: string) => void;
  onRelatedClick?: (dataset: Dataset) => void;
}

function DetailRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <span className="text-xs text-muted-foreground shrink-0">{label}</span>
      <span
        className={`text-sm text-foreground text-right ${mono ? "font-mono tabular-nums" : ""}`}
      >
        {value}
      </span>
    </div>
  );
}

function CopyableRow({ label, value }: { label: string; value: string }) {
  const { copied, copy } = useCopyToClipboard();

  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <span className="text-xs text-muted-foreground shrink-0">{label}</span>
      <button
        onClick={() => copy(value)}
        className="flex items-center gap-1.5 text-sm text-foreground font-mono text-right hover:text-primary transition-colors"
      >
        <span className="truncate max-w-[220px]">{value}</span>
        {copied ? (
          <Check className="h-3 w-3 text-emerald-400 shrink-0" />
        ) : (
          <Copy className="h-3 w-3 text-muted-foreground shrink-0" />
        )}
      </button>
    </div>
  );
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <h4 className="text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground mb-2">
      {children}
    </h4>
  );
}

// Visual age bar: fresh (0–30d), normal (30–180d), stale (>180d)
function AgeBar({ iso }: { iso: string }) {
  const days = daysSince(iso);
  // Scale: 0–365 days maps to 0–100%
  const cappedDays = Math.min(days, 365);
  const pct = (cappedDays / 365) * 100;
  const color =
    days <= 30
      ? "oklch(0.72 0.17 165)"
      : days > 180
        ? "oklch(0.55 0.05 260)"
        : "oklch(0.78 0.14 195)";

  return (
    <div className="space-y-1.5">
      <div className="relative h-1 w-full rounded-full bg-white/[0.05] overflow-hidden">
        {/* Zone markers */}
        <div
          className="absolute top-0 h-full w-px bg-white/[0.1]"
          style={{ left: `${(30 / 365) * 100}%` }}
        />
        <div
          className="absolute top-0 h-full w-px bg-white/[0.1]"
          style={{ left: `${(180 / 365) * 100}%` }}
        />
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <div className="flex justify-between text-[9px] font-mono uppercase tracking-wider text-muted-foreground/70">
        <span>Fresh</span>
        <span>30d</span>
        <span>180d</span>
        <span>Stale</span>
      </div>
    </div>
  );
}

export function DatasetDetailSheet({
  dataset,
  siblings = [],
  categorySiblings = [],
  open,
  onOpenChange,
  onTagClick,
  onRelatedClick,
}: DatasetDetailSheetProps) {
  const categoryLabel =
    ALL_CATEGORIES.find((c) => c.value === dataset?.category)?.label ??
    dataset?.category;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-xl overflow-y-auto bg-card border-white/[0.06]">
        {dataset && (
          <motion.div
            key={dataset.id}
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          >
            <SheetHeader className="pb-5">
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                <Badge
                  variant="outline"
                  className={`text-[11px] border px-1.5 py-0 h-5 ${CATEGORY_BG_CLASSES[dataset.category]}`}
                >
                  {categoryLabel}
                </Badge>
                <Badge
                  variant="outline"
                  className={`text-[10px] font-mono uppercase tracking-wider border px-1.5 py-0 h-5 ${
                    dataset.stage === "raw"
                      ? "bg-orange-500/15 text-orange-400 border-orange-500/30"
                      : "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                  }`}
                >
                  {dataset.stage === "raw" ? "RAW" : "PROCESSED"}
                </Badge>
                {dataset.format && (
                  <Badge
                    variant="outline"
                    className="font-mono text-[11px] uppercase tracking-wider border-white/[0.06] text-muted-foreground"
                  >
                    {dataset.format}
                  </Badge>
                )}
              </div>
              <SheetTitle className="text-lg font-normal tracking-tight text-foreground font-display">
                {dataset.name}
              </SheetTitle>
              {dataset.description && (
                <SheetDescription className="text-sm text-muted-foreground leading-relaxed">
                  {dataset.description}
                </SheetDescription>
              )}
            </SheetHeader>

            {/* Color accent bar */}
            <div
              className="h-px mb-5 opacity-30"
              style={{
                background: `linear-gradient(90deg, ${CATEGORY_COLORS[dataset.category]}, transparent)`,
              }}
            />

            {/* ACCESS (promoted to top for internal users) */}
            {dataset.s3Url && (
              <>
                <div className="space-y-3">
                  <SectionHeader>Access</SectionHeader>
                  <CopyableRow label="S3 Path" value={dataset.s3Url} />
                  <AccessSnippets s3Url={dataset.s3Url} format={dataset.format} />
                  <div className="space-y-0.5 pt-2">
                    <DetailRow
                      label="File Size"
                      value={formatBytes(dataset.sizeBytes)}
                      mono
                    />
                    {dataset.fileCount && (
                      <DetailRow
                        label="Files"
                        value={dataset.fileCount.toLocaleString()}
                        mono
                      />
                    )}
                    {dataset.format && (
                      <DetailRow label="Format" value={dataset.format} mono />
                    )}
                  </div>
                </div>
                <Separator className="my-5 bg-white/[0.04]" />
              </>
            )}

            {/* Coverage */}
            <div className="space-y-2">
              <SectionHeader>Coverage</SectionHeader>
              {dataset.bbox && (
                <div className="flex justify-center pb-2">
                  <div className="rounded-lg bg-background/40 ring-1 ring-white/[0.06] p-3">
                    <BboxMiniMap
                      bbox={dataset.bbox}
                      color={CATEGORY_COLORS[dataset.category]}
                      width={220}
                      height={140}
                    />
                  </div>
                </div>
              )}
              <DetailRow label="Region" value={dataset.region} />
              {dataset.timespan && (
                <DetailRow label="Timespan" value={dataset.timespan} />
              )}
              {dataset.temporalRange && (
                <DetailRow
                  label="Date Range"
                  value={`${dataset.temporalRange.start} → ${dataset.temporalRange.end ?? "ongoing"}`}
                  mono
                />
              )}
              {dataset.bbox && (
                <DetailRow
                  label="Bounding Box"
                  value={`[${dataset.bbox.map((v) => v.toFixed(1)).join(", ")}]`}
                  mono
                />
              )}
            </div>

            {/* Related datasets */}
            {(siblings.length > 0 || categorySiblings.length > 0) && onRelatedClick && (
              <>
                <Separator className="my-5 bg-white/[0.04]" />
                <div className="space-y-2">
                  <SectionHeader>Related</SectionHeader>
                  <RelatedDatasets
                    siblings={siblings}
                    categorySiblings={categorySiblings}
                    onSelect={onRelatedClick}
                  />
                </div>
              </>
            )}

            <Separator className="my-5 bg-white/[0.04]" />

            {/* Provenance */}
            <div className="space-y-0.5">
              <SectionHeader>Provenance</SectionHeader>
              {dataset.maintainer && (
                <DetailRow label="Maintainer" value={`@${dataset.maintainer}`} />
              )}
              {dataset.license && (
                <DetailRow label="License" value={dataset.license} />
              )}
              {dataset.sourceUrl && (
                <div className="flex items-start justify-between gap-4 py-2">
                  <span className="text-xs text-muted-foreground shrink-0">
                    Source
                  </span>
                  <a
                    href={dataset.sourceUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 text-sm text-primary/80 hover:text-primary transition-colors"
                  >
                    <span className="truncate max-w-[180px]">View source</span>
                    <ExternalLink className="h-3 w-3 shrink-0" />
                  </a>
                </div>
              )}
            </div>

            <Separator className="my-5 bg-white/[0.04]" />

            {/* Timeline */}
            <div className="space-y-3">
              <SectionHeader>Timeline</SectionHeader>
              <DetailRow
                label="Last Modified"
                value={`${formatDate(dataset.lastModified)} · ${timeAgo(dataset.lastModified)}`}
              />
              <AgeBar iso={dataset.lastModified} />
            </div>

            {/* Tags */}
            {dataset.tags && dataset.tags.length > 0 && (
              <>
                <Separator className="my-5 bg-white/[0.04]" />
                <div>
                  <SectionHeader>Tags</SectionHeader>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {dataset.tags.map((tag) => (
                      <button
                        key={tag}
                        onClick={() => onTagClick?.(tag)}
                        className={cn(
                          "font-mono text-xs border rounded-md px-2 py-0.5 transition-colors",
                          "border-white/[0.06] text-muted-foreground",
                          onTagClick &&
                            "hover:border-primary/40 hover:text-primary hover:bg-primary/5 cursor-pointer"
                        )}
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
          </motion.div>
        )}
      </SheetContent>
    </Sheet>
  );
}
