-- Assets are USD thousands; thresholds therefore convert stated dollar bands to $000.
CREATE TABLE staging.peer_group_candidates AS
SELECT
    f.cert, f.rssdid, f.reporting_date, f.bank_class, f.asset,
    CASE
        WHEN f.asset IS NULL OR f.asset < 0 THEN 'UNKNOWN'
        WHEN f.asset < 100000 THEN 'LT_100M'
        WHEN f.asset < 500000 THEN '100M_500M'
        WHEN f.asset < 1000000 THEN '500M_1B'
        WHEN f.asset < 10000000 THEN '1B_10B'
        WHEN f.asset < 50000000 THEN '10B_50B'
        WHEN f.asset < 250000000 THEN '50B_250B'
        ELSE 'GE_250B'
    END AS asset_size_band,
    CONCAT(CAST(f.reporting_date AS VARCHAR), '|',
        CASE
            WHEN f.asset IS NULL OR f.asset < 0 THEN 'UNKNOWN'
            WHEN f.asset < 100000 THEN 'LT_100M'
            WHEN f.asset < 500000 THEN '100M_500M'
            WHEN f.asset < 1000000 THEN '500M_1B'
            WHEN f.asset < 10000000 THEN '1B_10B'
            WHEN f.asset < 50000000 THEN '10B_50B'
            WHEN f.asset < 250000000 THEN '50B_250B'
            ELSE 'GE_250B'
        END, '|', COALESCE(f.bank_class, 'UNKNOWN')) AS detailed_peer_group_id,
    CONCAT(CAST(f.reporting_date AS VARCHAR), '|',
        CASE
            WHEN f.asset IS NULL OR f.asset < 0 THEN 'UNKNOWN'
            WHEN f.asset < 100000 THEN 'LT_100M'
            WHEN f.asset < 500000 THEN '100M_500M'
            WHEN f.asset < 1000000 THEN '500M_1B'
            WHEN f.asset < 10000000 THEN '1B_10B'
            WHEN f.asset < 50000000 THEN '10B_50B'
            WHEN f.asset < 250000000 THEN '50B_250B'
            ELSE 'GE_250B'
        END) AS broad_peer_group_id
FROM staging.feature_source f;

CREATE TABLE core.bank_peer_groups AS
WITH counted AS (
    SELECT *, COUNT(*) OVER (PARTITION BY detailed_peer_group_id) AS detailed_peer_count,
              COUNT(*) OVER (PARTITION BY broad_peer_group_id) AS broad_peer_count
    FROM staging.peer_group_candidates
)
SELECT
    cert, rssdid, reporting_date, asset, bank_class, asset_size_band,
    detailed_peer_group_id, detailed_peer_count,
    broad_peer_group_id, broad_peer_count,
    CASE WHEN detailed_peer_count >= 20 AND asset_size_band <> 'UNKNOWN'
         THEN detailed_peer_group_id ELSE broad_peer_group_id END AS final_peer_group_id,
    CASE WHEN detailed_peer_count >= 20 AND asset_size_band <> 'UNKNOWN'
         THEN detailed_peer_count ELSE broad_peer_count END AS final_peer_group_size,
    CASE WHEN detailed_peer_count >= 20 AND asset_size_band <> 'UNKNOWN'
         THEN 'DETAILED' ELSE 'BROAD_ASSET_FALLBACK' END AS peer_group_method,
    detailed_peer_count < 20 AS detailed_group_too_small,
    '{{feature_build_run_id}}' AS feature_build_run_id,
    '{{peer_configuration_hash}}' AS peer_configuration_hash
FROM counted
ORDER BY cert, reporting_date;
