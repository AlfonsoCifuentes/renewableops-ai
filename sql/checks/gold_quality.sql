-- Gold tables must be internally consistent before a snapshot can be published.
SELECT
    asset_id,
    timestamp_utc,
    COUNT(*) AS duplicate_count
FROM renewableops.gold_forecasts
GROUP BY asset_id, timestamp_utc
HAVING COUNT(*) > 1;

SELECT *
FROM renewableops.gold_forecasts
WHERE p10_mw > p50_mw OR p50_mw > p90_mw OR p10_mw < 0;
