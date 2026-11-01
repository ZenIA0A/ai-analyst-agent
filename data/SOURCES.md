# Data sources

All data are published statistics, copied from the companion project `au-mortgage-stress-test` (which holds the raw downloads and the preparation script). Nothing is simulated.

| File | Source | Notes |
|---|---|---|
| `cash_rate_monthly.csv` | RBA table A2, monetary policy changes | Month-end cash rate target. The 30 September 2026 increase to 4.60% comes from news coverage of the decision. Trimmed to 2026-09-30 (an unobserved forward-filled October row was removed). |
| `rates_monthly.csv` | RBA table F5, indicator lending rates | Discounted and standard variable, interest-only, 3-year fixed and investor rates. Trimmed to 2026-09-30. The September lender rates were recorded before the 30 September hike took effect. |
| `macro_quarterly.csv` | RBA table E2 (household ratios), BIS and OECD via FRED | Debt-to-income, interest burden, house price index, unemployment. Quarterly to 2026Q2. |
| `apra_panel_quarterly.csv` | APRA quarterly ADI property exposures, June 2026 | By lender group: All ADIs, Major banks, Other domestic banks, Foreign subsidiary banks, Mutual ADIs. Masked cells are missing. Groups overlap (Mutual ADIs also sit inside bank tabs), so they do not sum to All ADIs. |

`interest_burden` is housing debt to income x discounted variable rate / 100 (a whole-stock approximation).
