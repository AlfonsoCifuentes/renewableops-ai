"use client";

import { BatteryCharging, SunMedium, Wind } from "lucide-react";

import type { Asset } from "@/lib/types";

interface FleetMapProps {
  assets: Asset[];
  selectedId?: string;
  onSelect: (asset: Asset) => void;
}

function position(asset: Asset) {
  const left = ((asset.longitude + 9.5) / 12.7) * 78 + 10;
  const top = ((44.2 - asset.latitude) / 8.5) * 73 + 11;
  return {
    left: `${Math.min(92, Math.max(6, left))}%`,
    top: `${Math.min(90, Math.max(8, top))}%`,
  };
}

export function FleetMap({ assets, selectedId, onSelect }: FleetMapProps) {
  return (
    <div className="fleet-map">
      <div className="map-caption">
        <span>España peninsular</span>
        <span>{assets.length} activos visibles</span>
      </div>
      <svg
        className="spain-shape"
        viewBox="0 0 520 390"
        role="img"
        aria-label="Mapa simplificado de los activos en España"
      >
        <defs>
          <pattern id="map-grid" width="22" height="22" patternUnits="userSpaceOnUse">
            <path d="M 22 0 L 0 0 0 22" fill="none" stroke="#d7dbd5" strokeWidth=".7" />
          </pattern>
        </defs>
        <path
          d="M86 68L149 42L205 52L250 37L329 44L385 74L437 80L471 118L456 157L476 191L443 223L421 274L370 294L325 342L274 338L230 315L180 319L151 285L110 269L89 226L55 193L67 146L49 112Z"
          fill="url(#map-grid)"
          stroke="#aeb8af"
          strokeWidth="2"
        />
        <path
          d="M97 101C173 83 238 92 302 76M112 171C184 148 301 158 426 132M120 244C230 209 325 231 414 204"
          fill="none"
          stroke="#d3d8d2"
          strokeWidth="1"
          strokeDasharray="5 7"
        />
      </svg>
      <div className="map-markers" role="group" aria-label="Activos del portfolio">
        {assets.map((asset) => {
          const Icon =
            asset.technology === "solar"
              ? SunMedium
              : asset.technology === "wind"
                ? Wind
                : BatteryCharging;
          return (
            <button
              type="button"
              key={asset.asset_id}
              className={`map-marker marker-${asset.technology} ${
                selectedId === asset.asset_id ? "is-selected" : ""
              } ${asset.status === "attention" ? "has-alert" : ""}`}
              style={position(asset)}
              onClick={() => onSelect(asset)}
              aria-label={`${asset.name}, ${asset.technology_label}, ${asset.status}`}
            >
              <Icon size={14} strokeWidth={1.8} />
              <span className="marker-tooltip">
                <strong>{asset.name}</strong>
                <small>
                  {asset.current_power_mw.toLocaleString("es-ES")} MW · {asset.status}
                </small>
              </span>
            </button>
          );
        })}
      </div>
      <div className="map-legend" role="group" aria-label="Leyenda">
        <span><i className="legend-solar" />Solar</span>
        <span><i className="legend-wind" />Eólica</span>
        <span><i className="legend-battery" />Batería</span>
      </div>
    </div>
  );
}
