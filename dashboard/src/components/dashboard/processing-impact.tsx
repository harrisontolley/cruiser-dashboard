"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Dataset } from "@/lib/data/types";
import { formatBytes } from "@/lib/utils";
import { ArrowDown, ArrowRight, FileDown, Layers } from "lucide-react";

// Colors for raw vs processed
const RAW_COLOR = "oklch(0.65 0.18 30)"; // orange
const PROC_COLOR = "oklch(0.72 0.17 165)"; // emerald

interface DatasetPair {
  pairId: string;
  label: string;
  raw: Dataset[];
  processed: Dataset[];
  rawTotalBytes: number;
  processedTotalBytes: number;
  rawFileCount: number;
  processedFileCount: number;
}

// ---------------------------------------------------------------------------
// Custom Tooltip (matches existing chart styling)
// ---------------------------------------------------------------------------

type TooltipPayloadEntry = {
  dataKey?: string | number;
  name?: string;
  value?: number;
  fill?: string;
};

type ChartTooltipProps = {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
  label?: string | number;
};

function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg ring-1 ring-white/[0.08] bg-[oklch(0.16_0.008_265)] px-3.5 py-2.5 shadow-2xl shadow-black/40">
      <p className="mb-1 text-xs font-medium text-foreground">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} className="font-mono text-[11px]" style={{ color: p.fill }}>
          {p.name}: {formatBytes(p.value ?? 0)}
        </p>
      ))}
    </div>
  );
}

function FileCountTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg ring-1 ring-white/[0.08] bg-[oklch(0.16_0.008_265)] px-3.5 py-2.5 shadow-2xl shadow-black/40">
      <p className="mb-1 text-xs font-medium text-foreground">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} className="font-mono text-[11px]" style={{ color: p.fill }}>
          {p.name}: {(p.value ?? 0).toLocaleString()} files
        </p>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SizeComparisonChart({ pairs }: { pairs: DatasetPair[] }) {
  const data = pairs.map((p) => ({
    name: p.label,
    Raw: p.rawTotalBytes,
    Processed: p.processedTotalBytes,
  }));

  return (
    <div className="rounded-xl ring-1 ring-white/[0.06] bg-card/50 p-5">
      <div className="mb-4 flex items-center gap-2.5">
        <div className="h-1.5 w-1.5 rounded-full bg-primary/60" />
        <h4 className="text-sm font-medium text-foreground">Size Comparison</h4>
      </div>
      <div className="h-[200px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 0, right: 4, bottom: 0, left: 0 }}>
            <XAxis
              dataKey="name"
              stroke="oklch(0.45 0 0)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="oklch(0.45 0 0)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              fontFamily="var(--font-mono)"
              width={64}
              tickFormatter={(v) => formatBytes(v)}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: "oklch(1 0 0 / 2%)" }} />
            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: "11px", fontFamily: "var(--font-mono)" }}
            />
            <Bar dataKey="Raw" fill={RAW_COLOR} fillOpacity={0.7} radius={[4, 4, 0, 0]} barSize={28} />
            <Bar dataKey="Processed" fill={PROC_COLOR} fillOpacity={0.7} radius={[4, 4, 0, 0]} barSize={28} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function FileCountChart({ pairs }: { pairs: DatasetPair[] }) {
  const data = pairs.map((p) => ({
    name: p.label,
    Raw: p.rawFileCount,
    Processed: p.processedFileCount,
  }));

  return (
    <div className="rounded-xl ring-1 ring-white/[0.06] bg-card/50 p-5">
      <div className="mb-4 flex items-center gap-2.5">
        <div className="h-1.5 w-1.5 rounded-full bg-primary/60" />
        <h4 className="text-sm font-medium text-foreground">File Count Comparison</h4>
      </div>
      <div className="h-[200px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 0, right: 4, bottom: 0, left: 0 }}>
            <XAxis
              dataKey="name"
              stroke="oklch(0.45 0 0)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="oklch(0.45 0 0)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              fontFamily="var(--font-mono)"
              width={48}
            />
            <Tooltip content={<FileCountTooltip />} cursor={{ fill: "oklch(1 0 0 / 2%)" }} />
            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: "11px", fontFamily: "var(--font-mono)" }}
            />
            <Bar dataKey="Raw" fill={RAW_COLOR} fillOpacity={0.7} radius={[4, 4, 0, 0]} barSize={28} />
            <Bar dataKey="Processed" fill={PROC_COLOR} fillOpacity={0.7} radius={[4, 4, 0, 0]} barSize={28} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function CompressionIndicators({ pairs }: { pairs: DatasetPair[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {pairs.map((pair) => {
        const reduction = ((pair.rawTotalBytes - pair.processedTotalBytes) / pair.rawTotalBytes) * 100;
        const fileReduction = ((pair.rawFileCount - pair.processedFileCount) / pair.rawFileCount) * 100;

        return (
          <div
            key={pair.pairId}
            className="relative overflow-hidden rounded-xl bg-card/50 p-5 ring-1 ring-white/[0.06]"
          >
            <div className="absolute top-0 left-3 right-3 h-px opacity-40"
              style={{ background: `linear-gradient(90deg, transparent, ${PROC_COLOR}, transparent)` }}
            />
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-[0.12em] mb-3">
              {pair.label}
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <ArrowDown className="h-4 w-4 text-emerald-400" />
                <span className="text-2xl font-bold font-mono tabular-nums text-emerald-400">
                  {reduction.toFixed(1)}%
                </span>
                <span className="text-xs text-muted-foreground">size reduction</span>
              </div>
              <div className="flex items-baseline gap-2 text-xs text-muted-foreground font-mono">
                <span>{formatBytes(pair.rawTotalBytes)}</span>
                <ArrowRight className="h-3 w-3 shrink-0" />
                <span>{formatBytes(pair.processedTotalBytes)}</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <FileDown className="h-3.5 w-3.5" />
                <span className="font-mono">
                  {pair.rawFileCount.toLocaleString()} → {pair.processedFileCount.toLocaleString()} files
                </span>
                <span className="text-emerald-400/70">
                  ({fileReduction > 0 ? "-" : "+"}{Math.abs(fileReduction).toFixed(0)}%)
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function FormatList({
  title,
  formats,
  color,
}: {
  title: string;
  formats: Map<string, number>;
  color: string;
}) {
  return (
    <div>
      <div className="text-xs font-medium text-muted-foreground uppercase tracking-[0.12em] mb-2.5">
        {title}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {[...formats.entries()]
          .sort((a, b) => b[1] - a[1])
          .map(([fmt, count]) => (
            <span
              key={fmt}
              className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-mono ring-1"
              style={{
                backgroundColor: `color-mix(in oklch, ${color} 10%, transparent)`,
                color: color,
                borderColor: `color-mix(in oklch, ${color} 25%, transparent)`,
              }}
            >
              {fmt}
              <span className="opacity-60">×{count}</span>
            </span>
          ))}
      </div>
    </div>
  );
}

function FormatBreakdown({ datasets }: { datasets: Dataset[] }) {
  const rawFormats = new Map<string, number>();
  const procFormats = new Map<string, number>();

  for (const d of datasets) {
    const fmt = d.format ?? "Unknown";
    const map = d.stage === "raw" ? rawFormats : procFormats;
    map.set(fmt, (map.get(fmt) ?? 0) + 1);
  }

  return (
    <div className="rounded-xl ring-1 ring-white/[0.06] bg-card/50 p-5">
      <div className="mb-4 flex items-center gap-2.5">
        <div className="h-1.5 w-1.5 rounded-full bg-primary/60" />
        <h4 className="text-sm font-medium text-foreground">Format Breakdown</h4>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormatList title="Raw Formats" formats={rawFormats} color={RAW_COLOR} />
        <FormatList title="Processed Formats" formats={procFormats} color={PROC_COLOR} />
      </div>
    </div>
  );
}

function PairedDatasetCards({ pairs }: { pairs: DatasetPair[] }) {
  return (
    <div className="space-y-4">
      {pairs.map((pair) => {
        const reduction = ((pair.rawTotalBytes - pair.processedTotalBytes) / pair.rawTotalBytes) * 100;
        const rawPrimary = pair.raw[0];
        const procPrimary = pair.processed[0];

        return (
          <div key={pair.pairId} className="grid gap-4 md:grid-cols-[1fr_auto_1fr] items-center">
            {/* Raw card */}
            <div className="relative overflow-hidden rounded-xl bg-card/50 p-5 ring-1 ring-white/[0.06]">
              <div
                className="absolute top-0 left-3 right-3 h-px opacity-50"
                style={{ background: `linear-gradient(90deg, transparent, ${RAW_COLOR}, transparent)` }}
              />
              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider bg-orange-500/15 text-orange-400 ring-1 ring-orange-500/30">
                  Raw
                </span>
                <span className="text-sm font-medium text-foreground truncate">
                  {rawPrimary.name}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div>
                  <div className="text-muted-foreground mb-0.5">Size</div>
                  <div className="font-mono font-medium text-foreground">{formatBytes(pair.rawTotalBytes)}</div>
                </div>
                <div>
                  <div className="text-muted-foreground mb-0.5">Files</div>
                  <div className="font-mono font-medium text-foreground">{pair.rawFileCount.toLocaleString()}</div>
                </div>
                <div>
                  <div className="text-muted-foreground mb-0.5">Format</div>
                  <div className="font-mono font-medium text-foreground">
                    {[...new Set(pair.raw.map((d) => d.format))].join(", ")}
                  </div>
                </div>
              </div>
            </div>

            {/* Arrow + reduction */}
            <div className="flex flex-col items-center gap-1 px-2">
              <ArrowRight className="h-5 w-5 text-emerald-400 hidden md:block" />
              <ArrowDown className="h-5 w-5 text-emerald-400 md:hidden" />
              <span className="text-xs font-mono font-bold text-emerald-400">
                -{reduction.toFixed(0)}%
              </span>
            </div>

            {/* Processed card */}
            <div className="relative overflow-hidden rounded-xl bg-card/50 p-5 ring-1 ring-white/[0.06]">
              <div
                className="absolute top-0 left-3 right-3 h-px opacity-50"
                style={{ background: `linear-gradient(90deg, transparent, ${PROC_COLOR}, transparent)` }}
              />
              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30">
                  Processed
                </span>
                <span className="text-sm font-medium text-foreground truncate">
                  {procPrimary.name}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div>
                  <div className="text-muted-foreground mb-0.5">Size</div>
                  <div className="font-mono font-medium text-foreground">{formatBytes(pair.processedTotalBytes)}</div>
                </div>
                <div>
                  <div className="text-muted-foreground mb-0.5">Files</div>
                  <div className="font-mono font-medium text-foreground">{pair.processedFileCount.toLocaleString()}</div>
                </div>
                <div>
                  <div className="text-muted-foreground mb-0.5">Format</div>
                  <div className="font-mono font-medium text-foreground">
                    {[...new Set(pair.processed.map((d) => d.format))].join(", ")}
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ProcessingImpact({ datasets }: { datasets: Dataset[] }) {
  const pairs = useMemo(() => {
    const byPairId = new Map<string, { raw: Dataset[]; processed: Dataset[] }>();

    for (const d of datasets) {
      if (!d.pairId) continue;
      const entry = byPairId.get(d.pairId) ?? { raw: [], processed: [] };
      entry[d.stage].push(d);
      byPairId.set(d.pairId, entry);
    }

    return Array.from(byPairId.entries())
      .filter(([, v]) => v.raw.length > 0 && v.processed.length > 0)
      .map(([pairId, v]): DatasetPair => ({
        pairId,
        label: pairId
          .replace(/-/g, " ")
          .replace(/\b\w/g, (c) => c.toUpperCase()),
        raw: v.raw,
        processed: v.processed,
        rawTotalBytes: v.raw.reduce((s, d) => s + d.sizeBytes, 0),
        processedTotalBytes: v.processed.reduce((s, d) => s + d.sizeBytes, 0),
        rawFileCount: v.raw.reduce((s, d) => s + (d.fileCount ?? 0), 0),
        processedFileCount: v.processed.reduce((s, d) => s + (d.fileCount ?? 0), 0),
      }));
  }, [datasets]);

  if (pairs.length === 0) return null;

  return (
    <div className="rounded-xl ring-1 ring-white/[0.06] bg-card p-5">
      <div className="mb-5 flex items-center gap-2.5">
        <Layers className="h-4 w-4 text-primary/60" />
        <h3 className="text-sm font-medium text-foreground font-display">Processing Impact</h3>
        <span className="text-xs font-mono text-muted-foreground">
          {pairs.length} paired dataset{pairs.length !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="space-y-5">
        {/* Compression KPIs */}
        <CompressionIndicators pairs={pairs} />

        {/* Charts */}
        <div className="grid gap-5 lg:grid-cols-2">
          <SizeComparisonChart pairs={pairs} />
          <FileCountChart pairs={pairs} />
        </div>

        {/* Format breakdown */}
        <FormatBreakdown datasets={datasets} />

        {/* Paired cards */}
        <div>
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-[0.12em] mb-3">
            Dataset Pairs
          </div>
          <PairedDatasetCards pairs={pairs} />
        </div>
      </div>
    </div>
  );
}
