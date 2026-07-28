"use client";

import { ArrowDownToLine, ArrowUpDown, Search } from "lucide-react";
import { useDeferredValue, useMemo, useState } from "react";

import { FleetMap } from "@/components/fleet-map";
import { SectionHeader } from "@/components/section-header";
import { Badge, Panel, Sparkline, StatusDot } from "@/components/ui";
import { formatCurrency, formatNumber } from "@/lib/format";
import type { Asset } from "@/lib/types";

export function Fleet({
  assets,
  onAssetSelect,
}: {
  assets: Asset[];
  onAssetSelect: (asset: Asset) => void;
}) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<"risk" | "power" | "availability">("risk");
  const deferredQuery = useDeferredValue(query.toLocaleLowerCase("es-ES"));
  const filtered = useMemo(() => {
    const rows = assets.filter((asset) =>
      `${asset.name} ${asset.code} ${asset.region} ${asset.technology_label}`
        .toLocaleLowerCase("es-ES")
        .includes(deferredQuery),
    );
    return rows.toSorted((left, right) => {
      if (sort === "power") return right.current_power_mw - left.current_power_mw;
      if (sort === "availability") return right.availability - left.availability;
      return right.mwh_at_risk - left.mwh_at_risk;
    });
  }, [assets, deferredQuery, sort]);

  function exportCsv() {
    const header = "asset_id,name,technology,region,capacity_mw,current_power_mw,availability,mwh_at_risk";
    const body = filtered.map((asset) =>
      [
        asset.asset_id,
        `"${asset.name}"`,
        asset.technology,
        `"${asset.region}"`,
        asset.capacity_mw,
        asset.current_power_mw,
        asset.availability,
        asset.mwh_at_risk,
      ].join(","),
    );
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([[header, ...body].join("\n")], { type: "text/csv" }));
    link.download = "renewableops-fleet.csv";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  return (
    <>
      <SectionHeader
        eyebrow="Portfolio · 12 activos sintéticos"
        title="Flota renovable"
        description="Capacidad, producción y salud operacional con detalle trazable por activo."
        actions={
          <button type="button" className="button button-secondary" onClick={exportCsv}>
            <ArrowDownToLine size={15} /> Exportar CSV
          </button>
        }
      />
      <div className="fleet-summary">
        <div><span>Capacidad instalada</span><strong>{formatNumber(assets.reduce((sum, asset) => sum + asset.capacity_mw, 0))} MW</strong></div>
        <div><span>Potencia actual</span><strong>{formatNumber(assets.reduce((sum, asset) => sum + Math.max(0, asset.current_power_mw), 0))} MW</strong></div>
        <div><span>Disponibilidad media</span><strong>{formatNumber(assets.reduce((sum, asset) => sum + asset.availability, 0) / Math.max(assets.length, 1))}%</strong></div>
        <div><span>Ingreso semanal</span><strong>{formatCurrency(assets.reduce((sum, asset) => sum + asset.revenue_7d_eur, 0))}</strong></div>
      </div>
      <Panel className="fleet-map-panel">
        <FleetMap assets={filtered} onSelect={onAssetSelect} />
      </Panel>
      <Panel
        eyebrow="Vista operativa"
        title={`${filtered.length} activos`}
        action={
          <div className="table-tools">
            <label className="search-field">
              <Search size={14} />
              <span className="sr-only">Buscar activo</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Buscar activo o región"
              />
            </label>
            <label className="select-field compact">
              <ArrowUpDown size={14} />
              <span className="sr-only">Ordenar por</span>
              <select value={sort} onChange={(event) => setSort(event.target.value as typeof sort)}>
                <option value="risk">Mayor riesgo</option>
                <option value="power">Mayor potencia</option>
                <option value="availability">Disponibilidad</option>
              </select>
            </label>
          </div>
        }
      >
        <div className="table-scroll">
          <table className="data-table fleet-table">
            <thead>
              <tr>
                <th>Activo</th>
                <th>Tecnología</th>
                <th>Estado</th>
                <th>Tendencia</th>
                <th className="number-cell">Ahora</th>
                <th className="number-cell">Disponib.</th>
                <th className="number-cell">Factor</th>
                <th className="number-cell">Riesgo</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((asset) => (
                <tr key={asset.asset_id} onClick={() => onAssetSelect(asset)}>
                  <td>
                    <button className="asset-cell" type="button" onClick={() => onAssetSelect(asset)}>
                      <strong>{asset.name}</strong>
                      <small>{asset.code} · {asset.region}</small>
                    </button>
                  </td>
                  <td><Badge tone="neutral">{asset.technology_label}</Badge></td>
                  <td><StatusDot status={asset.status} /></td>
                  <td><Sparkline values={asset.sparkline} tone={asset.mwh_at_risk > 10 ? "rust" : "green"} /></td>
                  <td className="number-cell">{formatNumber(asset.current_power_mw)} MW</td>
                  <td className="number-cell">{formatNumber(asset.availability)}%</td>
                  <td className="number-cell">{formatNumber(asset.capacity_factor)}%</td>
                  <td className="number-cell">
                    <span className={asset.mwh_at_risk > 10 ? "value-warning" : ""}>
                      {formatNumber(asset.mwh_at_risk)} MWh
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </>
  );
}
