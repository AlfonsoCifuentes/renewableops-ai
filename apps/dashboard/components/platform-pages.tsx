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
import { useMemo, useState, useTransition } from "react";

import { baseAxis, Chart, chartTheme } from "@/components/chart";
import { SectionHeader } from "@/components/section-header";
import { Badge, Panel, StatusDot } from "@/components/ui";
import { formatNumber } from "@/lib/format";
import type { DashboardSnapshot, Scenario } from "@/lib/types";

export function Observability({ data }: { data: DashboardSnapshot }) {
  const latencyOption: EChartsOption = {
    grid: { left: 48, right: 12, top: 12, bottom: 28 },
    tooltip: { trigger: "axis" },
    xAxis: { ...baseAxis, type: "category", data: ["00", "03", "06", "09", "12", "15", "18", "21"], splitLine: { show: false } },
    yAxis: { ...baseAxis, type: "value", name: "ms" },
    series: [
      { name: "P95", type: "line", data: [172, 165, 201, 186, 194, 181, 176, 169], smooth: true, lineStyle: { color: chartTheme.green, width: 2.2 }, itemStyle: { color: chartTheme.green } },
      { name: "P50", type: "line", data: [62, 58, 71, 65, 69, 63, 61, 59], smooth: true, lineStyle: { color: chartTheme.blue, width: 1.6, type: "dashed" }, itemStyle: { color: chartTheme.blue } },
    ],
  };
  const pipelineOption: EChartsOption = {
    grid: { left: 152, right: 16, top: 10, bottom: 28 },
    xAxis: { ...baseAxis, type: "value", name: "s" },
    yAxis: { ...baseAxis, type: "category", data: data.workflows.map((workflow) => workflow.name), splitLine: { show: false } },
    series: [{ type: "bar", data: data.workflows.map((workflow) => workflow.duration_s), barWidth: 18, itemStyle: { color: chartTheme.greenSoft, borderRadius: [0, 3, 3, 0] } }],
  };
  return (
    <>
      <SectionHeader eyebrow="SRE · Trazabilidad" title="Observabilidad de extremo a extremo." description="Servicios, pipelines y correlación entre petición, dato, modelo y snapshot." />
      <div className="service-grid">
        {data.services.map((service) => (
          <article key={service.name}>
            <StatusDot status={service.status} />
            <strong>{service.name}</strong>
            <span>{service.latency_ms ? `${service.latency_ms} ms` : "sin ejecución"}</span>
            <small>{formatNumber(service.uptime)}% disponibilidad demo</small>
          </article>
        ))}
      </div>
      <div className="two-columns">
        <Panel eyebrow="FastAPI" title="Latencia de respuesta">
          <Chart option={latencyOption} height={285} ariaLabel="Latencia P50 y P95 de la API" />
        </Panel>
        <Panel eyebrow="Orquestación" title="Duración de workflows">
          <Chart option={pipelineOption} height={285} ariaLabel="Duración de workflows de operaciones" />
        </Panel>
      </div>
      <Panel eyebrow="n8n" title="Ejecuciones operativas">
        <div className="workflow-list">
          {data.workflows.map((workflow) => (
            <article key={workflow.name}>
              <StatusDot status={workflow.status} />
              <div><strong>{workflow.name}</strong><span>{workflow.runs_7d} ejecuciones · última {workflow.last_run}</span></div>
              <span>{workflow.duration_s}s</span>
              <button type="button" className="icon-button" aria-label={`Ver ${workflow.name}`}><Braces size={15} /></button>
            </article>
          ))}
        </div>
      </Panel>
      <Panel eyebrow="Logs estructurados" title="Traza correlacionada">
        <pre className="log-view" tabIndex={0}>
          <code>
{`06:27:02.118  INFO  forecast.completed   correlation_id=corr-7af2  model=wind@1.0.0
06:27:02.301  INFO  snapshot.write       correlation_id=corr-7af2  rows=480
06:27:03.012  INFO  quality.passed       correlation_id=corr-7af2  checks=84
06:29:14.882  INFO  snapshot.signed      correlation_id=corr-7af2  sha256=8d1c…c03a`}
          </code>
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
      data: [[2, 2, 2, "R-01"], [3, 3, 3, "R-02"], [1, 4, 4, "R-03"], [0, 4, 5, "R-04"]],
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
            {[
              ["System card", "v1.0 · approved"],
              ["Model cards", "solar + wind + CV"],
              ["Data cards", "4 datasets"],
              ["Threat model", "STRIDE + ML threats"],
              ["Incident playbooks", "12 procedimientos"],
              ["SBOM", "CycloneDX · current"],
            ].map(([title, meta]) => (
              <button type="button" key={title}>
                <FileCheck2 size={16} />
                <span><strong>{title}</strong><small>{meta}</small></span>
                <Check size={15} />
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
        {[
          ["AI Act", "Intended use, human oversight, logging", "12/12"],
          ["NIS2", "Risk, incident, continuity, supply chain", "18/20"],
          ["NIST AI RMF", "Govern, Map, Measure, Manage", "16/16"],
          ["OWASP ML", "Input, poisoning, supply chain, integrity", "9/10"],
        ].map(([name, description, score]) => (
          <article key={name}><span>{name}</span><strong>{score}</strong><p>{description}</p><div><i style={{ width: score === "18/20" || score === "9/10" ? "90%" : "100%" }} /></div></article>
        ))}
      </div>
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
  const [isPending, startTransition] = useTransition();

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
  }

  function execute() {
    const asset = data.assets.find((item) => item.asset_id === assetId) ?? eligibleAssets[0];
    startTransition(() => {
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
      });
    });
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
          <button type="button" className="button button-primary scenario-run" onClick={execute} disabled={isPending}>
            <CirclePlay size={16} /> {isPending ? "Ejecutando…" : "Ejecutar en sandbox"}
          </button>
        </Panel>
      </div>
      <Panel className={`scenario-output ${result ? "has-result" : ""}`}>
        {result ? (
          <>
            <div className="scenario-result-head">
              <div className="success-seal"><Check size={20} /></div>
              <div><p className="eyebrow">03 · Resultado</p><h2>Escenario detectado y revertido</h2><span>{result.runId} · auditado</span></div>
              <Badge tone="success">sandbox limpio</Badge>
            </div>
            <div className="scenario-timeline">
              <div><i /><span>00:00</span><strong>Inyección</strong><small>{result.scenario.name} · {result.assetName}</small></div>
              <div><i /><span>+{result.detectionSeconds}s</span><strong>Detección</strong><small>{result.scenario.detection}</small></div>
              <div><i /><span>+2 min</span><strong>Acción</strong><small>{result.scenario.action}</small></div>
              <div><i /><span>+4 min</span><strong>Rollback</strong><small>Snapshot base restaurado</small></div>
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
