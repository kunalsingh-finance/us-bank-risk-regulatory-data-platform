-- Future research outcomes require two categories or independently severe capital evidence.
CREATE TABLE core.distress_events AS
WITH evidence AS (
    SELECT cert, rssdid, reporting_date AS distress_date,
           CASE WHEN equity_to_assets <= {{capital_evidence_level_threshold}}
                     OR equity_to_assets_change_yoy_pp <= {{capital_evidence_change_threshold}} THEN 1 ELSE 0 END AS capital_evidence,
           CASE WHEN noncurrent_assets_to_total_loans >= {{asset_quality_level_threshold}}
                     OR noncurrent_ratio_change_yoy_pp >= {{asset_quality_change_threshold}} THEN 1 ELSE 0 END AS asset_quality_evidence,
           CASE WHEN return_on_assets <= {{earnings_roa_threshold}}
                     AND consecutive_loss_quarters >= {{earnings_loss_threshold}} THEN 1 ELSE 0 END AS earnings_evidence,
           CASE WHEN estimated_deposit_outflow_pct >= {{deposit_outflow_threshold}}
                     AND (loans_to_deposits >= {{loans_to_deposits_threshold}}
                          OR fhlb_advances_to_total_assets >= {{fhlb_threshold}}) THEN 1 ELSE 0 END AS liquidity_funding_evidence,
           CASE WHEN equity_to_assets <= {{severe_equity_threshold}}
                     OR equity_to_assets_change_yoy_pp <= {{severe_capital_change_threshold}}
                THEN 1 ELSE 0 END AS independently_severe_capital,
           (CASE WHEN equity_to_assets IS NOT NULL OR equity_to_assets_change_yoy_pp IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN noncurrent_assets_to_total_loans IS NOT NULL OR noncurrent_ratio_change_yoy_pp IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN return_on_assets IS NOT NULL AND consecutive_loss_quarters IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN estimated_deposit_outflow_pct IS NOT NULL
                        AND (loans_to_deposits IS NOT NULL OR fhlb_advances_to_total_assets IS NOT NULL) THEN 1 ELSE 0 END
           ) AS available_category_count
    FROM phase3.core.bank_quarter_risk_features
), classified AS (
    SELECT *, capital_evidence+asset_quality_evidence+earnings_evidence+liquidity_funding_evidence AS distress_category_count
    FROM evidence
)
SELECT cert, rssdid, distress_date,
       CAST(LAST_DAY(DATE_TRUNC('quarter', distress_date) + INTERVAL 2 MONTH) AS DATE) AS distress_quarter,
       capital_evidence, asset_quality_evidence, earnings_evidence, liquidity_funding_evidence,
       independently_severe_capital, available_category_count, distress_category_count,
       CASE WHEN independently_severe_capital=1 THEN 'INDEPENDENTLY_SEVERE_CAPITAL'
            WHEN distress_category_count >= {{minimum_distress_categories}} THEN 'MULTI_CATEGORY'
            ELSE 'SENSITIVITY_ONLY' END AS distress_rule,
       CONCAT_WS('|',
          CASE WHEN capital_evidence=1 THEN 'CAPITAL' END,
          CASE WHEN asset_quality_evidence=1 THEN 'ASSET_QUALITY' END,
          CASE WHEN earnings_evidence=1 THEN 'EARNINGS' END,
          CASE WHEN liquidity_funding_evidence=1 THEN 'LIQUIDITY_FUNDING' END) AS distress_driver_categories,
       (independently_severe_capital=1 OR (available_category_count >= 3 AND distress_category_count >= {{minimum_distress_categories}})) AS primary_distress_event,
       distress_category_count >= 1 AS one_category_sensitivity_event,
       '{{distress_configuration_hash}}' AS distress_configuration_hash,
       '{{label_build_run_id}}' AS label_build_run_id
FROM classified
WHERE independently_severe_capital=1 OR distress_category_count >= 1
ORDER BY cert, distress_date;
