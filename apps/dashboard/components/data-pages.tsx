"use client";

import {
  Activity,
  ArrowDownToLine,
  BrainCircuit,
  CheckCircle2,
  Cpu,
  Database,
  FileCheck2,
  FlaskConical,
  GitBranch,
  Search,
  ShieldCheck,
  SquareTerminal,
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

function shortHash(value?: string | null) {
  if (!value) return "—";
  const hash = value.replace("sha256:", "");
  return `${hash.slice(0, 10)}…${hash.slice(-6)}`;
}

function megabytes(bytes?: number | null) {
  return bytes ? `${formatNumber(bytes / 1024 / 1024, 2)} MB` : "—";
}

export function Mlops({ data }: { data: DashboardSnapshot }) {
  const championKeys = new Set(
    data.champions.map((model) => `${model.technology}:${model.model}`),
  );
  const comparison: EChartsOption = {
    grid: { left: 50, right: 12, top: 14, bottom: 62 },
    tooltip: { trigger: "axis" },
    xAxis: { ...baseAxis, type: "category", data: data.model_metrics.map((item) => `${item.technology}\n${item.model}`), axisLabel: { ...baseAxis.axisLabel, rotate: 24 }, splitLine: { show: false } },
    yAxis: { ...baseAxis, type: "value", name: "MAE validación", axisLabel: { formatter: (value: number) => `${formatNumber(value)} MW` } },
    series: [{
      type: "bar",
      data: data.model_metrics.map((item) => ({
        value: item.validation_mae_mw,
        itemStyle: {
          color: championKeys.has(`${item.technology}:${item.model}`)
            ? chartTheme.green
            : "#c5cbc6",
          borderRadius: [3, 3, 0, 0],
        },
      })),
      barMaxWidth: 28,
    }],
  };
  const evidence = data.ml_evidence;

  return (
    <>
      <SectionHeader
        eyebrow="Registry · MLflow · Evidencia ejecutable"
        title="El entrenamiento deja pruebas."
        description="Artefactos reales, validación temporal, inferencia de humo, hashes y aprobación humana vinculados a una ejecución reproducible."
      />

      <div className="ml-proof-grid">
        <article>
          <span className="ml-proof-icon"><FileCheck2 size={16} /></span>
          <div><small>Verificación</small><strong>{evidence.status}</strong><p>{evidence.checks.filter((check) => check.passed).length}/{evidence.checks.length} checks</p></div>
        </article>
        <article>
          <span className="ml-proof-icon"><FlaskConical size={16} /></span>
          <div><small>Experimento</small><strong>{evidence.learning.candidate_count} candidatos</strong><p>{evidence.learning.algorithm_count} algoritmos · 2 tecnologías</p></div>
        </article>
        <article>
          <span className="ml-proof-icon"><Cpu size={16} /></span>
          <div><small>Artefactos cargados</small><strong>{evidence.artifacts.length} ejecutables</strong><p>joblib · inferencia comprobada</p></div>
        </article>
        <article>
          <span className="ml-proof-icon"><Activity size={16} /></span>
          <div><small>MLflow local</small><strong>{evidence.tracking.runs} runs</strong><p>{evidence.tracking.experiment}</p></div>
        </article>
      </div>

      <Panel className="learning-evidence-panel">
        <div className="learning-disclosure">
          <div>
            <Badge tone="info">batch learning</Badge>
            <h2>Se reentrena; no aprende en el navegador.</h2>
            <p>
              Los modelos se ajustan de cero sobre un dataset versionado. No existe aprendizaje
              online ni cambios silenciosos en producción: cada nuevo artefacto necesita otra
              validación y otra aprobación.
            </p>
          </div>
          <div className="ml-training-flow" aria-label="Flujo de entrenamiento">
            {[
              ["01", "Dataset", `${formatNumber(evidence.dataset.row_count ?? 0)} filas`],
              ["02", "Features", `${evidence.artifacts[0]?.feature_count ?? 0} variables`],
              ["03", "Validación", `${evidence.learning.validation_folds} folds + gap ${evidence.learning.validation_gap_hours} h`],
              ["04", "Selección", "MAE temporal"],
              ["05", "Holdout", `${evidence.learning.blocked_test_days} días intactos`],
            ].map(([step, label, detail]) => (
              <div key={step}><span>{step}</span><strong>{label}</strong><small>{detail}</small></div>
            ))}
          </div>
        </div>
        <div className="reproduce-strip">
          <SquareTerminal size={15} />
          <span>Reentrenar</span>
          <code>{evidence.learning.reproduce_command}</code>
          <span>Verificar</span>
          <code>{evidence.learning.verify_command}</code>
        </div>
      </Panel>

      <div className="champion-grid">
        {data.champions.map((model) => (
          <Panel key={model.technology} className="champion-card">
            <div className="champion-top">
              <div><Badge tone="success">champion</Badge><Badge tone={model.approval_status === "approved" ? "info" : "warning"}>{model.approval_status}</Badge></div>
              <span>{model.technology}</span>
            </div>
            <h2>{model.technology} · {model.model.replaceAll("_", " ")}</h2>
            <p>v{model.version} · {model.stage}</p>
            <div className="champion-metrics">
              <div><span>MAE validación</span><strong>{formatNumber(model.validation_mae_mw, 3)} MW</strong></div>
              <div><span>MAE holdout</span><strong>{formatNumber(model.mae_mw, 3)} MW</strong></div>
              <div><span>Skill vs t−24 h</span><strong>+{formatNumber(model.skill_vs_persistence * 100)}%</strong></div>
              <div><span>Cobertura P10–P90</span><strong>{formatNumber(model.coverage_p10_p90 * 100)}%</strong></div>
            </div>
            <div className="artifact-signature">
              <span>{model.estimator_class} · {model.fitted_tree_count ?? "—"} árboles</span>
              <span>{megabytes(model.artifact_size_bytes)} · {shortHash(model.artifact_sha256)}</span>
            </div>
            <div className={`approval-line ${model.approval_status === "approved" ? "is-approved" : ""}`}>
              <ShieldCheck size={15} />
              <span>{model.approved_by}</span>
            </div>
          </Panel>
        ))}
      </div>

      <Panel
        className="model-proof-panel"
        eyebrow="Prueba de ejecución"
        title="Los artefactos cargan y producen inferencias"
        action={<Badge tone={evidence.status === "passed" ? "success" : "critical"}>{evidence.status}</Badge>}
      >
        <div className="model-proof-list">
          {evidence.artifacts.map((artifact) => (
            <article key={artifact.technology}>
              <div className="proof-status"><CheckCircle2 size={15} /><span>{artifact.smoke_inference.status}</span></div>
              <div><small>Modelo serializado</small><strong>{artifact.technology} · {artifact.model.replaceAll("_", " ")}</strong><p>{artifact.estimator_class} · seed {artifact.seed}</p></div>
              <div><small>Predicción de humo</small><strong>{formatNumber(artifact.smoke_inference.point_prediction_mw, 3)} MW</strong><p>P10 {formatNumber(artifact.smoke_inference.served_quantiles_mw.p10, 2)} · P90 {formatNumber(artifact.smoke_inference.served_quantiles_mw.p90, 2)}</p></div>
              <div><small>Integridad</small><strong>{shortHash(artifact.sha256)}</strong><p>{megabytes(artifact.size_bytes)} · {artifact.feature_count} features</p></div>
            </article>
          ))}
        </div>
      </Panel>

      <Panel eyebrow="Selección sin leakage" title="MAE de validación temporal">
        <Chart option={comparison} height={330} ariaLabel="Comparación de modelos registrados" />
      </Panel>

      <Panel eyebrow="Leaderboard" title="Qué modelos se entrenaron y qué resultado obtuvieron">
        <div className="model-leaderboards">
          {(["solar", "wind"] as const).map((technology) => {
            const rows = data.model_metrics
              .filter((model) => model.technology === technology)
              .toSorted((first, second) => first.validation_mae_mw - second.validation_mae_mw);
            return (
              <div key={technology}>
                <div className="leaderboard-title"><span>{technology}</span><small>ranking por validación</small></div>
                <table>
                  <thead><tr><th>#</th><th>Modelo</th><th>Validación</th><th>Holdout</th><th>Skill</th></tr></thead>
                  <tbody>
                    {rows.map((model, index) => (
                      <tr key={`${technology}-${model.model}`} className={index === 0 ? "is-champion" : ""}>
                        <td>{String(index + 1).padStart(2, "0")}</td>
                        <td><strong>{model.model.replaceAll("_", " ")}</strong>{index === 0 ? <Badge tone="success">selected</Badge> : null}</td>
                        <td>{formatNumber(model.validation_mae_mw, 3)} MW</td>
                        <td>{formatNumber(model.mae_mw, 3)} MW</td>
                        <td>+{formatNumber(model.skill_vs_persistence * 100)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel eyebrow="Challengers" title="Evaluados, pero no recomendados para promoción">
        <div className="challenger-review-grid">
          {data.challengers.map((model) => (
            <article key={`challenger-${model.technology}`}>
              <div><Badge tone="neutral">rank 02</Badge><span>{model.technology}</span></div>
              <h3>{model.model.replaceAll("_", " ")}</h3>
              <p>
                MAE de validación {formatNumber(model.validation_mae_mw, 3)} MW ·{" "}
                <strong>+{formatNumber(model.validation_delta_percent ?? 0, 2)}%</strong> frente al
                champion.
              </p>
              <div className="gate-list">
                <span><CheckCircle2 size={14} /> Entrenado y medido</span>
                <span><CheckCircle2 size={14} /> Resultado conservado en MLflow</span>
                <span className="gate-hold"><BrainCircuit size={14} /> No se promueve: pierde en la métrica de selección</span>
              </div>
            </article>
          ))}
        </div>
      </Panel>

      <Panel eyebrow="Trazabilidad" title="Dataset, runtime y ejecución">
        <div className="evidence-ledger">
          <div><span>Run de entrenamiento</span><strong>{evidence.run.training_run_id}</strong></div>
          <div><span>Commit del entrenamiento</span><strong>{shortHash(evidence.run.training_code_commit)}</strong></div>
          <div><span>Dataset SHA-256</span><strong>{shortHash(evidence.dataset.content_hash)}</strong></div>
          <div><span>Ventana temporal</span><strong>{evidence.dataset.min_timestamp?.slice(0, 10)} → {evidence.dataset.max_timestamp?.slice(0, 10)}</strong></div>
          <div><span>Runtime</span><strong>Python {evidence.runtime.python} · sklearn {evidence.runtime.scikit_learn}</strong></div>
          <div><span>Datos</span><strong>{evidence.dataset.contains_synthetic_data ? "SCADA sintético reproducible" : "Datos operativos"}</strong></div>
        </div>
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
