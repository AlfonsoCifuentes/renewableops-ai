CREATE OR REPLACE VIEW renewableops.dev.v_operations_overview AS
SELECT
  date_hour,
  technology,
  energy_mwh,
  actual_mw,
  expected_mw,
  availability,
  price_eur_mwh,
  mwh_at_risk,
  asset_count
FROM renewableops.dev.gold_portfolio_hourly;

CREATE OR REPLACE VIEW renewableops.dev.v_data_quality AS
SELECT
  origin.update_id,
  origin.timestamp AS event_timestamp,
  details:flow_progress.status AS status,
  details:flow_progress.metrics AS metrics
FROM event_log(TABLE(renewableops.dev.event_log_renewableops))
WHERE event_type = 'flow_progress';
