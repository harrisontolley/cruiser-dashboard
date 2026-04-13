"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { CATEGORY_COLORS, GrowthEntry } from "@/lib/data/types";
import { formatBytes } from "@/lib/utils";

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const data = payload[0].payload;
  if (!data.datasetName) return null;

  return (
    <div className="rounded-lg ring-1 ring-white/[0.08] bg-[oklch(0.16_0.008_265)] px-3.5 py-2.5 shadow-2xl shadow-black/40">
      <p className="mb-1 text-xs font-medium text-foreground">
        {data.datasetName}
      </p>
      <p className="font-mono text-[11px] text-muted-foreground">
        +{formatBytes(data.sizeBytes)}
      </p>
      <div className="mt-1.5 pt-1.5 border-t border-white/[0.06]">
        <p className="font-mono text-sm text-foreground">
          {formatBytes(data.totalBytes)}
        </p>
        <p className="text-[11px] text-muted-foreground">cumulative total</p>
      </div>
    </div>
  );
};

const CustomDot = (props: any) => {
  const { cx, cy, payload } = props;
  if (!payload.datasetName) return null;

  const color =
    CATEGORY_COLORS[payload.category as keyof typeof CATEGORY_COLORS] ??
    "oklch(0.78 0.14 195)";

  return (
    <g>
      <circle cx={cx} cy={cy} r={8} fill={color} opacity={0.1} />
      <circle cx={cx} cy={cy} r={4} fill={color} opacity={0.8} />
      <circle
        cx={cx}
        cy={cy}
        r={2}
        fill="oklch(0.95 0.005 260)"
        opacity={0.9}
      />
    </g>
  );
};

export function GrowthChart({ data }: { data: GrowthEntry[] }) {

  return (
    <div className="rounded-xl ring-1 ring-white/[0.06] bg-card p-5">
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="h-1.5 w-1.5 rounded-full bg-primary/60" />
          <h3 className="text-sm font-medium text-foreground">
            Storage Growth
          </h3>
          <span className="text-xs font-mono text-muted-foreground">
            {formatBytes(data[data.length - 1]?.totalBytes ?? 0)} total
          </span>
        </div>
        <span className="text-[11px] text-muted-foreground">
          {data.length - 1} datasets ingested
        </span>
      </div>

      <div className="h-[240px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
          >
            <defs>
              <linearGradient id="growthFill" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor="oklch(0.78 0.14 195)"
                  stopOpacity={0.25}
                />
                <stop
                  offset="100%"
                  stopColor="oklch(0.78 0.14 195)"
                  stopOpacity={0.02}
                />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              stroke="oklch(0.45 0 0)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              fontFamily="var(--font-mono)"
              tickFormatter={(v) => {
                const d = new Date(v);
                return d.toLocaleDateString("en-US", {
                  month: "short",
                  year: "2-digit",
                });
              }}
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
            <Tooltip
              content={<CustomTooltip />}
              cursor={{
                stroke: "oklch(0.78 0.14 195)",
                strokeOpacity: 0.15,
                strokeDasharray: "4 4",
              }}
            />
            <Area
              type="stepAfter"
              dataKey="totalBytes"
              stroke="oklch(0.78 0.14 195)"
              strokeWidth={2}
              fill="url(#growthFill)"
              dot={<CustomDot />}
              activeDot={{
                r: 5,
                fill: "oklch(0.78 0.14 195)",
                stroke: "oklch(0.95 0.005 260)",
                strokeWidth: 2,
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
