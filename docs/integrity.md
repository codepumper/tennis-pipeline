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

### 3. Gap Field Validation Strategies

For fields marked as ❌ Gap, we implement specialized validation approaches:

#### Max Points in a Row (Contextual Logic)

- **Validation Approach:** Physical possibility & match dynamics
- **Implementation:**
  - Flag if streak > 12 points (3 consecutive service games without break)
  - Check if streak aligns with match duration (e.g., 10+ points in < 20 minutes = improbable)
  - Verify streak distribution (shouldn't be 100% on serve or return)
- **Alert Level:** `WARNING` (requires match context review)

#### Unforced Errors (Tournament Baseline)

- **Validation Approach:** Tournament-rolling statistical analysis
- **Implementation:**
  - Days 1-3: Collect data, calculate tournament mean/std
  - Day 4+: Activate Z-score flagging (µ = tournament mean, σ = tournament std)
  - Additional checks: Unforced Errors < Total Points (deterministic)
  - Cross-check: Compare opponent UE counts (large disparity flags for review)
- **Alert Level:** `OUTLIER` if |Z| > 3.0 after Day 3

#### Winners (Forehand/Backhand) (Hybrid Validation)

- **Validation Approach:** Derived ratios with tournament baseline
- **Implementation:**
  1. Check: Winners_FH + Winners_BH ≤ Total Points Won
  2. Ratio check: Winners_FH/Winners_BH within player's historical range (if available)
  3. Statistical: Tournament baseline from Days 1-3, Z-score from Day 4
  4. Extreme check: Flag if winners > 70% of points won (nearly impossible)
- **Alert Level:** Combined deterministic + probabilistic flags

#### Net Points Won (Style-based Logic)

- **Validation Approach:** Player archetype + match context
- **Implementation:**
  1. Check: Net Points Won ≤ Total Net Points Attempted
  2. Player classification:
     - Serve & Volley players: Expected net points = 25-40% of total points
     - Baseline players: Expected net points = 5-15% of total points
  3. Statistical: Tournament baseline from Days 1-3
- **Alert Level:** `STYLE_ANOMALY` + statistical outlier

#### UTR Rating (Format Only)

- **Validation Approach:** Data integrity without statistical comparison
- **Implementation:**
  1. Format: Must be decimal 1.00-16.99
  2. Consistency: Player UTR should not change > 1.0 within tournament
  3. Store only: Used for enrichment, not for outlier detection
- **Alert Level:** `FORMAT_ERROR` if invalid, `CONSISTENCY_WARNING` if large daily change


