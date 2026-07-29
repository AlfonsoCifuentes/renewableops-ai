"use client";

import {
  Activity,
  ArrowRight,
  CircleDollarSign,
  Clock3,
  Gauge,
  Info,
  RadioTower,
  Sparkles,
  TriangleAlert,
  Zap,
} from "lucide-react";
import type { EChartsOption } from "echarts";

import { baseAxis, Chart, chartTheme } from "@/components/chart";
import { FleetMap } from "@/components/fleet-map";
import { SectionHeader } from "@/components/section-header";
import { Badge, KpiCard, Panel, Sparkline, StatusDot } from "@/components/ui";
import { formatCurrency, formatInteger, formatNumber, labelForCause } from "@/lib/format";
import type { Asset, DashboardSnapshot } from "@/lib/types";

interface OverviewProps {
  data: DashboardSnapshot;
  assets: Asset[];
  onAssetSelect: (asset: Asset) => void;
  onDefinition: (id: string) => void;
  onSourceOpen: () => void;
  onNavigate: (path: string) => void;
}

export function Overview({
  data,
  assets,
  onAssetSelect,
  onDefinition,
  onSourceOpen,
  onNavigate,
}: OverviewProps) {
  const labels = data.series.map((point) =>
    new Intl.DateTimeFormat("es-ES", {
      weekday: "short",
      hour: "2-digit",
      timeZone: "Europe/Madrid",
    }).format(new Date(point.timestamp)),
  );
  const forecastOption: EChartsOption = {
    animationDuration: 650,
    grid: { left: 46, right: 18, top: 28, bottom: 32 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#17231f",
      borderWidth: 0,
      textStyle: { color: "#fff", fontSize: 11 },
    },
    legend: {
      right: 2,
      top: 0,
      itemWidth: 18,
      textStyle: { color: chartTheme.muted, fontSize: 10 },
      data: ["Real", "P50"],
    },
    xAxis: {
      ...baseAxis,
      type: "category",
      boundaryGap: false,
      data: labels,
      axisLabel: { ...baseAxis.axisLabel, interval: 15 },
      splitLine: { show: false },
    },
    yAxis: {
      ...baseAxis,
      type: "value",
      name: "MW",
      nameTextStyle: { color: chartTheme.muted, fontSize: 10 },
    },
    series: [
      {
        name: "Rango P10–P90",
        type: "line",
        data: data.series.map((point) => point.p90 - point.p10),
        stack: "confidence",
        symbol: "none",
        lineStyle: { opacity: 0 },
        areaStyle: { color: "rgba(47,107,85,.13)" },
      },
      {
        name: "P10",
        type: "line",
        data: data.series.map((point) => point.p10),
        stack: "confidence",
        symbol: "none",
        lineStyle: { opacity: 0 },
        areaStyle: { opacity: 0 },
      },
      {
        name: "P50",
        type: "line",
        data: data.series.map((point) => point.forecast),
        showSymbol: false,
        smooth: 0.22,
        lineStyle: { color: chartTheme.green, width: 2.2 },
        itemStyle: { color: chartTheme.green },
      },
      {
        name: "Real",
        type: "line",
        data: data.series.map((point) => point.actual),
        showSymbol: false,
        smooth: 0.18,
        lineStyle: { color: chartTheme.ink, width: 1.4 },
        itemStyle: { color: chartTheme.ink },
      },
    ],
  };
  const mixOption: EChartsOption = {
    tooltip: { trigger: "item", valueFormatter: (value) => `${formatInteger(Number(value))} MWh` },
    color: [chartTheme.sand, chartTheme.blue, chartTheme.green],
    series: [
      {
        type: "pie",
        radius: ["63%", "84%"],
        center: ["50%", "48%"],
        avoidLabelOverlap: true,
        label: { show: false },
        itemStyle: { borderColor: chartTheme.paper, borderWidth: 4 },
        data: data.mix.map((item) => ({
          name: item.technology,
          value: item.energy_mwh,
        })),
      },
    ],
    graphic: [
      {
        type: "text",
        left: "center",
        top: "38%",
        style: {
          text: `${formatInteger(data.mix.reduce((sum, item) => sum + item.energy_mwh, 0))}\nMWh`,
          align: "center",
          fill: chartTheme.ink,
          fontSize: 18,
          fontWeight: 650,
          lineHeight: 23,
        },
      },
    ],
  };

  const underperformers = [...assets]
    .sort((a, b) => b.mwh_at_risk - a.mwh_at_risk)
    .slice(0, 4);

  return (
    <>
      <SectionHeader
        eyebrow="Centro de operaciones · 28 julio 2026"
        title="La cartera, en una sola lectura."
        description="Predicción, rendimiento y riesgo operativo con trazabilidad hasta la fuente y el modelo."
        actions={
          <>
            <button type="button" className="button button-secondary" onClick={onSourceOpen}>
              <RadioTower size={15} />
              Fuentes
            </button>
            <button
              type="button"
              className="button button-primary"
              onClick={() => onNavigate("/scenario-lab")}
            >
              <Sparkles size={15} />
              Simular escenario
            </button>
          </>
        }
      />

      <div className="kpi-grid">
        <KpiCard
          label="Previsión 24 h"
          value={`${formatInteger(data.kpis.forecast_24h_mwh)} MWh`}
          context="P50 del portfolio"
          icon={<Zap size={17} />}
        />
        <KpiCard
          label="Disponibilidad"
          value={`${formatNumber(data.kpis.availability)}%`}
          context={`${data.kpis.assets_online} de ${data.kpis.assets_total} online`}
          tone="good"
          icon={<Gauge size={17} />}
          onInfo={() => onDefinition("availability")}
        />
        <KpiCard
          label="MWh en riesgo"
          value={formatNumber(data.kpis.mwh_at_risk)}
          context={`${data.kpis.active_anomalies} incidencias activas`}
          tone="warning"
          icon={<TriangleAlert size={17} />}
          onInfo={() => onDefinition("mwh_at_risk")}
        />
        <KpiCard
          label="Ingreso 7 días"
          value={formatCurrency(data.kpis.revenue_7d_eur)}
          context="Estimación day-ahead"
          icon={<CircleDollarSign size={17} />}
        />
        <KpiCard
          label="nMAE forecast"
          value={`${formatNumber(data.kpis.forecast_nmae)}%`}
          context="Champion · ventana 7 d"
          tone="good"
          icon={<Activity size={17} />}
          onInfo={() => onDefinition("forecast_nmae")}
        />
      </div>

      <div className="overview-layout">
        <Panel
          className="forecast-panel"
          eyebrow="Producción agregada"
          title="Real frente a previsión"
          action={
            <button className="text-button" type="button" onClick={() => onNavigate("/forecast-solar")}>
              Analizar forecast <ArrowRight size={14} />
            </button>
          }
        >
          <Chart
            option={forecastOption}
            height={318}
            ariaLabel="Serie temporal de producción real y previsión P50 con intervalo P10 a P90"
          />
          <div className="chart-footnote">
            <span><i className="line-key line-actual" />Real</span>
            <span><i className="line-key line-forecast" />P50</span>
            <span><i className="range-key" />Rango P10–P90</span>
            <span className="chart-freshness"><Clock3 size={12} /> Actualizado hace 7 min</span>
          </div>
        </Panel>

        <Panel className="mix-panel" eyebrow="Últimos 7 días" title="Mix operativo">
          <Chart option={mixOption} height={205} ariaLabel="Distribución de energía por tecnología" />
          <div className="mix-legend">
            {data.mix.map((item, index) => (
              <div key={item.technology}>
                <span><i data-index={index} />{item.technology}</span>
                <strong>{formatNumber(item.share)}%</strong>
              </div>
            ))}
          </div>
          <button className="text-button full-width" type="button" onClick={() => onNavigate("/market")}>
            Ver captura de mercado <ArrowRight size={14} />
          </button>
        </Panel>
      </div>

      <div className="overview-bottom">
        <Panel
          className="map-panel"
          eyebrow="Portfolio"
          title="Implantación y estado"
          action={<Badge tone="neutral">{assets.length} visibles</Badge>}
        >
          <FleetMap assets={assets} onSelect={onAssetSelect} />
        </Panel>

        <Panel
          className="risk-panel"
          eyebrow="Priorización"
          title="Activos bajo expectativa"
          action={
            <button className="icon-button" type="button" aria-label="Cómo se priorizan los activos">
              <Info size={15} />
            </button>
          }
        >
          <div className="risk-list">
            {underperformers.map((asset, index) => (
              <button
                type="button"
                className="risk-row"
                key={asset.asset_id}
                onClick={() => onAssetSelect(asset)}
              >
                <span className="rank">{String(index + 1).padStart(2, "0")}</span>
                <span className="risk-asset">
                  <strong>{asset.name}</strong>
                  <small>{asset.region} · {asset.technology_label}</small>
                </span>
                <Sparkline values={asset.sparkline} tone={asset.mwh_at_risk > 10 ? "rust" : "green"} />
                <span className="risk-number">
                  <strong>{formatNumber(asset.mwh_at_risk)} MWh</strong>
                  <small>en riesgo</small>
                </span>
              </button>
            ))}
          </div>
        </Panel>
      </div>

      <Panel
        className="alerts-strip"
        eyebrow="Ahora"
        title="Señales que requieren atención"
        action={
          <button className="text-button" type="button" onClick={() => onNavigate("/asset-health")}>
            Ver todas <ArrowRight size={14} />
          </button>
        }
      >
        <div className="alert-cards">
          {data.anomalies.slice(0, 3).map((anomaly) => (
            <button
              type="button"
              key={anomaly.incident_id}
              className="alert-card"
              onClick={() => {
                const asset = assets.find((item) => item.asset_id === anomaly.asset_id);
                if (asset) onAssetSelect(asset);
              }}
            >
              <StatusDot status={anomaly.severity} />
              <strong>{labelForCause(anomaly.labelled_cause)}</strong>
              <span>{anomaly.asset_name}</span>
              <small>{formatNumber(anomaly.mwh_at_risk)} MWh · confianza {formatNumber(anomaly.confidence * 100)}%</small>
            </button>
          ))}
        </div>
      </Panel>
    </>
  );
}
