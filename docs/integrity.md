# 🎾 AO 2026: Data Strategy & Mapping Guide

## SofaScore Live vs. Sackmann Historical Baseline

This document outlines the architectural strategy for the 2026 Australian Open data pipeline. We categorize every data point into Deterministic (Common Sense) or Probabilistic (Statistical Deviation) checks.

## 1. Validation Strategy

### A. Deterministic Checks (Common Sense Logic)

These values are verified using hard-coded business rules. Any violation indicates a critical data integrity failure (e.g., scraping errors).

- **Age Logic**: Age must be $\ge 14$ and increment by 1 year maximum per season.
- **Match Duration**: For a "Best of 5" Grand Slam match, Duration must be $> 45$ minutes and $< 480$ minutes.
- **Serve Consistency**: 1st_In must always be $\le$ Total_Serve_Points.
- **Surface**: Must equal Outdoor Hard for Australian Open matches.

### B. Probabilistic Checks (Statistical Logic)

For these values, we calculate a Z-Score ($Z = \frac{x - \mu}{\sigma}$) based on the 2021–2025 Grand Slam Hard Court baseline.

- **Clean** ($|Z| \le 1.5$): Typical performance.
- **Warning** ($1.5 < |Z| \le 3.0$): High-performance spike or technical struggle.
- **Outlier** ($|Z| > 3.0$): Statistically improbable. Flags for manual review (e.g., Shelton's 100% 2nd serve points won).

## 2. Full Mapping Matrix

This matrix maps live SofaScore fields to the corresponding Sackmann historical columns to establish the "Truth Engine" baseline.

| SofaScore Live Statistic | Sackmann Baseline Column | Baseline Calculation Logic | Mapping Status |
|--------------------------|--------------------------|----------------------------|----------------|
| Aces | w_ace / l_ace | Total Count | ✅ Direct |
| Double Faults | w_df / l_df | Total Count | ✅ Direct |
| First Serve % | w_1stIn / w_svpt | 1stIn / svpt | ✅ Direct |
| 1st Serve Points Won % | w_1stWon / w_1stIn | 1stWon / 1stIn | ✅ Direct |
| 2nd Serve Points Won % | w_2ndWon / (svpt - 1stIn) | 2ndWon / (svpt - 1stIn) | ✅ Direct |
| Break Points Saved % | w_bpSaved / w_bpFaced | bpSaved / bpFaced | ✅ Direct |
| Service Games Won | w_SvGms | Total Count | ✅ Direct |
| Total Points Won | w_svpt + l_svpt | (Derived) Sum of pts | ✅ Derived |
| 1st Serve Return Pts | l_svpt - l_1stIn ... (l_1stIn - l_1stWon) | (l_1stIn - l_1stWon) | ✅ Derived |
| Max Pts in a Row | N/A | No historical equivalent | ❌ Gap |
| Unforced Errors | N/A | Not in standard Sackmann | ❌ Gap |
| Winners (FH/BH) | N/A | Not in standard Sackmann | ❌ Gap |
| Net Points Won | N/A | Not in standard Sackmann | ❌ Gap |
| UTR Rating | N/A | Proprietary Sofa/UTR | ❌ Gap |

## 3. Handling Data Gaps

For fields marked as ❌ Gap (like Unforced Errors or Winners):

- **Contextual Baseline**: We cannot use Sackmann for these. Instead, the pipeline will build its own rolling baseline during the 2026 tournament.
- **Logic**: The first 3 days of AO 2026 will be used to calculate a "Tournament Mean" for Unforced Errors. From Day 4 onwards, Z-score flagging will activate for these fields.

## 4. Enrichment Implementation (Python/Pydantic)

Every scraped record will be transformed into an augmented JSON before being saved to Parquet:

```json
{
  "player": "Ben Shelton",
  "stat": "1st_serve_pct",
  "value": 0.72,
  "historical_mu": 0.62,
  "historical_sigma": 0.07,
  "z_score": 1.42,
  "status": "CLEAN"
}