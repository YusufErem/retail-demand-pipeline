# Rebuilding the Tableau Public dashboard

The dashboard reads the CSV extracts in `tableau/` (produced by the `export_tableau` task).

1. Sign in at [public.tableau.com](https://public.tableau.com) (free) and choose **Create → Web Authoring**.
   (Tableau Public Desktop works the same way.)
2. Connect to `tableau/weekly_total.csv`, then add the other files with **Data → New Data Source**.
3. Build one sheet per question:

| Sheet | Source | Columns | Rows | Marks / filters |
|---|---|---|---|---|
| Weekly revenue | `weekly_total.csv` | `week` (exact date, continuous) | `SUM(revenue)` | line |
| ABC Pareto curve | `abc_products.csv` | `rank` (continuous) | `AVG(cum_share)` | line, colour by `abc_class` |
| Top products, weekly units | `weekly_top_products.csv` | `week` | `SUM(units)` | filter `description` (single value), colour by `abc_class` |
| Forecast backtest | `backtest_summary.csv` | `AVG(wape)` | `method` | bars, sorted ascending, labels on |
| Revenue by country | `country_month.csv` | map: `country` as Country/Region | | size and colour by `SUM(revenue)` |

4. **Dashboard → New**, size 1200 × 800, drag the five sheets in. Title: *Retail demand: Online Retail II
   (2009–2011)*. Caption: *Data: Chen (2012), UCI Machine Learning Repository, CC BY 4.0.*
5. **File → Save to Tableau Public** as *Retail Demand Pipeline* and copy the public link into the README.
