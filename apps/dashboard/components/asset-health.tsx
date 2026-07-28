"use client";

import { ArrowRight, ShieldAlert } from "lucide-react";
import type { EChartsOption } from "echarts";

import { baseAxis, Chart, chartTheme } from "@/components/chart";
import { SectionHeader } from "@/components/section-header";
import { Badge, Panel, StatusDot } from "@/components/ui";
import { formatCurrency, formatDate, formatNumber, labelForCause } from "@/lib/format";
import type { Asset, DashboardSnapshot } from "@/lib/types";

export function AssetHealth({
  data,
  onAssetSelect,
}: {
  data: DashboardSnapshot;
  onAssetSelect: (asset: Asset) => void;
}) {
  const severityCounts = ["critical", "high", "medium", "low"].map(
    (severity) => data.anomalies.filter((item) => item.severity === severity).length,
  );
  const severityOption: EChartsOption = {
    color: ["#7f382b", chartTheme.rust, chartTheme.sand, chartTheme.greenSoft],
    tooltip: { trigger: "item" },
    series: [{
      type: "pie",
      radius: ["58%", "82%"],
      label: { show: false },
      itemStyle: { borderWidth: 3, borderColor: chartTheme.paper },
      data: ["Crítica", "Alta", "Media", "Baja"].map((name, index) => ({ name, value: severityCounts[index] })),
    }],
    graphic: [{ type: "text", left: "center", top: "42%", style: { text: String(data.anomalies.length), fill: chartTheme.ink, fontSize: 24, fontWeight: 700 } }],
  };
  const riskOption: EChartsOption = {
    grid: { left: 126, right: 18, top: 8, bottom: 28 },
    xAxis: { ...baseAxis, type: "value", name: "MWh" },
    yAxis: { ...baseAxis, type: "category", data: data.anomalies.slice(0, 6).map((item) => item.asset_name), splitLine: { show: false } },
    series: [{ type: "bar", data: data.anomalies.slice(0, 6).map((item) => item.mwh_at_risk), barWidth: 17, itemStyle: { color: chartTheme.rust, borderRadius: [0, 3, 3, 0] } }],
  };

  return (
    <>
      <SectionHeader
        eyebrow="Detección multicapa · Operaciones"
        title="Salud de activos"
        description="Reglas físicas, residuales y aprendizaje no supervisado convertidos en incidencias accionables."
      />
      <div className="health-summary">
        <Panel className="health-total">
          <ShieldAlert size={20} />
          <div><span>Incidencias abiertas</span><strong>{data.anomalies.length}</strong></div>
          <small>{formatNumber(data.kpis.mwh_at_risk)} MWh potencialmente afectados</small>
        </Panel>
        <Panel className="health-chart"><Chart option={severityOption} height={170} ariaLabel="Incidencias por severidad" /></Panel>
        <Panel className="health-risk" eyebrow="Exposición" title="MWh en riesgo por activo">
          <Chart option={riskOption} height={210} ariaLabel="Energía en riesgo por activo" />
        </Panel>
      </div>
      <Panel
        eyebrow="Cola operativa"
        title="Incidencias priorizadas"
        action={<Badge tone="warning">{data.anomalies.length} requieren revisión</Badge>}
      >
        <div className="incident-list">
          {data.anomalies.map((incident) => {
            const asset = data.assets.find((item) => item.asset_id === incident.asset_id);
            return (
              <article className="incident-row" key={incident.incident_id}>
                <div className="incident-id">
                  <StatusDot status={incident.severity} />
                  <small>{incident.incident_id}</small>
                </div>
                <div className="incident-main">
                  <strong>{labelForCause(incident.labelled_cause)}</strong>
                  <span>{incident.asset_name} · desde {formatDate(incident.started_at, true)}</span>
                  <p>{incident.recommended_action}</p>
                </div>
                <div className="incident-evidence">
                  <span>Confianza <strong>{formatNumber(incident.confidence * 100)}%</strong></span>
                  <span>Impacto <strong>{formatNumber(incident.mwh_at_risk)} MWh</strong></span>
                  <span>Valor <strong>{formatCurrency(incident.estimated_impact_eur)}</strong></span>
                </div>
                <button
                  type="button"
                  className="icon-button"
                  aria-label={`Abrir ${incident.asset_name}`}
                  disabled={!asset}
                  onClick={() => asset && onAssetSelect(asset)}
                >
                  <ArrowRight size={16} />
                </button>
              </article>
            );
          })}
        </div>
      </Panel>
    </>
  );
}
