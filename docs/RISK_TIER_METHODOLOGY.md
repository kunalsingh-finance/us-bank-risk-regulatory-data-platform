# Risk Tier Methodology

Risk tiers use same-quarter percentiles on a 0–100 scale:

| Tier | Percentile interval | Monitoring relationship |
|---|---:|---|
| Low | Below 50 | Outside top-5% monitoring |
| Moderate | 50 to below 90 | Outside top-5% monitoring |
| Elevated | 90 to below 95 | Immediately below the primary cutoff |
| High | 95 to below 99 | Inside top-5% monitoring |
| Highest monitored tier | 99 and above | Inside top-1% and top-5% monitoring |

Tiers are transparent relative groups, not invented likelihood categories. Ties share the same percentile and tier. CERT breaks ties only when the fixed operational budget must contain an exact integer count.
