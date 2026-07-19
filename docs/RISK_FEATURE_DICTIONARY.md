# Risk Feature Dictionary

These are transparent **public-data CAMELS-style risk indicators**, not official CAMELS ratings. Raw calculated values are preserved; nulls are not imputed; unsupported regulatory fields are excluded.

| Feature | Category | Formula | Units | Direction | Availability / missingness | Peer | Limitation |
|---|---|---|---|---|---|---|---|
| `equity_to_assets` | Capital | 100 * equity / asset | percent | Lower value = higher risk | 2001-03-31–2026-03-31; 0.147% missing | Yes | Accounting equity is not regulatory capital |
| `equity_change_qoq_pct` | Capital | 100 * change / abs(prior equity) | percent | Lower value = higher risk | 2001-06-30–2026-03-31; 1.729% missing | No | Percentage change can be unstable near zero equity |
| `equity_change_yoy_pct` | Capital | 100 * change / abs(lag equity) | percent | Lower value = higher risk | 2002-03-31–2026-03-31; 6.383% missing | Yes | Percentage change can be unstable near zero equity |
| `equity_to_assets_change_qoq_pp` | Capital | current minus one-quarter lag | percentage points | Lower value = higher risk | 2001-06-30–2026-03-31; 1.729% missing | No | Requires consecutive quarters |
| `equity_to_assets_change_yoy_pp` | Capital | current minus four-quarter lag | percentage points | Lower value = higher risk | 2002-03-31–2026-03-31; 6.383% missing | No | Requires exact year-ago quarter |
| `equity_to_assets_slope_8q` | Capital | REGR_SLOPE over trailing eight quarters | percentage points per quarter | Lower value = higher risk | 2002-12-31–2026-03-31; 10.901% missing | No | Short-window linear trend |
| `equity_to_assets_volatility_8q` | Capital | STDDEV_SAMP over trailing eight quarters | percentage points | Higher value = higher risk | 2002-12-31–2026-03-31; 10.901% missing | No | Volatility is descriptive, not causality |
| `capital_deterioration_flag` | Capital | 1 when equity ratio falls materially | flag | Higher value = higher risk | 2001-06-30–2026-03-31; 1.729% missing | No | Screening flag, not an official CAMELS rating |
| `past_due_30_89_to_total_loans` | Asset quality | 100 * numerator / denominator | percent | Higher value = higher risk | 2001-03-31–2026-03-31; 0.773% missing | Yes | Source is past-due assets, used as a loan-denominator proxy |
| `past_due_90_plus_to_total_loans` | Asset quality | 100 * numerator / denominator | percent | Higher value = higher risk | 2001-03-31–2026-03-31; 0.773% missing | Yes | Source is past-due assets, used as a loan-denominator proxy |
| `nonaccrual_assets_to_total_loans` | Asset quality | 100 * numerator / denominator | percent | Higher value = higher risk | 2001-03-31–2026-03-31; 0.773% missing | Yes | Nonaccrual assets are broader than nonaccrual loans |
| `noncurrent_assets_to_total_loans` | Asset quality | 100 * numerator / denominator | percent | Higher value = higher risk | 2001-03-31–2026-03-31; 0.773% missing | Yes | Public-data proxy, not FDIC noncurrent-loan ratio |
| `net_chargeoffs_to_average_loans` | Asset quality | 400 * quarterly flow / average loans | annualized percent | Higher value = higher risk | 2001-06-30–2026-03-31; 2.496% missing | Yes | Requires valid prior-quarter balance |
| `noncurrent_ratio_change_qoq_pp` | Asset quality | current minus one-quarter lag | percentage points | Higher value = higher risk | 2001-06-30–2026-03-31; 2.352% missing | No | Requires consecutive quarters |
| `noncurrent_ratio_change_yoy_pp` | Asset quality | current minus four-quarter lag | percentage points | Higher value = higher risk | 2002-03-31–2026-03-31; 6.978% missing | No | Requires exact year-ago quarter |
| `noncurrent_ratio_slope_8q` | Asset quality | REGR_SLOPE over trailing eight quarters | percentage points per quarter | Higher value = higher risk | 2002-12-31–2026-03-31; 11.476% missing | No | Short-window linear trend |
| `noncurrent_ratio_volatility_8q` | Asset quality | STDDEV_SAMP over trailing eight quarters | percentage points | Higher value = higher risk | 2002-12-31–2026-03-31; 11.476% missing | No | Proxy volatility |
| `asset_quality_deterioration_flag` | Asset quality | 1 when noncurrent proxy rises materially | flag | Higher value = higher risk | 2001-06-30–2026-03-31; 2.310% missing | No | Screening flag only |
| `return_on_assets` | Earnings | Direct FDIC quarterly ROA | annualized percent | Lower value = higher risk | 2001-03-31–2026-03-31; 0.147% missing | Yes | Do not double annualize |
| `return_on_equity` | Earnings | 400 * quarterly income / average equity | annualized percent | Lower value = higher risk | 2001-06-30–2026-03-31; 1.795% missing | Yes | Undefined for nonpositive average equity |
| `net_interest_margin` | Earnings | Direct FDIC quarterly NIM | annualized percent | Lower value = higher risk | 2001-03-31–2026-03-31; 0.161% missing | Yes | Rounded source-reported quarterly margin |
| `efficiency_ratio` | Earnings | Direct FDIC quarterly efficiency ratio | percent | Higher value = higher risk | 2001-03-31–2026-03-31; 0.164% missing | Yes | Extreme values may reflect small denominators |
| `net_income_to_average_assets` | Earnings | 400 * quarterly income / average assets | annualized percent | Lower value = higher risk | 2001-06-30–2026-03-31; 1.729% missing | No | Requires valid prior-quarter assets |
| `net_interest_income_to_average_assets` | Earnings | 400 * quarterly amount / average assets | annualized percent | Lower value = higher risk | 2001-06-30–2026-03-31; 1.729% missing | No | Not equivalent to NIM because denominator differs |
| `noninterest_expense_to_average_assets` | Earnings | 400 * quarterly amount / average assets | annualized percent | Higher value = higher risk | 2001-06-30–2026-03-31; 1.729% missing | No | Requires valid prior-quarter assets |
| `roa_change_qoq_pp` | Earnings | current minus one-quarter lag | percentage points | Lower value = higher risk | 2001-06-30–2026-03-31; 1.729% missing | No | Requires consecutive quarters |
| `roa_change_yoy_pp` | Earnings | current minus four-quarter lag | percentage points | Lower value = higher risk | 2002-03-31–2026-03-31; 6.383% missing | No | Requires exact year-ago quarter |
| `roa_mean_8q` | Earnings | AVG over trailing eight quarters | annualized percent | Lower value = higher risk | 2002-12-31–2026-03-31; 10.901% missing | Yes | Backward-looking mean |
| `roa_volatility_8q` | Earnings | STDDEV_SAMP over trailing eight quarters | percentage points | Higher value = higher risk | 2002-12-31–2026-03-31; 10.901% missing | Yes | Backward-looking volatility |
| `consecutive_loss_quarters` | Earnings | running count since last non-loss quarter | quarters | Higher value = higher risk | 2001-03-31–2026-03-31; 0.147% missing | No | Null income resets no evidence and is flagged |
| `earnings_deterioration_flag` | Earnings | 1 when ROA deteriorates or losses persist | flag | Higher value = higher risk | 2001-03-31–2026-03-31; 0.147% missing | No | Screening flag only |
| `liquid_assets_to_total_assets` | Liquidity | 100 * proxy liquid assets / assets | percent | Lower value = higher risk | 2001-03-31–2026-03-31; 0.000% missing | Yes | Broad proxy; securities liquidity varies |
| `loans_to_deposits` | Liquidity | 100 * loans / deposits | percent | Higher value = higher risk | 2001-03-31–2026-03-31; 0.027% missing | Yes | Does not capture all funding sources |
| `deposits_to_total_assets` | Funding | 100 * deposits / assets | percent | Lower value = higher risk | 2001-03-31–2026-03-31; 0.000% missing | Yes | Deposit composition unavailable in Core-v1 |
| `assessable_deposits_to_total_deposits` | Funding | 100 * assessable deposits / deposits | percent | Descriptive only | 2001-03-31–2026-03-31; 0.053% missing | No | Not brokered or uninsured deposits |
| `fhlb_advances_to_total_assets` | Funding | 100 * advances / assets | percent | Higher value = higher risk | 2001-03-31–2026-03-31; 0.147% missing | Yes | Only FHLB advances, not all wholesale funding |
| `deposit_growth_qoq_pct` | Funding | 100 * change / abs(prior deposits) | percent | Non-monotonic | 2001-06-30–2026-03-31; 1.602% missing | No | Rapid decline or growth can both warrant review |
| `deposit_growth_yoy_pct` | Funding | 100 * change / abs(year-ago deposits) | percent | Non-monotonic | 2002-03-31–2026-03-31; 6.257% missing | Yes | Rapid decline or growth can both warrant review |
| `estimated_deposit_outflow_pct` | Funding | 100 * max(prior-current,0) / prior | percent | Higher value = higher risk | 2001-06-30–2026-03-31; 1.602% missing | Yes | Accounting change proxy, not observed cash outflow |
| `funding_cost` | Funding | Direct FDIC quarterly funding cost | annualized percent | Higher value = higher risk | 2001-03-31–2026-03-31; 0.161% missing | Yes | Do not double annualize |
| `funding_cost_change_qoq_pp` | Funding | current minus one-quarter lag | percentage points | Higher value = higher risk | 2001-06-30–2026-03-31; 1.743% missing | No | Requires consecutive quarters |
| `funding_cost_change_yoy_pp` | Funding | current minus four-quarter lag | percentage points | Higher value = higher risk | 2002-03-31–2026-03-31; 6.397% missing | No | Requires exact year-ago quarter |
| `liquidity_deterioration_flag` | Liquidity | 1 when liquid share falls or loan/deposit pressure is high | flag | Higher value = higher risk | 2001-03-31–2026-03-31; 0.006% missing | No | Screening flag only |
| `funding_pressure_flag` | Funding | 1 when outflow, cost, or FHLB reliance is elevated | flag | Higher value = higher risk | 2001-03-31–2026-03-31; 0.002% missing | No | Screening flag only |
| `reported_real_estate_loans_to_total_loans` | Concentration | 100 * categories / gross loans | percent | Non-monotonic | 2001-03-31–2026-03-31; 0.827% missing | No | Reported categories are an incomplete CRE/business-model proxy |
| `construction_to_total_loans` | Concentration | 100 * category / gross loans | percent | Higher value = higher risk | 2001-03-31–2026-03-31; 0.827% missing | Yes | Concentration does not imply loss |
| `multifamily_to_total_loans` | Concentration | 100 * category / gross loans | percent | Non-monotonic | 2001-03-31–2026-03-31; 0.827% missing | Yes | Business-model descriptor |
| `residential_mortgages_to_total_loans` | Concentration | 100 * category / gross loans | percent | Non-monotonic | 2001-03-31–2026-03-31; 0.827% missing | No | Business-model descriptor |
| `commercial_industrial_to_total_loans` | Concentration | 100 * category / gross loans | percent | Non-monotonic | 2001-03-31–2026-03-31; 0.773% missing | No | Business-model descriptor |
| `consumer_to_total_loans` | Concentration | 100 * max(consumer-credit cards,0) / gross loans | percent | Non-monotonic | 2001-03-31–2026-03-31; 0.919% missing | No | Assumes credit cards are nested within consumer loans |
| `credit_card_to_total_loans` | Concentration | 100 * category / gross loans | percent | Non-monotonic | 2001-03-31–2026-03-31; 0.919% missing | No | Business-model descriptor |
| `largest_reported_loan_category_share` | Concentration | 100 * max category / gross loans | percent | Higher value = higher risk | 2001-03-31–2026-03-31; 0.773% missing | Yes | Only six reported categories |
| `loan_concentration_hhi` | Concentration | sum((category/covered total)^2) | 0-to-1 index | Higher value = higher risk | 2001-03-31–2026-03-31; 0.851% missing | Yes | Incomplete portfolio HHI; categories documented and coverage retained |
| `loan_category_coverage_ratio` | Concentration | 100 * covered categories / gross loans | percent | Descriptive only | 2001-03-31–2026-03-31; 0.773% missing | No | Coverage may exceed expectations if source categories overlap or definitions shift |
| `concentration_change_yoy` | Concentration | current minus four-quarter lag | index change | Higher value = higher risk | 2002-03-31–2026-03-31; 7.046% missing | No | Requires comparable category coverage |
| `concentration_pressure_flag` | Concentration | 1 when HHI is high with adequate coverage | flag | Higher value = higher risk | 2001-03-31–2026-03-31; 0.851% missing | No | Screening flag only |
| `total_asset_growth_qoq_pct` | Growth | 100 * change / abs(prior assets) | percent | Higher value = higher risk | 2001-06-30–2026-03-31; 1.585% missing | No | Growth may be merger-driven |
| `total_asset_growth_yoy_pct` | Growth | 100 * change / abs(year-ago assets) | percent | Higher value = higher risk | 2002-03-31–2026-03-31; 6.246% missing | Yes | Growth may be merger-driven |
| `total_loan_growth_qoq_pct` | Growth | 100 * change / abs(prior loans) | percent | Higher value = higher risk | 2001-06-30–2026-03-31; 2.335% missing | No | Growth may reflect portfolio transfers |
| `total_loan_growth_yoy_pct` | Growth | 100 * change / abs(year-ago loans) | percent | Higher value = higher risk | 2002-03-31–2026-03-31; 6.944% missing | Yes | Growth may reflect portfolio transfers |
| `equity_growth_yoy_pct` | Growth | 100 * change / abs(year-ago equity) | percent | Lower value = higher risk | 2002-03-31–2026-03-31; 6.383% missing | No | Unstable near zero equity |
| `loan_growth_minus_deposit_growth` | Growth | year-over-year loan growth minus deposit growth | percentage points | Higher value = higher risk | 2002-03-31–2026-03-31; 6.945% missing | Yes | Relative growth pressure proxy |
| `rapid_asset_growth_flag` | Growth | 1 when year-over-year asset growth exceeds 25% | flag | Higher value = higher risk | 2002-03-31–2026-03-31; 6.246% missing | No | Threshold is a screening rule |
| `rapid_loan_growth_flag` | Growth | 1 when year-over-year loan growth exceeds 25% | flag | Higher value = higher risk | 2002-03-31–2026-03-31; 6.944% missing | No | Threshold is a screening rule |
| `funding_gap_flag` | Growth | 1 when loan growth exceeds deposit growth by 15 points | flag | Higher value = higher risk | 2002-03-31–2026-03-31; 6.945% missing | No | Screening rule, not liquidity forecast |

## Explicitly unsupported candidates

The following requested candidates were not built because their inputs were excluded from the approved Core-v1 contract: `tier1_leverage_ratio`, `tier1_risk_based_capital_ratio`, `total_risk_based_capital_ratio`, `regulatory_capital_buffer`, `allowance_to_total_loans`, `allowance_to_noncurrent_loans`, `provisions_to_average_assets`, `provision_burden`, `brokered_deposits_to_total_deposits`, `uninsured_deposits_to_total_deposits`, `short_term_borrowings_to_total_assets`, `other_borrowed_funds_to_total_assets`, `agricultural_loans_to_total_loans`.

The authoritative machine-readable metadata is `configs/risk_features.yaml`; empirical counts are in `reports/feature_inventory.csv`.
