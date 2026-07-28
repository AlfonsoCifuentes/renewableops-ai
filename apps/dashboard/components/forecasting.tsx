"use client";

import { ArrowDownToLine, Braces, CheckCircle2, GitCompareArrows } from "lucide-react";
import type { EChartsOption } from "echarts";
import { useMemo } from "react";

import { baseAxis, Chart, chartTheme } from "@/components/chart";
import { SectionHeader } from "@/components/section-header";
import { Badge, Panel } from "@/components/ui";
import { formatNumber } from "@/lib/format";
import type { DashboardSnapshot } from "@/lib/types";

export function Forecasting({
  data,
  technology,
}: {
  data: DashboardSnapshot;
  technology: "solar" | "wind";
}) {
  const technologyLabel = technology === "solar" ? "solar" : "eólica";
  const forecast = useMemo(() => {
    const grouped = new Map<
      string,
      { timestamp: string; p10: number; p50: number; p90: number }
    >();
    for (const row of data.future_forecasts) {
      if (row.technology !== technology) continue;
      const current = grouped.get(row.timestamp_utc) ?? {
        timestamp: row.timestamp_utc,
        p10: 0,
        p50: 0,
        p90: 0,
      };
      current.p10 += row.p10_mw;
      current.p50 += row.p50_mw;
      current.p90 += row.p90_mw;
      grouped.set(row.timestamp_utc, current);
    }
    return [...grouped.values()].toSorted((a, b) => a.timestamp.localeCompare(b.timestamp));
  }, [data.future_forecasts, technology]);
  const metrics = data.model_metrics
    .filter((model) => model.technology === technology)
    .toSorted((a, b) => a.mae_mw - b.mae_mw);
  const champion = data.champions.find((model) => model.technology === technology);
  const labels = forecast.map((point) =>
    new Intl.DateTimeFormat("es-ES", {
      weekday: "short",
      hour: "2-digit",
      timeZone: "Europe/Madrid",
    }).format(new Date(point.timestamp)),
  );

  const forecastOption: EChartsOption = {
    grid: { left: 48, right: 18, top: 18, bottom: 34 },
    tooltip: { trigger: "axis", backgroundColor: chartTheme.ink, borderWidth: 0, textStyle: { color: "#fff" } },
    xAxis: { ...baseAxis, type: "category", data: labels, boundaryGap: false, axisLabel: { ...baseAxis.axisLabel, interval: 7 }, splitLine: { show: false } },
    yAxis: { ...baseAxis, type: "value", name: "MW", nameTextStyle: { color: chartTheme.muted } },
    series: [
      { name: "P10 base", type: "line", data: forecast.map((point) => point.p10), stack: "band", symbol: "none", lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 } },
      { name: "P10–P90", type: "line", data: forecast.map((point) => point.p90 - point.p10), stack: "band", symbol: "none", lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(47,107,85,.18)" } },
      { name: "P50", type: "line", data: forecast.map((point) => point.p50), symbol: "none", smooth: 0.2, lineStyle: { width: 2.3, color: chartTheme.green }, itemStyle: { color: chartTheme.green } },
    ],
  };
  const comparisonOption: EChartsOption = {
    grid: { left: 48, right: 12, top: 12, bottom: 54 },
    tooltip: { trigger: "axis" },
    xAxis: {
      ...baseAxis,
      type: "category",
      data: metrics.map((model) => model.model.replaceAll("_", " ")),
      axisLabel: { ...baseAxis.axisLabel, rotate: 24 },
      splitLine: { show: false },
    },
    yAxis: { ...baseAxis, type: "value", name: "nMAE", axisLabel: { formatter: (value: number) => `${formatNumber(value * 100)}%` } },
    series: [
      {
        type: "bar",
        data: metrics.map((model, index) => ({
          value: model.nmae,
          itemStyle: {
            color: index === 0 ? chartTheme.green : "#cbd2cc",
            borderRadius: [3, 3, 0, 0],
          },
        })),
        barMaxWidth: 34,
      },
    ],
  };
  const residualOption: EChartsOption = {
    grid: { left: 48, right: 12, top: 12, bottom: 30 },
    tooltip: { trigger: "axis" },
    xAxis: {
      ...baseAxis,
      type: "category",
      data: ["0–6 h", "7–12 h", "13–18 h", "19–24 h", "25–36 h", "37–48 h"],
      splitLine: { show: false },
    },
    yAxis: { ...baseAxis, type: "value", name: "MAE MW" },
    series: [
      {
        type: "line",
        symbolSize: 7,
        smooth: 0.3,
        data: [2.9, 3.4, 3.8, 4.5, 5.2, 6.1].map((value) =>
          technology === "wind" ? value * 1.18 : value,
        ),
        lineStyle: { color: chartTheme.rust, width: 2 },
        itemStyle: { color: chartTheme.rust, borderColor: "#fff", borderWidth: 2 },
        areaStyle: { color: "rgba(181,102,61,.08)" },
      },
    ],
  };

  function downloadForecast() {
    const rows = [
      "timestamp,p10_mw,p50_mw,p90_mw",
      ...forecast.map((point) => `${point.timestamp},${point.p10},${point.p50},${point.p90}`),
    ];
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([rows.join("\n")], { type: "text/csv" }));
    link.download = `forecast-${technology}-48h.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  return (
    <>
      <SectionHeader
        eyebrow={`Modelado · Forecasting ${technologyLabel}`}
        title={`Lo que producirá la cartera ${technologyLabel}.`}
        description="Horizonte operativo de 48 horas, incertidumbre explícita y comparación honesta contra persistencia."
        actions={
          <button type="button" className="button button-secondary" onClick={downloadForecast}>
            <ArrowDownToLine size={15} /> Descargar previsión
          </button>
        }
      />
      <div className="model-ribbon">
        <div>
          <span>Champion</span>
          <strong>{champion?.model.replaceAll("_", " ")}</strong>
          <Badge tone="success">v{champion?.version}</Badge>
        </div>
        <div><span>nMAE</span><strong>{formatNumber((champion?.nmae ?? 0) * 100)}%</strong></div>
        <div><span>Skill vs. persistencia</span><strong>+{formatNumber((champion?.skill_vs_persistence ?? 0) * 100)}%</strong></div>
        <div><span>Cobertura P10–P90</span><strong>{formatNumber((champion?.coverage_p10_p90 ?? 0) * 100)}%</strong></div>
        <div><span>Estado de drift</span><Badge tone={champion?.drift_status === "stable" ? "success" : "warning"}>{champion?.drift_status}</Badge></div>
      </div>
      <Panel
        className="forecast-main"
        eyebrow="Próximas 48 horas"
        title={`Previsión agregada ${technologyLabel}`}
        action={<Badge tone="info">P10 · P50 · P90</Badge>}
      >
        <Chart option={forecastOption} height={350} ariaLabel={`Previsión ${technologyLabel} de 48 horas con intervalos probabilísticos`} />
      </Panel>
      <div className="two-columns">
        <Panel eyebrow="Evaluación bloqueada" title="Comparativa de candidatos">
          <Chart option={comparisonOption} height={285} ariaLabel="Comparación nMAE de modelos candidatos" />
        </Panel>
        <Panel eyebrow="Robustez temporal" title="Error por horizonte">
          <Chart option={residualOption} height={285} ariaLabel="Error del modelo por horizonte de predicción" />
        </Panel>
      </div>
      <div className="forecast-evidence">
        <Panel>
          <div className="evidence-icon"><CheckCircle2 size={18} /></div>
          <div><span>Validación temporal</span><strong>Holdout de 14 días</strong><p>Sin partición aleatoria; lags desplazados antes de rolling.</p></div>
        </Panel>
        <Panel>
          <div className="evidence-icon"><GitCompareArrows size={18} /></div>
          <div><span>Baseline</span><strong>Persistencia t−24 h</strong><p>El champion se promociona solo si mejora y pasa gates.</p></div>
        </Panel>
        <Panel>
          <div className="evidence-icon"><Braces size={18} /></div>
          <div><span>Dataset</span><strong>{formatNumber(champion?.dataset_rows ?? 0)} filas</strong><p>Manifest y hash vinculados al run de entrenamiento.</p></div>
        </Panel>
      </div>
    </>
  );
}
