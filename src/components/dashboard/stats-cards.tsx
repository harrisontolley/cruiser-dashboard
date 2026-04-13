"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { formatBytes, timeAgo } from "@/lib/utils";
import { BucketStats } from "@/lib/data/types";
import { AnimatedCard } from "@/components/motion/animated-container";
import { Database, Layers, Globe, HardDrive, Clock, Users } from "lucide-react";

interface KpiStatsCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  description: string;
  accentColor?: string;
}

function KpiStatsCard({ icon, label, value, description, accentColor }: KpiStatsCardProps) {
  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-xl bg-card p-5",
        "ring-1 ring-white/[0.06]",
        "transition-all duration-300",
        "hover:ring-white/[0.1] hover:bg-card/80"
      )}
    >
      {/* Top accent line */}
      <div
        className="absolute top-0 left-3 right-3 h-px opacity-40"
        style={{
          background: `linear-gradient(90deg, transparent, ${accentColor ?? "oklch(0.78 0.14 195)"}, transparent)`,
        }}
      />

      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-[0.12em]">
            {label}
          </div>
          <div className="text-2xl font-bold tracking-tight text-foreground font-mono tabular-nums">
            {value}
          </div>
          <div className="text-xs text-muted-foreground">
            {description}
          </div>
        </div>

        <div
          className="flex h-9 w-9 items-center justify-center rounded-lg transition-all duration-300"
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
}

export function StatsCards({ stats }: { stats: BucketStats }) {

  const cards = [
    {
      icon: <Database className="h-4 w-4" />,
      label: "Datasets",
      value: stats.datasetCount.toString(),
      description: "In the catalogue",
      accentColor: "oklch(0.78 0.14 195)",
    },
    {
      icon: <Layers className="h-4 w-4" />,
      label: "Categories",
      value: `${stats.categoryCount}/7`,
      description: "Active categories",
      accentColor: "oklch(0.68 0.18 290)",
    },
    {
      icon: <Globe className="h-4 w-4" />,
      label: "Regions",
      value: stats.regionCount.toString(),
      description: "Geographic areas",
      accentColor: "oklch(0.72 0.17 165)",
    },
    {
      icon: <HardDrive className="h-4 w-4" />,
      label: "Total Size",
      value: formatBytes(stats.totalSizeBytes),
      description: "Across all datasets",
      accentColor: "oklch(0.75 0.16 85)",
    },
    {
      icon: <Clock className="h-4 w-4" />,
      label: "Last Updated",
      value: timeAgo(stats.lastUpdated),
      description: "Most recent change",
      accentColor: "oklch(0.65 0.18 250)",
    },
    {
      icon: <Users className="h-4 w-4" />,
      label: "Maintainers",
      value: stats.maintainerCount.toString(),
      description: "Team members",
      accentColor: "oklch(0.70 0.12 30)",
    },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-6">
      {cards.map((card, i) => (
        <AnimatedCard key={card.label} index={i}>
          <KpiStatsCard {...card} />
        </AnimatedCard>
      ))}
    </div>
  );
}
