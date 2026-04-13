"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, Rectangle, Tooltip, useMap } from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";
import "leaflet/dist/leaflet.css";
import { Dataset, CATEGORY_COLORS } from "@/lib/data/types";

function FitBounds({ datasets }: { datasets: Dataset[] }) {
  const map = useMap();

  useEffect(() => {
    if (datasets.length === 0) return;
    const allBboxes = datasets.filter((d) => d.bbox);
    if (allBboxes.length === 0) return;

    const west = Math.min(...allBboxes.map((d) => d.bbox![0]));
    const south = Math.min(...allBboxes.map((d) => d.bbox![1]));
    const east = Math.max(...allBboxes.map((d) => d.bbox![2]));
    const north = Math.max(...allBboxes.map((d) => d.bbox![3]));

    map.fitBounds(
      [
        [south - 8, west - 15],
        [north + 8, east + 15],
      ],
      { padding: [30, 30], maxZoom: 4 }
    );
  }, [map, datasets]);

  return null;
}

interface CoverageMapInnerProps {
  datasets: Dataset[];
  hoveredId: string | null;
  onHover: (id: string | null) => void;
  onClick?: (dataset: Dataset) => void;
}

export default function CoverageMapInner({
  datasets,
  hoveredId,
  onHover,
  onClick,
}: CoverageMapInnerProps) {
  return (
    <MapContainer
      center={[0, 60]}
      zoom={2}
      scrollWheelZoom={true}
      style={{ height: "100%", width: "100%" }}
      attributionControl={false}
      zoomControl={true}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      />
      {/* Labels on top of rectangles */}
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png"
        pane="overlayPane"
      />
      <FitBounds datasets={datasets} />
      {datasets.map((dataset) => {
        if (!dataset.bbox) return null;
        const [west, south, east, north] = dataset.bbox;
        const bounds: LatLngBoundsExpression = [
          [south, west],
          [north, east],
        ];
        const color = CATEGORY_COLORS[dataset.category];
        const isHovered = hoveredId === dataset.id;

        return (
          <Rectangle
            key={dataset.id}
            bounds={bounds}
            pathOptions={{
              color,
              weight: isHovered ? 2.5 : 1,
              fillColor: color,
              fillOpacity: isHovered ? 0.28 : 0.12,
              dashArray: isHovered ? undefined : "6 4",
            }}
            eventHandlers={{
              mouseover: () => onHover(dataset.id),
              mouseout: () => onHover(null),
              click: () => onClick?.(dataset),
            }}
          >
            <Tooltip
              direction="top"
              offset={[0, -10]}
              className="!bg-[oklch(0.16_0.008_265)] !border-white/[0.08] !text-foreground !rounded-lg !px-3.5 !py-2.5 !shadow-2xl !shadow-black/40"
            >
              <div className="text-xs space-y-0.5">
                <div className="font-medium">{dataset.name}</div>
                <div className="opacity-50">{dataset.region}</div>
              </div>
            </Tooltip>
          </Rectangle>
        );
      })}
    </MapContainer>
  );
}
