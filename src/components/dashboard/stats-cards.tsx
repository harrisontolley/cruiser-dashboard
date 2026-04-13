"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { formatBytes } from "@/lib/utils";
import { BucketStats } from "@/lib/data/types";
import { AnimatedCard } from "@/components/motion/animated-container";
import { CountUp } from "@/components/motion/count-up";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Database, Layers, Files, HardDrive, ArrowLeftRight } from "lucide-react";

interface KpiStatsCardProps {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  description: string;
  accentColor?: string;
  tooltip?: string;
}

function KpiStatsCard({
  icon,
  label,
  value,
  description,
  accentColor,
  tooltip,
}: KpiStatsCardProps) {
  const card = (
    <div
      className={cn(
        "group relative overflow-hidden rounded-xl bg-card p-5",
        "ring-1 ring-white/[0.06]",
        "transition-all duration-300",
        "hover:ring-white/[0.1] hover:bg-card/80",
        tooltip && "cursor-help"
      )}
    >
      <div
        className="absolute top-0 left-3 right-3 h-px opacity-40"
        style={{
          background: `linear-gradient(90deg, transparent, ${accentColor ?? "oklch(0.78 0.14 195)"}, transparent)`,
        }}
      />

      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2 min-w-0">
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-[0.12em]">
            {label}
          </div>
          <div className="text-2xl font-bold tracking-tight text-foreground font-mono tabular-nums">
            {value}
          </div>
          <div className="text-xs text-muted-foreground">{description}</div>
        </div>

        <div
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-all duration-300"
          style={{
            backgroundColor: `color-mix(in oklch, ${accentColor ?? "oklch(0.78 0.14 195)"} 12%, transparent)`,
            color: accentColor ?? "oklch(0.78 0.14 195)",
          }}
        >
          {icon}
        </div>
      </div>
    </div>
  );

  if (!tooltip) return card;

  return (
    <Tooltip>
      <TooltipTrigger render={card} />
      <TooltipContent className="max-w-[240px] text-xs leading-relaxed">
        {tooltip}
      </TooltipContent>
    </Tooltip>
  );
}

function PairCoverageValue({ rawWithProcessed, rawTotal }: { rawWithProcessed: number; rawTotal: number }) {
  if (rawTotal === 0) {
    return <span className="text-muted-foreground">—</span>;
  }
  return (
    <span className="inline-flex items-baseline gap-1">
      <CountUp value={rawWithProcessed} />
      <span className="text-muted-foreground text-base font-normal">/</span>
      <CountUp value={rawTotal} />
    </span>
  );
}

function CategoriesValue({ count }: { count: number }) {
  return (
    <span className="inline-flex items-baseline gap-1">
      <CountUp value={count} />
      <span className="text-muted-foreground text-base font-normal">/ 7</span>
    </span>
  );
}

export function StatsCards({ stats }: { stats: BucketStats }) {
  const pairComplete =
    stats.pairCoverage.rawTotal > 0 &&
    stats.pairCoverage.rawWithProcessed === stats.pairCoverage.rawTotal;

  const cards: KpiStatsCardProps[] = [
    {
      icon: <Database className="h-4 w-4" />,
      label: "Datasets",
      value: <CountUp value={stats.datasetCount} />,
      description: "In the catalogue",
      accentColor: "oklch(0.78 0.14 195)",
    },
    {
      icon: <Layers className="h-4 w-4" />,
      label: "Categories",
      value: <CategoriesValue count={stats.categoryCount} />,
      description: "Data pipelines ingested",
      accentColor: "oklch(0.68 0.18 290)",
      tooltip:
        "Categories with ingested data out of 7 planned. Remaining slots are reserved for future pipelines.",
    },
    {
      icon: <Files className="h-4 w-4" />,
      label: "Files",
      value: (
        <CountUp
          value={stats.fileCountTotal}
          format={(n) => Math.round(n).toLocaleString()}
        />
      ),
      description: "Objects across all datasets",
      accentColor: "oklch(0.72 0.17 165)",
    },
    {
      icon: <HardDrive className="h-4 w-4" />,
      label: "Total Size",
      value: (
        <CountUp
          value={stats.totalSizeBytes}
          format={(n) => formatBytes(n)}
        />
      ),
      description: "On-disk footprint",
      accentColor: "oklch(0.75 0.16 85)",
    },
    {
      icon: <ArrowLeftRight className="h-4 w-4" />,
      label: "Pair Coverage",
      value: (
        <PairCoverageValue
          rawWithProcessed={stats.pairCoverage.rawWithProcessed}
          rawTotal={stats.pairCoverage.rawTotal}
        />
      ),
      description:
        stats.pairCoverage.rawTotal === 0
          ? "No paired pipelines yet"
          : pairComplete
            ? "Raw → Processed pipelines complete"
            : "Raw datasets with processed sibling",
      accentColor: pairComplete
        ? "oklch(0.72 0.17 165)"
        : "oklch(0.72 0.17 25)",
      tooltip:
        "Count of raw datasets that have a matching processed sibling (linked by pairId). An indicator of ingestion pipeline completeness.",
    },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-5">
      {cards.map((card, i) => (
        <AnimatedCard key={card.label} index={i}>
          <KpiStatsCard {...card} />
        </AnimatedCard>
      ))}
    </div>
  );
}
