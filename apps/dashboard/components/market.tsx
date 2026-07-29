"use client";

import { CircleDollarSign, CloudSun, TrendingDown, TrendingUp } from "lucide-react";
import type { EChartsOption } from "echarts";

import { baseAxis, Chart, chartTheme } from "@/components/chart";
import { SectionHeader } from "@/components/section-header";
import { KpiCard, Panel } from "@/components/ui";
import { formatCurrency, formatNumber } from "@/lib/format";
import type { DashboardSnapshot } from "@/lib/types";

export function Market({ data }: { data: DashboardSnapshot }) {
  const points = data.market;
  const labels = points.map((point) =>
    new Intl.DateTimeFormat("es-ES", {
      weekday: "short",
      hour: "2-digit",
      timeZone: "Europe/Madrid",
    }).format(new Date(point.timestamp)),
  );
  const averagePrice = points.reduce((sum, point) => sum + point.price, 0) / points.length;
  const negativeHours = points.filter((point) => point.price < 0).length;
  const capturePrice =
    points.reduce((sum, point) => sum + point.price * point.generation, 0) /
    points.reduce((sum, point) => sum + point.generation, 0);
  const captureRates = [
    data.market_capture_rates.solar,
    data.market_capture_rates.wind,
    data.market_capture_rates.portfolio,
  ];
  const priceOption: EChartsOption = {
    grid: { left: 48, right: 48, top: 26, bottom: 36 },
    tooltip: { trigger: "axis" },
    legend: { top: 0, right: 0, textStyle: { color: chartTheme.muted } },
    xAxis: { ...baseAxis, type: "category", data: labels, axisLabel: { ...baseAxis.axisLabel, interval: 18 }, splitLine: { show: false } },
    yAxis: [
      { ...baseAxis, type: "value", name: "€/MWh" },
      { ...baseAxis, type: "value", name: "MW", splitLine: { show: false } },
    ],
    series: [
      {
        name: "Precio",
        type: "line",
        data: points.map((point) => point.price),
        symbol: "none",
        smooth: 0.22,
        lineStyle: { color: chartTheme.rust, width: 2.1 },
        areaStyle: { color: "rgba(181,102,61,.09)" },
      },
      {
        name: "Generación",
        type: "bar",
        yAxisIndex: 1,
        data: points.map((point) => point.generation),
        itemStyle: { color: "rgba(47,107,85,.32)", borderRadius: [2, 2, 0, 0] },
        barMaxWidth: 9,
      },
    ],
  };
  const duration = [...points.map((point) => point.price)].toSorted((a, b) => b - a);
  const durationOption: EChartsOption = {
    grid: { left: 48, right: 12, top: 10, bottom: 32 },
    tooltip: { trigger: "axis" },
    xAxis: { ...baseAxis, type: "category", data: duration.map((_, index) => index + 1), axisLabel: { formatter: (value: string) => `${value} h` }, splitLine: { show: false } },
    yAxis: { ...baseAxis, type: "value", name: "€/MWh" },
    series: [{ type: "line", data: duration, symbol: "none", lineStyle: { color: chartTheme.ink, width: 2 }, markLine: { silent: true, data: [{ yAxis: 0 }], lineStyle: { color: chartTheme.rust, type: "dashed" } } }],
  };
  const captureOption: EChartsOption = {
    grid: { left: 90, right: 18, top: 8, bottom: 24 },
    xAxis: {
      ...baseAxis,
      type: "value",
      max: Math.max(100, Math.ceil(Math.max(...captureRates) / 10) * 10),
      axisLabel: { formatter: "{value}%" },
    },
    yAxis: { ...baseAxis, type: "category", data: ["Solar", "Eólica", "Portfolio"], splitLine: { show: false } },
    series: [{
      type: "bar",
      data: captureRates,
      barWidth: 18,
      itemStyle: { color: (params: { dataIndex: number }) => [chartTheme.sand, chartTheme.blue, chartTheme.green][params.dataIndex], borderRadius: [0, 3, 3, 0] },
      label: { show: true, position: "right", formatter: "{c}%", color: chartTheme.ink, fontWeight: 600 },
    }],
  };

  return (
    <>
      <SectionHeader
        eyebrow="Mercado eléctrico · MIBEL"
        title="Energía y precio, en contexto."
        description="Captura de valor, exposición horaria y relación entre generación renovable y mercado day-ahead."
      />
      <div className="kpi-grid kpi-grid-four">
        <KpiCard label="Precio medio" value={`${formatNumber(averagePrice)} €/MWh`} context="Últimos 5 días" icon={<CircleDollarSign size={17} />} />
        <KpiCard label="Precio de captura" value={`${formatNumber(capturePrice)} €/MWh`} context="Portfolio renovable" icon={<TrendingUp size={17} />} />
        <KpiCard label="Horas negativas" value={`${negativeHours} h`} context="Ventana analizada" tone="good" icon={<TrendingDown size={17} />} />
        <KpiCard label="Ingreso estimado" value={formatCurrency(data.kpis.revenue_7d_eur)} context="No es liquidación" icon={<CloudSun size={17} />} />
      </div>
      <Panel eyebrow="Serie combinada" title="Precio y generación">
        <Chart option={priceOption} height={360} ariaLabel="Precio day-ahead y generación renovable por hora" />
      </Panel>
      <div className="two-columns">
        <Panel eyebrow="Distribución" title="Curva de duración de precios">
          <Chart option={durationOption} height={285} ariaLabel="Curva de duración de precios" />
        </Panel>
        <Panel eyebrow="Monetización" title="Capture rate por tecnología">
          <Chart option={captureOption} height={285} ariaLabel="Tasa de captura por tecnología" />
        </Panel>
      </div>
    </>
  );
}
