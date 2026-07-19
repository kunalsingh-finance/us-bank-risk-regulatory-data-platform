CREATE TABLE staging.concentration_levels AS
WITH categories AS (
    SELECT
        cert, reporting_date, gross_loans_leases,
        construction_loans, multifamily_loans, residential_loans, commercial_industrial_loans,
        CASE WHEN consumer_loans IS NOT NULL AND credit_card_loans IS NOT NULL AND consumer_loans >= credit_card_loans
             THEN consumer_loans - credit_card_loans END AS consumer_ex_credit_card,
        credit_card_loans,
        (CASE WHEN construction_loans IS NULL THEN 0 ELSE construction_loans END
         + CASE WHEN multifamily_loans IS NULL THEN 0 ELSE multifamily_loans END
         + CASE WHEN residential_loans IS NULL THEN 0 ELSE residential_loans END
         + CASE WHEN commercial_industrial_loans IS NULL THEN 0 ELSE commercial_industrial_loans END
         + CASE WHEN consumer_loans IS NULL OR credit_card_loans IS NULL OR consumer_loans < credit_card_loans THEN 0 ELSE consumer_loans - credit_card_loans END
         + CASE WHEN credit_card_loans IS NULL THEN 0 ELSE credit_card_loans END) AS covered_balance,
        quarter_index
    FROM staging.feature_base
), levels AS (
    SELECT *,
        CASE WHEN gross_loans_leases > 0 AND construction_loans IS NOT NULL AND multifamily_loans IS NOT NULL AND residential_loans IS NOT NULL
             THEN 100.0 * (construction_loans + multifamily_loans + residential_loans) / gross_loans_leases END AS reported_real_estate_loans_to_total_loans,
        CASE WHEN gross_loans_leases > 0 THEN 100.0 * construction_loans / gross_loans_leases END AS construction_to_total_loans,
        CASE WHEN gross_loans_leases > 0 THEN 100.0 * multifamily_loans / gross_loans_leases END AS multifamily_to_total_loans,
        CASE WHEN gross_loans_leases > 0 THEN 100.0 * residential_loans / gross_loans_leases END AS residential_mortgages_to_total_loans,
        CASE WHEN gross_loans_leases > 0 THEN 100.0 * commercial_industrial_loans / gross_loans_leases END AS commercial_industrial_to_total_loans,
        CASE WHEN gross_loans_leases > 0 THEN 100.0 * consumer_ex_credit_card / gross_loans_leases END AS consumer_to_total_loans,
        CASE WHEN gross_loans_leases > 0 THEN 100.0 * credit_card_loans / gross_loans_leases END AS credit_card_to_total_loans,
        CASE WHEN gross_loans_leases > 0 THEN 100.0 * GREATEST(construction_loans, multifamily_loans, residential_loans,
             commercial_industrial_loans, consumer_ex_credit_card, credit_card_loans) / gross_loans_leases END AS largest_reported_loan_category_share,
        CASE WHEN covered_balance > 0 THEN
             (POWER(COALESCE(construction_loans, 0) / covered_balance, 2)
              + POWER(COALESCE(multifamily_loans, 0) / covered_balance, 2)
              + POWER(COALESCE(residential_loans, 0) / covered_balance, 2)
              + POWER(COALESCE(commercial_industrial_loans, 0) / covered_balance, 2)
              + POWER(COALESCE(consumer_ex_credit_card, 0) / covered_balance, 2)
              + POWER(COALESCE(credit_card_loans, 0) / covered_balance, 2)) END AS loan_concentration_hhi,
        CASE WHEN gross_loans_leases > 0 THEN 100.0 * covered_balance / gross_loans_leases END AS loan_category_coverage_ratio
    FROM categories
)
SELECT * FROM levels;

CREATE TABLE staging.concentration_features AS
WITH lagged AS (
    SELECT *, LAG(loan_concentration_hhi, 4) OVER bank_history AS year_ago_hhi,
           LAG(reporting_date, 4) OVER bank_history AS year_ago_date
    FROM staging.concentration_levels
    WINDOW bank_history AS (PARTITION BY cert ORDER BY reporting_date)
)
SELECT *,
       CASE WHEN year_ago_date = LAST_DAY(reporting_date - INTERVAL 12 MONTH)
            THEN loan_concentration_hhi - year_ago_hhi END AS concentration_change_yoy,
       CASE WHEN loan_concentration_hhi IS NULL OR loan_category_coverage_ratio IS NULL THEN NULL
            WHEN loan_concentration_hhi >= 0.50 AND loan_category_coverage_ratio >= 60 THEN 1 ELSE 0 END AS concentration_pressure_flag
FROM lagged;
