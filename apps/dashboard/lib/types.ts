export type Technology = "solar" | "wind" | "battery";
export type Severity = "critical" | "high" | "medium" | "low";

export interface SnapshotMeta {
  snapshot_version: string;
  generated_at: string;
  data_through: string;
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
  validation_mae_mw: number;
  nrmse: number;
  pinball_p10: number;
  pinball_p50: number;
  pinball_p90: number;
  interval_width_mw: number;
  quantile_crossing_rate: number;
  validation_folds: number;
  validation_gap_hours: number;
}

export interface Champion extends ModelMetric {
  version: string;
  alias: string;
  stage: string;
  approved_by: string;
  approval_status?: "approved" | "pending" | "not_requested";
  approval_reviewed_at?: string | null;
  approval_evidence_hash?: string | null;
  artifact_sha256?: string | null;
  artifact_size_bytes?: number | null;
  estimator_class?: string | null;
  fitted_tree_count?: number | null;
  smoke_inference?: {
    status: string;
    point_prediction_mw: number;
    served_quantiles_mw: {
      p10: number;
      p50: number;
      p90: number;
    };
  } | null;
  selection_rank?: number;
  validation_delta_percent?: number;
  drift_status: string;
  drift_max_psi?: number | null;
  feature_drift?: Record<string, number>;
  target_psi?: number | null;
  prediction_psi?: number | null;
  trained_at: string;
}

export interface MlEvidence {
  schema_version: string;
  generated_at: string;
  status: string;
  run: {
    training_run_id?: string | null;
    training_code_commit?: string | null;
    verification_code_commit?: string | null;
    registry_generated_at?: string | null;
  };
  learning: {
    mode: string;
    online_learning: boolean;
    automatic_retraining: boolean;
    selection_metric: string;
    test_used_for_selection: boolean;
    validation_folds: number;
    validation_gap_hours: number;
    blocked_test_days: number;
    candidate_count: number;
    algorithm_count: number;
    algorithms: string[];
    reproduce_command: string;
    verify_command: string;
  };
  dataset: {
    manifest: string;
    dataset_id?: string | null;
    version?: string | null;
    row_count?: number | null;
    min_timestamp?: string | null;
    max_timestamp?: string | null;
    content_hash?: string | null;
    schema_hash?: string | null;
    quality_status?: string | null;
    contains_synthetic_data?: boolean | null;
  };
  runtime: {
    python: string;
    scikit_learn: string;
    pandas: string;
    numpy: string;
  };
  tracking: {
    status: string;
    backend: string;
    experiment: string;
    runs: number;
    note: string;
  };
  artifacts: {
    technology: "solar" | "wind";
    model: string;
    alias: string;
    file: string;
    sha256: string;
    size_bytes: number;
    estimator_class: string;
    hyperparameters: Record<string, string | number | boolean | null>;
    fitted_tree_count?: number | null;
    feature_count: number;
    features: string[];
    trained_until: string;
    seed: number;
    validation: {
      method: string;
      folds: number;
      gap_hours: number;
      selection_metric: string;
      selection_score: number;
      test_is_untouched_for_selection: boolean;
    };
    smoke_inference: {
      status: string;
      input_row_sha256: string;
      point_prediction_mw: number;
      raw_quantiles_mw: Record<"p10" | "p50" | "p90", number>;
      served_quantiles_mw: Record<"p10" | "p50" | "p90", number>;
    };
    approval: {
      status: string;
      approver?: string | null;
      reviewed_at?: string | null;
      evidence_hash?: string | null;
      scope: string;
    };
  }[];
  checks: {
    id: string;
    passed: boolean;
  }[];
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
  extracted_at: string | null;
  source_updated_at: string | null;
  checksum: string | null;
  records: number;
  evidence: string | null;
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
  latency_ms: number | null;
  uptime: number | null;
  evidence_at: string | null;
  evidence_scope: string;
}

export interface Workflow {
  name: string;
  status: string;
  duration_s: number | null;
  last_run: string;
  runs_7d: number;
  evidence: string;
}

export interface Risk {
  id: string;
  category: string;
  title: string;
  severity: string;
  residual: string;
  owner: string;
  control: string;
  status: string;
  likelihood: number;
  impact: number;
  evidence: string;
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
  forecast_horizon_metrics: Record<
    "solar" | "wind",
    {
      label: string;
      start_hour: number;
      end_hour: number;
      mae_mw: number;
      observations: number;
    }[]
  >;
  model_metrics: ModelMetric[];
  champions: Champion[];
  challengers: Champion[];
  ml_evidence: MlEvidence;
  drift: {
    generated_at?: string;
    method?: string;
    scope?: string;
    technologies?: Record<string, {
      status: string;
      max_psi: number;
      feature_psi: Record<string, number>;
      target_psi: number;
      prediction_psi: number;
    }>;
  };
  cv_metrics: {
    dataset?: string;
    data_origin?: string;
    license?: string;
    champion?: string;
    model?: string;
    images?: number;
    balanced_accuracy?: number;
    macro_f1?: number;
    pr_auc?: number;
    roc_auc?: number;
    brier_score?: number;
    expected_calibration_error?: number;
    confusion_matrix?: number[][];
    class_order?: string[];
    candidate_validation?: Record<string, { macro_f1?: number }>;
    test_used_for_selection?: boolean;
  };
  market: MarketPoint[];
  market_capture_rates: {
    solar: number;
    wind: number;
    portfolio: number;
  };
  inspections: Inspection[];
  sources: Source[];
  quality: QualityRow[];
  quality_summary: {
    checks_executed: number;
    checks_passed: number;
    checks_watch_or_failed: number;
    quarantined_rows: number;
    quarantined_rate: number;
    schema_changes_detected: number;
    overall_validity: number;
  };
  services: Service[];
  workflows: Workflow[];
  risks: Risk[];
  governance: {
    documents: {
      name: string;
      description: string;
      status: string;
      count: number;
      evidence: string[];
    }[];
    frameworks: {
      name: string;
      status: string;
      evidence: string | null;
    }[];
    disclaimer: string;
  };
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
