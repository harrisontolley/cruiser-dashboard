"use client";

import { cn } from "@/lib/utils";

// Australia bounding box used as the projection reference.
const AUS_WEST = 113;
const AUS_EAST = 154;
const AUS_NORTH = -10;
const AUS_SOUTH = -44;
const VB_WIDTH = 100;
const VB_HEIGHT = 80;

// Simplified Australia silhouette, hand-tuned to the 100x80 viewBox above.
// Not geographically precise — purely aesthetic scaffolding for the bbox.
const AUS_PATH =
  "M9,40 L14,28 L22,18 L34,10 L46,6 L58,5 L70,8 L82,14 L90,24 L94,34 L95,44 L92,54 L86,62 L76,68 L64,72 L52,73 L40,71 L30,67 L22,60 L15,52 L10,44 Z";

function project(lon: number, lat: number): [number, number] {
  const x = ((lon - AUS_WEST) / (AUS_EAST - AUS_WEST)) * VB_WIDTH;
  const y = ((AUS_NORTH - lat) / (AUS_NORTH - AUS_SOUTH)) * VB_HEIGHT;
  return [x, y];
}

interface BboxMiniMapProps {
  bbox: [number, number, number, number]; // [west, south, east, north]
  color?: string;
  className?: string;
  width?: number;
  height?: number;
  showOutline?: boolean;
}

export function BboxMiniMap({
  bbox,
  color = "oklch(0.78 0.14 195)",
  className,
  width = 60,
  height = 48,
  showOutline = true,
}: BboxMiniMapProps) {
  const [west, south, east, north] = bbox;
  const [x1, y1] = project(west, north);
  const [x2, y2] = project(east, south);

  // Clamp the bbox so tiny regions still render visibly.
  const rectX = Math.min(x1, x2);
  const rectY = Math.min(y1, y2);
  const rectW = Math.max(Math.abs(x2 - x1), 2);
  const rectH = Math.max(Math.abs(y2 - y1), 2);

  const centerX = rectX + rectW / 2;
  const centerY = rectY + rectH / 2;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${VB_WIDTH} ${VB_HEIGHT}`}
      className={cn("overflow-visible", className)}
      role="img"
      aria-label="Geographic coverage within Australia"
    >
      {showOutline && (
        <path
          d={AUS_PATH}
          fill="oklch(1 0 0 / 0.03)"
          stroke="oklch(1 0 0 / 0.18)"
          strokeWidth={1}
          strokeLinejoin="round"
        />
      )}

      <rect
        x={rectX}
        y={rectY}
        width={rectW}
        height={rectH}
        fill={color}
        fillOpacity={0.35}
        stroke={color}
        strokeWidth={1}
        strokeOpacity={0.9}
        rx={1}
      />

      <circle cx={centerX} cy={centerY} r={1.4} fill={color} />
    </svg>
  );
}
