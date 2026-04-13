"use client";

import { useState } from "react";
import { Dataset, ALL_CATEGORIES, CATEGORY_BG_CLASSES, CATEGORY_COLORS } from "@/lib/data/types";
import { formatBytes, formatDate, timeAgo } from "@/lib/utils";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { motion } from "framer-motion";
import { Copy, Check, ExternalLink } from "lucide-react";

interface DatasetDetailSheetProps {
  dataset: Dataset | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
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
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <span className="text-xs text-muted-foreground shrink-0">{label}</span>
      <button
        onClick={copy}
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

export function DatasetDetailSheet({
  dataset,
  open,
  onOpenChange,
}: DatasetDetailSheetProps) {
  const categoryLabel =
    ALL_CATEGORIES.find((c) => c.value === dataset?.category)?.label ??
    dataset?.category;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto bg-card border-white/[0.06]">
        {dataset && (
          <motion.div
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
              <SheetTitle className="text-base font-semibold tracking-tight text-foreground">
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

            {/* Coverage */}
            <div className="space-y-0.5">
              <SectionHeader>Coverage</SectionHeader>
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

            <Separator className="my-5 bg-white/[0.04]" />

            {/* Storage */}
            <div className="space-y-0.5">
              <SectionHeader>Storage</SectionHeader>
              {dataset.s3Url && (
                <CopyableRow label="S3 Path" value={dataset.s3Url} />
              )}
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
            <div className="space-y-0.5">
              <SectionHeader>Timeline</SectionHeader>
              <DetailRow
                label="Last Modified"
                value={formatDate(dataset.lastModified)}
                mono
              />
              <DetailRow label="Last Update" value={timeAgo(dataset.lastModified)} />
            </div>

            {/* Tags */}
            {dataset.tags && dataset.tags.length > 0 && (
              <>
                <Separator className="my-5 bg-white/[0.04]" />
                <div>
                  <SectionHeader>Tags</SectionHeader>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {dataset.tags.map((tag) => (
                      <Badge
                        key={tag}
                        variant="outline"
                        className="font-mono text-xs border-white/[0.06] text-muted-foreground"
                      >
                        {tag}
                      </Badge>
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
