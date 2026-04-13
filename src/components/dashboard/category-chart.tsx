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
import { CategoryStatEntry } from "@/lib/data/types";
import { formatBytes } from "@/lib/utils";

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const data = payload[0].payload;
  return (
    <div className="rounded-lg ring-1 ring-white/[0.08] bg-[oklch(0.16_0.008_265)] px-3.5 py-2.5 shadow-2xl shadow-black/40">
      <p className="mb-1 text-xs font-medium text-foreground">{data.label}</p>
      {data.count > 0 ? (
        <>
          <p className="font-mono text-sm text-foreground">{formatBytes(data.sizeBytes)}</p>
          <p className="font-mono text-xs text-muted-foreground">
            {data.count} dataset{data.count !== 1 ? "s" : ""}
          </p>
        </>
      ) : (
        <p className="text-xs text-muted-foreground italic">No datasets yet</p>
      )}
    </div>
  );
};

export function CategoryChart({ data }: { data: CategoryStatEntry[] }) {

  return (
    <div className="rounded-xl ring-1 ring-white/[0.06] bg-card p-5">
      <div className="mb-4 flex items-center gap-2.5">
        <div className="h-1.5 w-1.5 rounded-full bg-primary/60" />
        <h3 className="text-sm font-medium text-foreground">Size by Category</h3>
      </div>
      <div className="h-[200px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 0, right: 4, bottom: 0, left: 0 }}
          >
            <XAxis
              type="number"
              stroke="oklch(0.65 0 0)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              fontFamily="var(--font-mono)"
              tickFormatter={(v) => formatBytes(v)}
            />
            <YAxis
              type="category"
              dataKey="label"
              stroke="oklch(0.65 0 0)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              width={90}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: "oklch(1 0 0 / 2%)" }} />
            <Bar dataKey="sizeBytes" radius={[0, 4, 4, 0]} barSize={16}>
              {data.map((entry) => (
                <Cell
                  key={entry.category}
                  fill={entry.color}
                  fillOpacity={entry.count > 0 ? 0.7 : 0.08}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
