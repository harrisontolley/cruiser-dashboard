"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { RegionStatEntry } from "@/lib/data/types";
import { formatBytes } from "@/lib/utils";

const REGION_COLORS = [
  "oklch(0.78 0.14 195)",
  "oklch(0.68 0.18 290)",
  "oklch(0.72 0.17 165)",
  "oklch(0.75 0.16 85)",
  "oklch(0.65 0.18 250)",
  "oklch(0.70 0.12 30)",
];

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const data = payload[0].payload;
  return (
    <div className="rounded-lg ring-1 ring-white/[0.08] bg-[oklch(0.16_0.008_265)] px-3.5 py-2.5 shadow-2xl shadow-black/40">
      <p className="mb-1 text-xs font-medium text-foreground">{data.region}</p>
      <p className="font-mono text-sm text-foreground">{formatBytes(data.sizeBytes)}</p>
      <p className="font-mono text-xs text-muted-foreground">
        {data.count} dataset{data.count !== 1 ? "s" : ""}
      </p>
    </div>
  );
};

export function RegionChart({ data }: { data: RegionStatEntry[] }) {

  return (
    <div className="rounded-xl ring-1 ring-white/[0.06] bg-card p-5">
      <div className="mb-4 flex items-center gap-2.5">
        <div className="h-1.5 w-1.5 rounded-full bg-primary/60" />
        <h3 className="text-sm font-medium text-foreground">Datasets by Region</h3>
      </div>
      <div className="h-[200px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 0, right: 4, bottom: 0, left: -20 }}>
            <XAxis
              dataKey="region"
              stroke="oklch(0.65 0 0)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              interval={0}
              angle={-15}
              textAnchor="end"
              height={50}
            />
            <YAxis
              stroke="oklch(0.65 0 0)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              fontFamily="var(--font-mono)"
              tickFormatter={(v) => formatBytes(v)}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: "oklch(1 0 0 / 2%)" }} />
            <Bar dataKey="sizeBytes" radius={[4, 4, 0, 0]} barSize={28}>
              {data.map((_, i) => (
                <Cell key={i} fill={REGION_COLORS[i % REGION_COLORS.length]} fillOpacity={0.7} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
