"use client";

import {
  Activity,
  Braces,
  Check,
  CirclePlay,
  Clock3,
  FileCheck2,
  RotateCcw,
  ServerCog,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { EChartsOption } from "echarts";
import { useMemo, useState } from "react";

import { baseAxis, Chart, chartTheme } from "@/components/chart";
import { SectionHeader } from "@/components/section-header";
import { Badge, Panel, StatusDot } from "@/components/ui";
import { formatDate } from "@/lib/format";
import type { DashboardSnapshot, Scenario } from "@/lib/types";

export function Observability({ data }: { data: DashboardSnapshot }) {
  const probedServices = data.services.filter(
    (service): service is typeof service & { latency_ms: number } =>
      service.latency_ms !== null,
  );
  const latencyOption: EChartsOption = {
    grid: { left: 142, right: 20, top: 12, bottom: 28 },
    tooltip: { trigger: "axis" },
    xAxis: { ...baseAxis, type: "value", name: "ms" },
    yAxis: {
      ...baseAxis,
      type: "category",
      data: probedServices.map((service) => service.name),
      splitLine: { show: false },
    },
    series: [{
      name: "Probe HTTP",
      type: "bar",
      data: probedServices.map((service) => service.latency_ms),
      barWidth: 18,
      itemStyle: { color: chartTheme.green, borderRadius: [0, 3, 3, 0] },
      label: { show: true, position: "right", color: chartTheme.ink, formatter: "{c} ms" },
    }],
  };
  const executed = data.workflows.filter((workflow) => workflow.status === "executed_success").length;
  const pipelineOption: EChartsOption = {
    grid: { left: 98, right: 16, top: 10, bottom: 28 },
    xAxis: { ...baseAxis, type: "value", minInterval: 1, name: "workflows" },
    yAxis: { ...baseAxis, type: "category", data: ["Ejecutado", "Configurado"], splitLine: { show: false } },
    series: [{
      type: "bar",
      data: [executed, data.workflows.length - executed],
      barWidth: 22,
      itemStyle: { color: chartTheme.greenSoft, borderRadius: [0, 3, 3, 0] },
      label: { show: true, position: "right", color: chartTheme.ink },
    }],
  };
  return (
    <>
      <SectionHeader eyebrow="SRE · Trazabilidad" title="Observabilidad de extremo a extremo." description="Servicios, pipelines y correlación entre petición, dato, modelo y snapshot." />
      <div className="service-grid">
        {data.services.map((service) => (
          <article key={service.name}>
            <StatusDot status={service.status} />
            <strong>{service.name}</strong>
            <span>{service.latency_ms !== null ? `${service.latency_ms} ms` : "sin probe HTTP"}</span>
            <small>{service.evidence_at ? `verificado ${formatDate(service.evidence_at, true)}` : service.evidence_scope}</small>
          </article>
        ))}
      </div>
      <div className="two-columns">
        <Panel eyebrow="Runtime verificado" title="Latencia de probes HTTP">
          <Chart option={latencyOption} height={285} ariaLabel="Latencia medida durante la verificación local" />
        </Panel>
        <Panel eyebrow="Orquestación" title="Cobertura de ejecución">
          <Chart option={pipelineOption} height={285} ariaLabel="Workflows configurados y ejecutados con evidencia" />
        </Panel>
      </div>
      <Panel eyebrow="n8n" title="Ejecuciones operativas">
        <div className="workflow-list">
          {data.workflows.map((workflow) => (
            <article key={workflow.name}>
              <StatusDot status={workflow.status} />
              <div><strong>{workflow.name}</strong><span>{workflow.runs_7d ? `${workflow.runs_7d} ejecución con evidencia` : "configurado · no ejecutado"} · {workflow.last_run}</span></div>
              <span>{workflow.duration_s !== null ? `${workflow.duration_s}s` : "—"}</span>
              <button type="button" className="icon-button" aria-label={`Ver ${workflow.name}`}><Braces size={15} /></button>
            </article>
          ))}
        </div>
      </Panel>
      <Panel eyebrow="Logs estructurados" title="Traza correlacionada">
        <pre className="log-view" tabIndex={0}>
          <code>{data.audit.length
            ? data.audit.map((event) => `${event.time}  ${event.result.toUpperCase().padEnd(8)} ${event.action.padEnd(22)} actor=${event.actor} resource=${event.resource}`).join("\n")
            : "Sin eventos persistidos. Ejecuta el pipeline para crear la cadena de auditoría."}</code>
        </pre>
      </Panel>
    </>
  );
}

export function Governance({ data }: { data: DashboardSnapshot }) {
  const riskMatrix: EChartsOption = {
    grid: { left: 76, right: 24, top: 18, bottom: 42 },
    xAxis: { ...baseAxis, type: "category", data: ["Rara", "Improbable", "Posible", "Probable", "Casi segura"], name: "Probabilidad", splitLine: { show: true } },
    yAxis: { ...baseAxis, type: "category", data: ["Menor", "Moderado", "Serio", "Alto", "Crítico"], name: "Impacto" },
    visualMap: { show: false, min: 1, max: 5, inRange: { color: [chartTheme.greenSoft, chartTheme.sand, chartTheme.rust] } },
    series: [{
      type: "scatter",
      symbolSize: (value: number[]) => 14 + value[2] * 3,
      data: data.risks.map((risk) => [
        risk.likelihood - 1,
        risk.impact - 1,
        risk.impact,
        risk.id,
      ]),
      label: { show: true, formatter: (params: { data: unknown }) => String((params.data as [number, number, number, string])[3]), color: "#fff", fontWeight: 700 },
      itemStyle: { borderColor: "#fff", borderWidth: 2 },
    }],
  };
  return (
    <>
      <SectionHeader eyebrow="Gobierno · Seguridad" title="Controles, límites y evidencia." description="Alineación de ingeniería con AI Act, NIS2, GDPR, NIST AI RMF y OWASP; no constituye certificación." />
      <div className="governance-banner">
        <ShieldCheck size={22} />
        <div><strong>Sistema de apoyo a decisiones</strong><span>No controla infraestructura, no ejecuta trading y requiere supervisión humana.</span></div>
        <Badge tone="success">Boundary enforced</Badge>
      </div>
      <div className="governance-layout">
        <Panel eyebrow="Registro de riesgos" title="Riesgo inherente">
          <Chart option={riskMatrix} height={320} ariaLabel="Matriz de riesgos de probabilidad e impacto" />
        </Panel>
        <Panel eyebrow="Evidencias" title="Paquete de gobierno">
          <div className="document-list">
            {data.governance.documents.map((document) => (
              <button type="button" key={document.name}>
                <FileCheck2 size={16} />
                <span>
                  <strong>{document.name}</strong>
                  <small>{document.count} artefacto{document.count === 1 ? "" : "s"} · {document.description}</small>
                </span>
                {document.status === "versioned"
                  ? <Check size={15} />
                  : <Clock3 size={15} aria-label="Pendiente de generar" />}
              </button>
            ))}
          </div>
        </Panel>
      </div>
      <Panel eyebrow="Tratamiento" title="Riesgos y controles activos">
        <div className="risk-register">
          {data.risks.map((risk) => (
            <article key={risk.id}>
              <strong>{risk.id}</strong>
              <Badge tone={risk.severity === "critical" ? "critical" : risk.severity === "high" ? "warning" : "neutral"}>{risk.severity}</Badge>
              <div><strong>{risk.title}</strong><span>{risk.category} · owner {risk.owner}</span></div>
              <p>{risk.control}</p>
              <span>Residual <strong>{risk.residual}</strong></span>
            </article>
          ))}
        </div>
      </Panel>
      <div className="control-grid">
        {data.governance.frameworks.map((framework) => (
          <article key={framework.name}>
            <span>{framework.name}</span>
            <strong>{framework.status === "documented_alignment" ? "Mapeado" : "Sin evidencia"}</strong>
            <p>{framework.evidence ?? "No hay documento versionado."}</p>
            <div><i style={{ width: framework.status === "documented_alignment" ? "100%" : "0%" }} /></div>
          </article>
        ))}
      </div>
      <p className="governance-disclaimer">{data.governance.disclaimer}</p>
    </>
  );
}

interface ScenarioResult {
  runId: string;
  scenario: Scenario;
  assetName: string;
  severity: number;
  detectionSeconds: number;
  risk: number;
  action: string;
  source: "api" | "offline_preview";
  audited: boolean;
}

export function ScenarioLab({ data }: { data: DashboardSnapshot }) {
  const [scenarioId, setScenarioId] = useState(data.scenarios[0].id);
  const selectedScenario = data.scenarios.find((item) => item.id === scenarioId) ?? data.scenarios[0];
  const eligibleAssets = useMemo(
    () =>
      data.assets.filter(
        (asset) =>
          selectedScenario.asset_type === "all" ||
          asset.technology === selectedScenario.asset_type,
      ),
    [data.assets, selectedScenario.asset_type],
  );
  const [assetId, setAssetId] = useState(eligibleAssets[0]?.asset_id ?? data.assets[0].asset_id);
  const [severity, setSeverity] = useState(selectedScenario.default_severity);
  const [duration, setDuration] = useState(12);
  const [seed, setSeed] = useState(42);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [isPending, setIsPending] = useState(false);
  const [scenarioError, setScenarioError] = useState<string | null>(null);

  function selectScenario(id: string) {
    const scenario = data.scenarios.find((item) => item.id === id);
    if (!scenario) return;
    setScenarioId(id);
    setSeverity(scenario.default_severity);
    const eligible = data.assets.filter(
      (asset) => scenario.asset_type === "all" || asset.technology === scenario.asset_type,
    );
    setAssetId(eligible[0]?.asset_id ?? data.assets[0].asset_id);
    setResult(null);
    setScenarioError(null);
  }

  async function execute() {
    const asset = data.assets.find((item) => item.asset_id === assetId) ?? eligibleAssets[0];
    setIsPending(true);
    setScenarioError(null);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/scenarios`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            scenario: scenarioId,
            asset_id: assetId,
            severity,
            duration_hours: duration,
            seed,
          }),
        },
      );
      if (!response.ok) {
        throw new Error(`El sandbox rechazó la solicitud (HTTP ${response.status}).`);
      }
      const payload = (await response.json()) as {
        run_id: string;
        detection_seconds: number;
        estimated_mwh_at_risk: number;
        action: string;
        audit_event_id: string;
        reverted: boolean;
      };
      if (!payload.reverted) throw new Error("El sandbox no confirmó la reversión.");
      setResult({
        runId: payload.run_id,
        scenario: selectedScenario,
        assetName: asset.name,
        severity,
        detectionSeconds: payload.detection_seconds,
        risk: payload.estimated_mwh_at_risk,
        action: payload.action,
        source: "api",
        audited: Boolean(payload.audit_event_id),
      });
    } catch (error) {
      if (error instanceof TypeError) {
        // The public snapshot remains useful with the local API powered off.
        // This preview is labelled and never presented as an audited execution.
      const runHash = Math.abs(
        [...`${scenarioId}:${assetId}:${seed}`].reduce(
          (hash, character) => (hash * 31 + character.charCodeAt(0)) | 0,
          7,
        ),
      );
      setResult({
        runId: `SCN-${String(runHash).slice(0, 7)}`,
        scenario: selectedScenario,
        assetName: asset.name,
        severity,
        detectionSeconds: Math.max(8, 76 - Math.round(severity / 2)),
        risk: Number((asset.capacity_mw * duration * severity * 0.0018).toFixed(1)),
        action: selectedScenario.action,
        source: "offline_preview",
        audited: false,
      });
      } else {
        setScenarioError(error instanceof Error ? error.message : "No se pudo ejecutar.");
      }
    } finally {
      setIsPending(false);
    }
  }

  return (
    <>
      <SectionHeader eyebrow="Sandbox reproducible" title="Scenario Lab" description="Inyecta un fallo controlado, observa la detección y revierte el sandbox sin tocar datos operativos." />
      <div className="scenario-layout">
        <Panel eyebrow="01 · Configuración" title="Selecciona el escenario">
          <div className="scenario-options">
            {data.scenarios.map((scenario) => (
              <button type="button" key={scenario.id} className={scenario.id === scenarioId ? "is-active" : ""} onClick={() => selectScenario(scenario.id)}>
                <span>{scenario.name}</span><small>{scenario.detection}</small>
              </button>
            ))}
          </div>
        </Panel>
        <Panel eyebrow="02 · Parámetros" title="Define el experimento">
          <div className="scenario-form">
            <label><span>Activo</span><select value={assetId} onChange={(event) => setAssetId(event.target.value)}>{eligibleAssets.map((asset) => <option value={asset.asset_id} key={asset.asset_id}>{asset.name}</option>)}</select></label>
            <label><span>Severidad <strong>{severity}%</strong></span><input type="range" min="10" max="100" value={severity} onChange={(event) => setSeverity(Number(event.target.value))} /></label>
            <label><span>Duración</span><select value={duration} onChange={(event) => setDuration(Number(event.target.value))}><option value={6}>6 horas</option><option value={12}>12 horas</option><option value={24}>24 horas</option><option value={48}>48 horas</option></select></label>
            <label><span>Seed reproducible</span><input type="number" min="1" value={seed} onChange={(event) => setSeed(Number(event.target.value))} /></label>
          </div>
          <button type="button" className="button button-primary scenario-run" onClick={() => void execute()} disabled={isPending}>
            <CirclePlay size={16} /> {isPending ? "Ejecutando…" : "Ejecutar en sandbox"}
          </button>
          {scenarioError ? <p role="alert" className="form-error">{scenarioError}</p> : null}
        </Panel>
      </div>
      <Panel className={`scenario-output ${result ? "has-result" : ""}`}>
        {result ? (
          <>
            <div className="scenario-result-head">
              <div className="success-seal"><Check size={20} /></div>
              <div>
                <p className="eyebrow">03 · Resultado</p>
                <h2>{result.source === "api" ? "Escenario detectado y revertido" : "Vista previa determinista"}</h2>
                <span>{result.runId} · {result.audited ? "ejecución API auditada" : "sin ejecución ni auditoría"}</span>
              </div>
              <Badge tone={result.source === "api" ? "success" : "warning"}>
                {result.source === "api" ? "sandbox limpio" : "modo offline"}
              </Badge>
            </div>
            <div className="scenario-timeline">
              <div><i /><span>00:00</span><strong>Inyección</strong><small>{result.scenario.name} · {result.assetName}</small></div>
              <div><i /><span>+{result.detectionSeconds}s</span><strong>Detección</strong><small>{result.scenario.detection}</small></div>
              <div><i /><span>+2 min</span><strong>Acción</strong><small>{result.action}</small></div>
              <div><i /><span>+4 min</span><strong>Rollback</strong><small>{result.source === "api" ? "Snapshot base restaurado" : "No aplicado en modo offline"}</small></div>
            </div>
            <div className="scenario-impact">
              <div><Activity size={16} /><span>Severidad</span><strong>{result.severity}%</strong></div>
              <div><Clock3 size={16} /><span>Tiempo de detección</span><strong>{result.detectionSeconds}s</strong></div>
              <div><ServerCog size={16} /><span>MWh en riesgo</span><strong>{result.risk}</strong></div>
              <div><Sparkles size={16} /><span>Reproducibilidad</span><strong>seed {seed}</strong></div>
            </div>
            <button type="button" className="button button-secondary" onClick={() => setResult(null)}><RotateCcw size={15} /> Restablecer laboratorio</button>
          </>
        ) : (
          <div className="scenario-placeholder">
            <Sparkles size={24} />
            <strong>El resultado aparecerá aquí</strong>
            <p>La ejecución es determinista, aislada y genera un evento de auditoría.</p>
          </div>
        )}
      </Panel>
    </>
  );
}
