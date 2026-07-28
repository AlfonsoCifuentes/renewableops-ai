-- Metric view syntax requires the workspace feature to be enabled.
CREATE OR REPLACE VIEW renewableops.dev.v_semantic_metrics AS
SELECT
  date_hour,
  technology,
  energy_mwh,
  mwh_at_risk,
  ABS(actual_mw - expected_mw) AS absolute_error_mw,
  availability
FROM renewableops.dev.gold_portfolio_hourly;
