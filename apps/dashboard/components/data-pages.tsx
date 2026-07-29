"use client";

import {
  ArrowDownToLine,
  CheckCircle2,
  Database,
  GitBranch,
  RotateCcw,
  Search,
  ShieldCheck,
} from "lucide-react";
import type { EChartsOption } from "echarts";
import { useMemo, useState } from "react";

import { baseAxis, Chart, chartTheme } from "@/components/chart";
import { SectionHeader } from "@/components/section-header";
import { Badge, Panel, StatusDot } from "@/components/ui";
import { formatNumber } from "@/lib/format";
import type { DashboardSnapshot } from "@/lib/types";

export function DataExplorer({ data }: { data: DashboardSnapshot }) {
  const datasets = ["assets", "anomalies", "forecasts", "inspections", "sources"] as const;
  const [dataset, setDataset] = useState<(typeof datasets)[number]>("assets");
  const [query, setQuery] = useState("");
  const rows = useMemo(() => {
    const selected = {
      assets: data.assets,
      anomalies: data.anomalies,
      forecasts: data.future_forecasts.slice(0, 100),
      inspections: data.inspections,
      sources: data.sources,
    }[dataset] as unknown as Record<string, unknown>[];
    if (!query) return selected;
    return selected.filter((row) =>
      JSON.stringify(row).toLocaleLowerCase("es-ES").includes(query.toLocaleLowerCase("es-ES")),
    );
  }, [data, dataset, query]);
  const columns = Object.keys(rows[0] ?? {}).slice(0, 7);

  function exportRows() {
    const csv = [
      columns.join(","),
      ...rows.map((row) => columns.map((column) => JSON.stringify(row[column] ?? "")).join(",")),
    ];
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([csv.join("\n")], { type: "text/csv" }));
    link.download = `${dataset}-sample.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  return (
    <>
      <SectionHeader
        eyebrow="Gold marts · Consulta segura"
        title="Explorador de datos"
        description="Muestras saneadas, esquema, procedencia y descarga acotada. La demo pública no ejecuta SQL arbitrario."
        actions={<button type="button" className="button button-secondary" onClick={exportRows}><ArrowDownToLine size={15} /> Exportar muestra</button>}
      />
      <div className="explorer-layout">
        <Panel className="dataset-list" eyebrow="Catálogo" title="Datasets">
          {datasets.map((item) => (
            <button type="button" key={item} className={dataset === item ? "is-active" : ""} onClick={() => setDataset(item)}>
              <Database size={15} />
              <span><strong>{item}</strong><small>public/latest/{item}.json</small></span>
              <Badge tone="success">valid</Badge>
            </button>
          ))}
        </Panel>
        <Panel
          className="dataset-preview"
          eyebrow="Muestra"
          title={`${dataset} · ${rows.length} filas`}
          action={
            <label className="search-field">
              <Search size={14} />
              <span className="sr-only">Filtrar filas</span>
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filtrar muestra" />
            </label>
          }
        >
          <div className="schema-strip">
            {columns.map((column) => <span key={column}>{column}<small>inferred</small></span>)}
          </div>
          <div className="table-scroll">
            <table className="data-table compact-table">
              <thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
              <tbody>
                {rows.slice(0, 12).map((row, rowIndex) => (
                  <tr key={`${dataset}-${rowIndex}`}>
                    {columns.map((column) => <td key={column}>{String(row[column] ?? "—")}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="lineage-mini">
            <GitBranch size={15} />
            <span>Fuente → Bronze → Silver/Pandas → Gold → snapshot saneado</span>
            <Badge tone="success">checksum verified</Badge>
          </div>
        </Panel>
      </div>
    </>
  );
}

export function DataQuality({ data }: { data: DashboardSnapshot }) {
  const summary = data.quality_summary;
  const qualityOption: EChartsOption = {
    grid: { left: 130, right: 12, top: 24, bottom: 28 },
    tooltip: { trigger: "axis" },
    legend: { top: 0, right: 0, textStyle: { color: chartTheme.muted, fontSize: 10 } },
    xAxis: { ...baseAxis, type: "value", min: 88, max: 100, axisLabel: { formatter: "{value}%" } },
    yAxis: { ...baseAxis, type: "category", data: data.quality.map((row) => row.dataset), splitLine: { show: false } },
    series: [
      { name: "Freshness", type: "bar", data: data.quality.map((row) => row.freshness), itemStyle: { color: chartTheme.blue } },
      { name: "Completeness", type: "bar", data: data.quality.map((row) => row.completeness), itemStyle: { color: chartTheme.green } },
      { name: "Validity", type: "bar", data: data.quality.map((row) => row.validity), itemStyle: { color: chartTheme.sand } },
    ],
  };
  return (
    <>
      <SectionHeader eyebrow="Data contracts · Calidad" title="Datos confiables, fallos visibles." description="Freshness, completitud, validez y estabilidad de esquema con cuarentena explícita." />
      <div className="quality-kpis">
        <div><span>Checks ejecutados</span><strong>{summary.checks_executed}</strong><small>{summary.checks_passed} passed · {summary.checks_watch_or_failed} watch/failed</small></div>
        <div><span>Filas en cuarentena</span><strong>{summary.quarantined_rows}</strong><small>{formatNumber(summary.quarantined_rate, 3)}% del lote</small></div>
        <div><span>Schema changes</span><strong>{summary.schema_changes_detected}</strong><small>en la materialización actual</small></div>
        <div><span>Validez global</span><strong>{formatNumber(summary.overall_validity)}%</strong><small>medida sobre artefactos versionados</small></div>
      </div>
      <Panel eyebrow="Última materialización" title="Calidad por dataset">
        <Chart option={qualityOption} height={350} ariaLabel="Métricas de calidad por dataset" />
      </Panel>
      <Panel eyebrow="Contratos" title="Estado de validaciones">
        <div className="quality-list">
          {data.quality.map((row) => (
            <article key={row.dataset}>
              <StatusDot status={row.status} />
              <div><strong>{row.dataset}</strong><span>Schema v1 · UTC · claves únicas</span></div>
              <span>Freshness <strong>{formatNumber(row.freshness)}%</strong></span>
              <span>Completeness <strong>{formatNumber(row.completeness)}%</strong></span>
              <span>Validity <strong>{formatNumber(row.validity)}%</strong></span>
            </article>
          ))}
        </div>
      </Panel>
    </>
  );
}

export function Mlops({ data }: { data: DashboardSnapshot }) {
  const comparison: EChartsOption = {
    grid: { left: 50, right: 12, top: 14, bottom: 62 },
    tooltip: { trigger: "axis" },
    xAxis: { ...baseAxis, type: "category", data: data.model_metrics.map((item) => `${item.technology}\n${item.model}`), axisLabel: { ...baseAxis.axisLabel, rotate: 24 }, splitLine: { show: false } },
    yAxis: { ...baseAxis, type: "value", name: "nMAE", axisLabel: { formatter: (value: number) => `${formatNumber(value * 100)}%` } },
    series: [{ type: "bar", data: data.model_metrics.map((item) => item.nmae), itemStyle: { color: (params: { dataIndex: number }) => params.dataIndex % 3 === 0 ? chartTheme.green : "#bfc7c0", borderRadius: [3, 3, 0, 0] }, barMaxWidth: 28 }],
  };
  return (
    <>
      <SectionHeader eyebrow="Registry · MLflow" title="Modelos con criterio de promoción." description="Champion y challengers comparados por precisión, robustez, latencia, drift y aprobación humana." />
      <div className="champion-grid">
        {data.champions.map((model) => (
          <Panel key={model.technology} className="champion-card">
            <div className="champion-top"><Badge tone="success">champion</Badge><span>{model.technology}</span></div>
            <h2>{model.model.replaceAll("_", " ")}</h2>
            <p>v{model.version} · {model.stage}</p>
            <div className="champion-metrics">
              <div><span>nMAE</span><strong>{formatNumber(model.nmae * 100)}%</strong></div>
              <div><span>Skill</span><strong>+{formatNumber(model.skill_vs_persistence * 100)}%</strong></div>
              <div><span>Coverage</span><strong>{formatNumber(model.coverage_p10_p90 * 100)}%</strong></div>
              <div><span>Drift PSI</span><strong>{model.drift_max_psi === null || model.drift_max_psi === undefined ? "—" : formatNumber(model.drift_max_psi, 3)}</strong></div>
            </div>
            <p>Selección: {model.validation_folds} folds temporales · gap {model.validation_gap_hours} h · MAE {formatNumber(model.validation_mae_mw, 3)} MW</p>
            <div className="approval-line"><ShieldCheck size={15} /><span>{model.approved_by}</span></div>
          </Panel>
        ))}
        {data.challengers.map((model) => (
          <Panel className="challenger-card" key={`challenger-${model.technology}`}>
            <Badge tone="warning">challenger</Badge>
            <h2>{model.technology} · {model.model.replaceAll("_", " ")}</h2>
            <p>v{model.version} · {model.stage}</p>
            <div className="gate-list">
              <span><CheckCircle2 size={14} /> Métricas temporales registradas</span>
              <span><CheckCircle2 size={14} /> Artefacto reproducible</span>
              <span className="gate-wait"><RotateCcw size={14} /> Aprobación humana pendiente</span>
            </div>
            <button type="button" className="button button-secondary" disabled>No desplegado</button>
          </Panel>
        ))}
      </div>
      <Panel eyebrow="Experimentos" title="Comparación temporal">
        <Chart option={comparison} height={330} ariaLabel="Comparación de modelos registrados" />
      </Panel>
      <Panel eyebrow="Historial de despliegue" title="Auditoría de modelos">
        <div className="audit-list">
          {data.audit.map((event) => (
            <div key={event.id}><StatusDot status={event.result} /><span>{event.time}</span><strong>{event.action}</strong><span>{event.resource}</span><small>{event.actor}</small></div>
          ))}
        </div>
      </Panel>
    </>
  );
}
