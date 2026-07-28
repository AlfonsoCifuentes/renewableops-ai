export type Technology = "solar" | "wind" | "battery";
export type Severity = "critical" | "high" | "medium" | "low";

export interface SnapshotMeta {
  snapshot_version: string;
  generated_at: string;
  display_timezone: string;
  pipeline_run_id: string;
  data_status: string;
  is_demo: boolean;
  contains_synthetic_data: boolean;
  source_note: string;
}

export interface DashboardKpis {
  forecast_24h_mwh: number;
  assets_online: number;
  assets_total: number;
  active_anomalies: number;
  mwh_at_risk: number;
  revenue_7d_eur: number;
  forecast_nmae: number;
  availability: number;
  data_freshness_minutes: number;
}

export interface TimePoint {
  timestamp: string;
  actual: number;
  forecast: number;
  p10: number;
  p90: number;
}

export interface Asset {
  asset_id: string;
  code: string;
  name: string;
  technology: Technology;
  technology_label: string;
  region: string;
  municipality: string;
  latitude: number;
  longitude: number;
  capacity_mw: number;
  commissioning_date: string;
  status: "online" | "attention" | "standby";
  manufacturer: string;
  model: string;
  portfolio: string;
  expected_availability: number;
  current_power_mw: number;
  availability: number;
  capacity_factor: number;
  forecast_24h_mwh: number;
  mwh_at_risk: number;
  revenue_7d_eur: number;
  last_inspection: string;
  sparkline: number[];
}

export interface Anomaly {
  incident_id: string;
  asset_id: string;
  asset_name: string;
  technology: Technology;
  started_at: string;
  last_seen_at: string;
  points: number;
  worst_residual_mw: number;
  capacity_mw: number;
  labelled_cause: string;
  mwh_at_risk: number;
  severity: Severity;
  status: string;
  confidence: number;
  recommended_action: string;
  estimated_impact_eur: number;
}

export interface ModelMetric {
  technology: "solar" | "wind";
  model: string;
  mae_mw: number;
  rmse_mw: number;
  nmae: number;
  bias_mw: number;
  skill_vs_persistence: number;
  coverage_p10_p90: number;
  dataset_rows: number;
  test_rows: number;
}

export interface Champion extends ModelMetric {
  version: string;
  alias: string;
  stage: string;
  approved_by: string;
  drift_status: string;
  trained_at: string;
}

export interface MarketPoint {
  timestamp: string;
  price: number;
  generation: number;
  demand: number;
}

export interface Inspection {
  inspection_id: string;
  asset_id: string;
  asset_name: string;
  label: string;
  confidence: number;
  review_status: string;
  captured_at: string;
  is_synthetic: boolean;
  temperature_delta_c: number;
}

export interface Source {
  id: string;
  name: string;
  authority: string;
  status: string;
  age: string;
  kind: "official" | "synthetic";
  license: string;
}

export interface QualityRow {
  dataset: string;
  freshness: number;
  completeness: number;
  validity: number;
  uniqueness: number;
  status: string;
}

export interface Service {
  name: string;
  status: string;
  latency_ms: number;
  uptime: number;
}

export interface Workflow {
  name: string;
  status: string;
  duration_s: number;
  last_run: string;
  runs_7d: number;
}

export interface Risk {
  id: string;
  category: string;
  title: string;
  severity: string;
  residual: string;
  owner: string;
  control: string;
}

export interface AuditEvent {
  id: string;
  time: string;
  actor: string;
  action: string;
  resource: string;
  result: string;
}

export interface Scenario {
  id: string;
  name: string;
  asset_type: Technology | "all";
  default_severity: number;
  detection: string;
  action: string;
}

export interface DashboardSnapshot {
  meta: SnapshotMeta;
  kpis: DashboardKpis;
  series: TimePoint[];
  mix: { technology: string; energy_mwh: number; share: number }[];
  assets: Asset[];
  anomalies: Anomaly[];
  future_forecasts: {
    timestamp_utc: string;
    asset_id: string;
    asset_name: string;
    technology: "solar" | "wind";
    horizon_hours: number;
    p10_mw: number;
    p50_mw: number;
    p90_mw: number;
    model_version: string;
    is_synthetic: boolean;
  }[];
  model_metrics: ModelMetric[];
  champions: Champion[];
  cv_metrics: Record<string, string | number>;
  market: MarketPoint[];
  inspections: Inspection[];
  sources: Source[];
  quality: QualityRow[];
  services: Service[];
  workflows: Workflow[];
  risks: Risk[];
  audit: AuditEvent[];
  lineage: { from: string; to: string; status: string }[];
  scenarios: Scenario[];
  definitions: Record<string, string>;
}

export type SectionId =
  | "overview"
  | "fleet"
  | "forecast-solar"
  | "forecast-wind"
  | "market"
  | "asset-health"
  | "inspections"
  | "data-explorer"
  | "data-quality"
  | "mlops"
  | "observability"
  | "governance"
  | "scenario-lab";

export interface GlobalFilters {
  period: "24h" | "7d" | "30d";
  technology: "all" | Technology;
  region: string;
}
