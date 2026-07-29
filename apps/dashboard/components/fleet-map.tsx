"use client";

import { BatteryCharging, SunMedium, Wind } from "lucide-react";
import { useId, useMemo, useState } from "react";

import {
  projectSpainCoordinate,
  SPAIN_MAINLAND_PATH,
  SPAIN_MAP_VIEWBOX,
  type SpainMapPoint,
} from "@/lib/spain-map";
import type { Asset } from "@/lib/types";

interface FleetMapProps {
  assets: Asset[];
  selectedId?: string;
  onSelect: (asset: Asset) => void;
}

interface MarkerLayout {
  asset: Asset;
  anchor: SpainMapPoint;
  offset: SpainMapPoint;
}

const COLLISION_DISTANCE = 38;

function distanceBetween(first: MarkerLayout, second: MarkerLayout) {
  return Math.hypot(first.anchor.x - second.anchor.x, first.anchor.y - second.anchor.y);
}

function spreadOffset(index: number, total: number): SpainMapPoint {
  if (total === 1) {
    return { x: 0, y: 0 };
  }

  const radius = total === 2 ? 30 : 35;
  const angle = (-90 + (index * 360) / total) * (Math.PI / 180);
  return {
    x: Math.cos(angle) * radius,
    y: Math.sin(angle) * radius,
  };
}

function layoutMarkers(assets: Asset[]): MarkerLayout[] {
  const remaining = assets.map((asset) => ({
    asset,
    anchor: projectSpainCoordinate(asset.longitude, asset.latitude),
    offset: { x: 0, y: 0 },
  }));
  const groups: MarkerLayout[][] = [];

  while (remaining.length > 0) {
    const group = [remaining.shift()!];
    let groupExpanded = true;

    while (groupExpanded) {
      groupExpanded = false;
      for (let index = remaining.length - 1; index >= 0; index -= 1) {
        if (group.some((member) => distanceBetween(member, remaining[index]) < COLLISION_DISTANCE)) {
          group.push(remaining.splice(index, 1)[0]);
          groupExpanded = true;
        }
      }
    }

    groups.push(group);
  }

  return groups.flatMap((group) =>
    group.map((marker, index) => ({
      ...marker,
      offset: spreadOffset(index, group.length),
    })),
  );
}

export function FleetMap({ assets, selectedId, onSelect }: FleetMapProps) {
  const [hoveredId, setHoveredId] = useState<string>();
  const mapId = useId().replaceAll(":", "");
  const markers = useMemo(() => layoutMarkers(assets), [assets]);
  const activeMarker = markers.find((marker) => marker.asset.asset_id === hoveredId);
  const clipPathId = `${mapId}-mainland-clip`;
  const gridPatternId = `${mapId}-coordinate-grid`;
  const fillGradientId = `${mapId}-land-fill`;
  const titleId = `${mapId}-map-title`;
  const tooltipPosition = activeMarker
    ? {
        x: Math.min(
          SPAIN_MAP_VIEWBOX.width - 198,
          Math.max(10, activeMarker.anchor.x + activeMarker.offset.x - 94),
        ),
        y:
          activeMarker.anchor.y + activeMarker.offset.y < 86
            ? activeMarker.anchor.y + activeMarker.offset.y + 30
            : activeMarker.anchor.y + activeMarker.offset.y - 70,
      }
    : undefined;

  return (
    <div className="fleet-map">
      <div className="map-caption">
        <span>España peninsular</span>
        <span>{assets.length} activos visibles</span>
      </div>
      <svg
        className="spain-map"
        viewBox={`0 0 ${SPAIN_MAP_VIEWBOX.width} ${SPAIN_MAP_VIEWBOX.height}`}
        role="group"
        aria-labelledby={titleId}
        onPointerLeave={() => setHoveredId(undefined)}
      >
        <title id={titleId}>
          Mapa geográfico de los activos del portfolio en España peninsular
        </title>
        <defs>
          <linearGradient id={fillGradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" className="spain-fill-start" />
            <stop offset="1" className="spain-fill-end" />
          </linearGradient>
          <pattern id={gridPatternId} width="28" height="28" patternUnits="userSpaceOnUse">
            <path className="spain-grid-line" d="M 28 0 L 0 0 0 28" />
          </pattern>
          <clipPath id={clipPathId}>
            <path d={SPAIN_MAINLAND_PATH} />
          </clipPath>
        </defs>

        <g className="map-water-labels" aria-hidden="true">
          <text x="22" y="352">Atlántico</text>
          <text x="380" y="22" textAnchor="middle">Cantábrico</text>
          <text x="718" y="382" textAnchor="end">Mediterráneo</text>
        </g>

        <path
          className="spain-land"
          d={SPAIN_MAINLAND_PATH}
          fill={`url(#${fillGradientId})`}
        />
        <path
          className="spain-grid"
          d={SPAIN_MAINLAND_PATH}
          fill={`url(#${gridPatternId})`}
        />

        <g className="spain-coordinate-lines" clipPath={`url(#${clipPathId})`} aria-hidden="true">
          {[-8, -6, -4, -2, 0, 2].map((longitude) => {
            const start = projectSpainCoordinate(longitude, 36);
            const end = projectSpainCoordinate(longitude, 43.8);
            return (
              <line
                key={`longitude-${longitude}`}
                x1={start.x}
                y1={start.y}
                x2={end.x}
                y2={end.y}
              />
            );
          })}
          {[37, 39, 41, 43].map((latitude) => {
            const start = projectSpainCoordinate(-9.3, latitude);
            const end = projectSpainCoordinate(3.4, latitude);
            return (
              <line
                key={`latitude-${latitude}`}
                x1={start.x}
                y1={start.y}
                x2={end.x}
                y2={end.y}
              />
            );
          })}
        </g>

        <g className="map-marker-layer" role="group" aria-label="Activos del portfolio">
          {markers.map(({ asset, anchor, offset }) => {
            const Icon =
              asset.technology === "solar"
                ? SunMedium
                : asset.technology === "wind"
                  ? Wind
                  : BatteryCharging;
            const hasLeader = offset.x !== 0 || offset.y !== 0;
            const markerTitle = `${asset.name} · ${asset.current_power_mw.toLocaleString(
              "es-ES",
            )} MW · ${asset.municipality}`;

            return (
              <g
                key={asset.asset_id}
                className={`map-marker-svg marker-${asset.technology} ${
                  selectedId === asset.asset_id ? "is-selected" : ""
                } ${asset.status === "attention" ? "has-alert" : ""}`}
                transform={`translate(${anchor.x} ${anchor.y})`}
                role="button"
                tabIndex={0}
                focusable="true"
                onClick={() => onSelect(asset)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelect(asset);
                  }
                }}
                onPointerEnter={() => setHoveredId(asset.asset_id)}
                onFocus={() => setHoveredId(asset.asset_id)}
                onBlur={() => setHoveredId(undefined)}
                aria-label={`${asset.name}, ${asset.technology_label}, ${asset.municipality}, ${asset.status}`}
              >
                <title>{markerTitle}</title>
                {hasLeader ? (
                  <line
                    className="map-marker-leader"
                    x1="0"
                    y1="0"
                    x2={offset.x}
                    y2={offset.y}
                  />
                ) : null}
                <circle className="map-coordinate-anchor" r="3.2" />
                <g className="map-marker-button" transform={`translate(${offset.x} ${offset.y})`}>
                  <circle className="map-marker-halo" r="22" />
                  <circle className="map-marker-core" r="17" />
                  <Icon
                    x="-9"
                    y="-9"
                    width="18"
                    height="18"
                    strokeWidth={1.9}
                    aria-hidden="true"
                  />
                  {asset.status === "attention" ? (
                    <circle className="map-marker-alert" cx="13" cy="-13" r="4.5" />
                  ) : null}
                </g>
              </g>
            );
          })}
        </g>

        {activeMarker && tooltipPosition ? (
          <g
            className="map-svg-tooltip"
            transform={`translate(${tooltipPosition.x} ${tooltipPosition.y})`}
            aria-hidden="true"
          >
            <rect width="188" height="48" rx="5" />
            <text x="12" y="19" className="map-tooltip-name">
              {activeMarker.asset.name}
            </text>
            <text x="12" y="36" className="map-tooltip-detail">
              {activeMarker.asset.current_power_mw.toLocaleString("es-ES")} MW ·{" "}
              {activeMarker.asset.municipality}
            </text>
          </g>
        ) : null}
      </svg>
      <div className="map-source">WGS 84 · Cartografía GISCO 2024</div>
      <div className="map-legend" role="group" aria-label="Leyenda">
        <span><i className="legend-solar" />Solar</span>
        <span><i className="legend-wind" />Eólica</span>
        <span><i className="legend-battery" />Batería</span>
      </div>
    </div>
  );
}
