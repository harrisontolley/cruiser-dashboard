"use client";

import { useMemo } from "react";
import { Dataset, CATEGORY_COLORS, ALL_CATEGORIES } from "@/lib/data/types";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const YEAR_START = 2019;
const YEAR_END = 2027;
const TOTAL_YEARS = YEAR_END - YEAR_START;

function yearToPercent(year: number): number {
  return ((year - YEAR_START) / TOTAL_YEARS) * 100;
}

function dateToPercent(dateStr: string): number {
  const d = new Date(dateStr);
  const year = d.getFullYear() + d.getMonth() / 12 + d.getDate() / 365;
  return yearToPercent(year);
}

export function TemporalTimeline({ datasets }: { datasets: Dataset[] }) {

  const timelineData = useMemo(() => {
    return datasets
      .filter((d) => d.temporalRange)
      .sort((a, b) => {
        const catOrder =
          ALL_CATEGORIES.findIndex((c) => c.value === a.category) -
          ALL_CATEGORIES.findIndex((c) => c.value === b.category);
        if (catOrder !== 0) return catOrder;
        return (
          new Date(a.temporalRange!.start).getTime() -
          new Date(b.temporalRange!.start).getTime()
        );
      });
  }, [datasets]);

  const noTemporalData = useMemo(
    () => datasets.filter((d) => !d.temporalRange),
    [datasets]
  );

  const years = Array.from({ length: TOTAL_YEARS + 1 }, (_, i) => YEAR_START + i);

  return (
    <div className="rounded-xl ring-1 ring-white/[0.06] bg-card p-5">
      <div className="mb-5 flex items-center gap-2.5">
        <div className="h-1.5 w-1.5 rounded-full bg-primary/60" />
        <h3 className="text-sm font-medium text-foreground font-display">
          Temporal Coverage
        </h3>
        <span className="text-xs font-mono text-muted-foreground">
          {timelineData.length + noTemporalData.length} datasets
        </span>
      </div>

      <div className="space-y-2.5">
        {/* Year axis */}
        <div className="relative h-4 ml-[130px]">
          {years
            .filter((_, i) => i % 2 === 0 || i === years.length - 1)
            .map((year) => (
              <span
                key={year}
                className="absolute text-[11px] font-mono text-muted-foreground -translate-x-1/2"
                style={{ left: `${yearToPercent(year)}%` }}
              >
                {year}
              </span>
            ))}
        </div>

        {/* Bars */}
        {timelineData.map((dataset) => {
          const startPct = dateToPercent(dataset.temporalRange!.start);
          const endPct = dataset.temporalRange!.end
            ? dateToPercent(dataset.temporalRange!.end)
            : dateToPercent(new Date().toISOString());
          const widthPct = Math.max(endPct - startPct, 1);
          const color = CATEGORY_COLORS[dataset.category];

          return (
            <div key={dataset.id} className="flex items-center gap-2.5 group">
              <div className="w-[130px] shrink-0 text-right pr-2">
                <span className="text-xs text-foreground truncate block group-hover:text-foreground transition-colors">
                  {dataset.name}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {dataset.region}
                </span>
              </div>
              <div className="relative flex-1 h-6">
                {years.map((year) => (
                  <div
                    key={year}
                    className="absolute top-0 h-full w-px bg-white/[0.03]"
                    style={{ left: `${yearToPercent(year)}%` }}
                  />
                ))}
                <Tooltip>
                  <TooltipTrigger
                    className="absolute top-1 h-4 rounded-[4px] cursor-default transition-all duration-200 opacity-70 group-hover:opacity-100"
                    style={{
                      left: `${startPct}%`,
                      width: `${widthPct}%`,
                      background: `linear-gradient(90deg, ${color}, color-mix(in oklch, ${color} 70%, transparent))`,
                      boxShadow: `0 0 12px -2px ${color}40`,
                    }}
                  />
                  <TooltipContent side="top">
                    <div className="font-medium text-[11px]">{dataset.name}</div>
                    <div className="text-muted-foreground text-[10px]">
                      {dataset.timespan ??
                        `${dataset.temporalRange!.start} → ${dataset.temporalRange!.end ?? "ongoing"}`}
                    </div>
                  </TooltipContent>
                </Tooltip>
              </div>
            </div>
          );
        })}

        {/* Datasets without temporal range */}
        {noTemporalData.length > 0 && (
          <div className="mt-3 pt-3 border-t border-white/[0.04]">
            <span className="text-[11px] text-muted-foreground uppercase tracking-[0.15em] ml-[130px]">
              No temporal range
            </span>
            {noTemporalData.map((dataset) => (
              <div
                key={dataset.id}
                className="flex items-center gap-2.5 mt-2 group"
              >
                <div className="w-[130px] shrink-0 text-right pr-2">
                  <span className="text-[11px] text-foreground truncate block">
                    {dataset.name}
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    {dataset.region}
                  </span>
                </div>
                <div className="relative flex-1 h-6">
                  {years.map((year) => (
                    <div
                      key={year}
                      className="absolute top-0 h-full w-px bg-white/[0.03]"
                      style={{ left: `${yearToPercent(year)}%` }}
                    />
                  ))}
                  <div className="absolute top-2 left-1/2 h-2 w-2 rounded-full bg-muted-foreground/20 ring-2 ring-background" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
