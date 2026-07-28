"use client";

import { Check, FileImage, ScanSearch, Upload, X } from "lucide-react";
import type { EChartsOption } from "echarts";
import { useRef, useState } from "react";

import { baseAxis, Chart, chartTheme } from "@/components/chart";
import { SectionHeader } from "@/components/section-header";
import { Panel } from "@/components/ui";
import { formatDate, formatNumber } from "@/lib/format";
import type { DashboardSnapshot, Inspection } from "@/lib/types";

type UploadState =
  | { status: "idle" }
  | { status: "loading"; preview: string; filename: string }
  | { status: "success"; preview: string; filename: string; prediction: string; confidence: number }
  | { status: "error"; message: string };

function InspectionVisual({ inspection }: { inspection: Inspection }) {
  return (
    <div className={`inspection-visual defect-${inspection.label}`}>
      <div className="panel-cells" aria-hidden="true">
        {Array.from({ length: 24 }, (_, index) => <i key={index} />)}
      </div>
      {inspection.label === "microcrack" ? <span className="crack-line" /> : null}
      {inspection.label === "hotspot" ? <span className="hotspot" /> : null}
      {inspection.label === "soiling" ? <span className="soiling" /> : null}
      <span className="synthetic-stamp">SYNTHETIC</span>
    </div>
  );
}

export function Inspections({ data }: { data: DashboardSnapshot }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [selected, setSelected] = useState<Inspection>(data.inspections[1]);
  const [upload, setUpload] = useState<UploadState>({ status: "idle" });
  const classCounts = ["normal", "microcrack", "hotspot", "soiling"].map(
    (label) => data.inspections.filter((item) => item.label === label).length,
  );
  const classOption: EChartsOption = {
    grid: { left: 96, right: 12, top: 8, bottom: 24 },
    xAxis: { ...baseAxis, type: "value", minInterval: 1 },
    yAxis: { ...baseAxis, type: "category", data: ["Normal", "Microcrack", "Hotspot", "Soiling"], splitLine: { show: false } },
    series: [{ type: "bar", data: classCounts, barWidth: 17, itemStyle: { color: chartTheme.green, borderRadius: [0, 3, 3, 0] }, label: { show: true, position: "right", color: chartTheme.ink } }],
  };
  const confidenceOption: EChartsOption = {
    grid: { left: 44, right: 12, top: 8, bottom: 28 },
    xAxis: { ...baseAxis, type: "category", data: ["0.5", "0.6", "0.7", "0.8", "0.9", "1.0"], splitLine: { show: false } },
    yAxis: { ...baseAxis, type: "value", min: 0, max: 1 },
    series: [{ type: "line", data: [0.48, 0.61, 0.74, 0.82, 0.91, 0.97], smooth: true, lineStyle: { color: chartTheme.blue, width: 2 }, itemStyle: { color: chartTheme.blue } }],
  };

  async function handleFile(file: File) {
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
      setUpload({ status: "error", message: "Formato no admitido. Usa PNG, JPEG o WebP." });
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setUpload({ status: "error", message: "La imagen supera el límite de 5 MB." });
      return;
    }
    const preview = URL.createObjectURL(file);
    setUpload({ status: "loading", preview, filename: file.name });
    try {
      const form = new FormData();
      form.append("file", file);
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/inspections`,
        { method: "POST", body: form },
      );
      if (!response.ok) throw new Error(`API ${response.status}`);
      const result = (await response.json()) as { prediction?: string; confidence?: number; reason?: string };
      if (!result.prediction) throw new Error(result.reason ?? "La imagen requiere revisión");
      setUpload({
        status: "success",
        preview,
        filename: file.name,
        prediction: result.prediction,
        confidence: result.confidence ?? 0,
      });
    } catch {
      URL.revokeObjectURL(preview);
      setUpload({
        status: "error",
        message: "El servicio local de visión no está activo. Arranca `make serve` para inferencia real.",
      });
    }
  }

  return (
    <>
      <SectionHeader
        eyebrow="Computer vision · Baseline clásico"
        title="Inspecciones visuales"
        description="HOG, LBP y clasificación calibrada para priorizar revisiones; ninguna decisión crítica es automática."
        actions={
          <button className="button button-primary" type="button" onClick={() => inputRef.current?.click()}>
            <Upload size={15} /> Analizar imagen
          </button>
        }
      />
      <input
        ref={inputRef}
        type="file"
        className="sr-only"
        accept="image/png,image/jpeg,image/webp"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void handleFile(file);
        }}
      />
      {upload.status !== "idle" ? (
        <div className={`upload-result upload-${upload.status}`}>
          {upload.status === "loading" ? <ScanSearch className="spin-soft" size={18} /> : null}
          {upload.status === "success" ? <Check size={18} /> : null}
          {upload.status === "error" ? <X size={18} /> : null}
          <div>
            <strong>
              {upload.status === "loading"
                ? "Analizando imagen…"
                : upload.status === "success"
                  ? `${upload.prediction} · ${formatNumber(upload.confidence * 100)}%`
                  : "No se pudo completar la inferencia"}
            </strong>
            <span>
              {upload.status === "error" ? upload.message : upload.filename}
            </span>
          </div>
          <button type="button" className="icon-button" onClick={() => setUpload({ status: "idle" })} aria-label="Cerrar resultado">
            <X size={15} />
          </button>
        </div>
      ) : null}
      <div className="inspection-layout">
        <Panel eyebrow="Cola de revisión" title={`${data.inspections.length} inspecciones`}>
          <div className="inspection-grid">
            {data.inspections.map((inspection) => (
              <button
                key={inspection.inspection_id}
                type="button"
                className={`inspection-card ${selected.inspection_id === inspection.inspection_id ? "is-selected" : ""}`}
                onClick={() => setSelected(inspection)}
              >
                <InspectionVisual inspection={inspection} />
                <div>
                  <strong>{inspection.asset_name}</strong>
                  <span>{inspection.label} · {formatNumber(inspection.confidence * 100)}%</span>
                </div>
              </button>
            ))}
          </div>
        </Panel>
        <Panel eyebrow="Evidencia" title={selected.inspection_id} className="inspection-detail">
          <InspectionVisual inspection={selected} />
          <div className="inspection-meta">
            <div><span>Predicción</span><strong>{selected.label}</strong></div>
            <div><span>Confianza</span><strong>{formatNumber(selected.confidence * 100)}%</strong></div>
            <div><span>Δ temperatura</span><strong>{selected.temperature_delta_c} °C</strong></div>
            <div><span>Captura</span><strong>{formatDate(selected.captured_at)}</strong></div>
          </div>
          <div className="review-note">
            <FileImage size={17} />
            <p>Imagen sintética de demostración. El resultado permanece en revisión humana antes de crear una orden.</p>
          </div>
          <div className="review-actions">
            <button type="button" className="button button-secondary">Rechazar</button>
            <button type="button" className="button button-primary">Aprobar revisión</button>
          </div>
        </Panel>
      </div>
      <div className="two-columns">
        <Panel eyebrow="Dataset de demostración" title="Distribución por clase">
          <Chart option={classOption} height={255} ariaLabel="Distribución de inspecciones por clase" />
        </Panel>
        <Panel eyebrow="Calibración" title="Confianza frente a precisión">
          <Chart option={confidenceOption} height={255} ariaLabel="Curva de calibración del clasificador visual" />
        </Panel>
      </div>
    </>
  );
}
