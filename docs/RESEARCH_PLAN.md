# EdgeFoundry: BTC/USDT Intraday ML Edge Research Plan

**Protocol version:** 2.0-DRAFT, revision 2 (supersedes v1)
**Status:** Design approved, including the forward-holdout dates (D21, approved 2026-10-07). Not yet frozen. Binding only after the Freeze Config (Section 19) is committed and tagged `protocol-v2.0-frozen`.
**Companion document:** `PLATFORM_VISION.md` is parked, unchanged, and lower priority. Nothing in it may weaken this protocol.

Section 20 lists every decision with its status: **Settled** or **Approved** (agreed), or **Open** (needs input or verification before freeze). No value may be weakened to make a pass more likely.

---

## 1. Research Objective

Determine whether a small, validated ML model can produce positive, stable **net expectancy per trade** on unseen BTC/USDT 5-minute data after fees, spread, slippage and funding, under taker-only execution.

The research does not assume ML beats simple strategies. NO EDGE is a valid result. No real-money trading. Paper trading is not part of this research scope (Section 3, Phase 12 hands off to it).

---

## 2. Scope

**In scope:** BTC/USDT perpetual, 5-minute candles, long-only, OHLCV plus funding, cost model, trade simulator, XGBoost, probability calibration, nested walk-forward validation with purging and embargo, pre-registered trial grid, block permutation test, single-use forward holdout, experiment registry.

**Out of scope until the full protocol passes (G3):** LSTM or any other model, ensembles, regime logic, extra indicators beyond the two fixed feature sets, short selling, partial exits, maker orders, other markets (including NIFTY), Claude in any decision path, self-learning, paper trading, dashboard, FastAPI, PostgreSQL, Docker, cloud. These belong to `PLATFORM_VISION.md`.

---

## 3. Phase Map and Gates

Phases are sequential. A phase may not start until the previous phase's exit condition is met.

| Phase | Name | Exit condition |
|---|---|---|
| 0 | Freeze | **G0:** Freeze Config and trial grid committed and tagged (Section 19) |
| 1 | Data collection and integrity | **G1:** integrity report passes for the research period (Section 4.4); data version hashed. Holdout data is not acquired in this phase |
| 2 | Experiment registry | Registry enforces "no run without an ID"; trial grid loaded |
| 3 | Cost model and trade simulator | Simulator unit-tested against hand-computed trades |
| 4 | Label engine | Label tests pass, including window-length checks |
| 5 | Baselines | Baselines B1-B4 evaluated once on research test blocks, results stored |
| 6 | Feature engine | FS-1 and FS-2 implemented, look-ahead tests pass |
| 7 | Pipeline build and synthetic validation | Controls A, B, C pass (Section 9.6); compute feasibility of about 200 x 48 full pipeline evaluations measured and documented (Section 14.2) |
| 8 | Trial execution | All pre-registered trials run on the research period (max 50) |
| 9 | Selection and criteria | Top-ranked trial selected; criteria C1-C7 computed |
| 10 | Permutation test and research gate | **G2:** C1-C8 all satisfied, else STOP |
| 11 | Forward holdout: seal, wait, single evaluation | Artifacts sealed and tagged before 2027-01-01; no changes during the holdout; one batch evaluation only after 2028-04-30 23:55 UTC; **G3:** pass / fail / insufficient evidence (Section 15) |
| 12 | Final decision | Findings documented after G3; Path A or Path B (Section 16) |

---

## 4. Instrument, Data and Conventions

### 4.1 Instrument (decision O1: approved)

Approved and assumed throughout:

| Item | Value |
|---|---|
| Exchange | Binance |
| Instrument | BTCUSDT USD-M (USDT-margined, linear) perpetual futures |
| Contract type | Perpetual, no expiry |
| Quote / margin currency | USDT |
| Leverage in research | 1x notional (no leverage effect on returns) |
| Direction | Long-only (Section 6) |

Rationale for perpetual over spot: lower regular-tier taker fee (Section 5), a long 5-minute history, and a clean path to a later long/short branch. Cost: funding must be modelled (Section 6.7).

### 4.2 Data sources (decision O2: approved; fee and funding schedule re-verified on the actual freeze date, with source and date recorded in the Freeze Config)

| Item | Value |
|---|---|
| OHLCV | Binance public data archive for USD-M futures BTCUSDT 5m klines, verified against published checksums, with a sampled cross-check against the REST klines endpoint |
| Funding rates | Binance USD-M funding rate history (REST funding rate endpoint and archive), realized settlements |
| Funding schedule | Default 8-hour settlements at 00:00, 08:00 and 16:00 UTC. Binance may change a contract's interval (1 hour when a settlement hits the funding cap or floor since 2025-05-02, with 4-hour reversion rules since 2026-01-02). **Realized settlement timestamps from the funding history are authoritative.** Verified against the official Binance funding FAQ (updated 2026-03-06) on 2026-10-07 |
| Raw data | Stored read-only; never modified; source and download date recorded |
| Holdout data | Not acquired until the forward holdout has ended (Section 15.3, Step 5) |

Account or jurisdiction access is not needed for public historical data. It must be revisited before any paper-trading stage.

### 4.3 Conventions

- All times UTC. A candle is labelled by its open time and covers `[open_time, open_time + 5 min)`.
- Features for candle `t` use only candles up to and including `t`. The signal is evaluated at the close of `t`. The fill is at the open of `t+1`.
- Prices are the exchange last-trade klines. Mark price is not used.
- Missing candles are never forward-filled. Any sample whose feature window (288 candles back) or label window overlaps a missing candle is excluded.
- First 288 candles of the dataset are warm-up and excluded as samples.

### 4.4 Data integrity gate G1

Checks run automatically and the pipeline refuses to continue if any critical check fails:

- Duplicate candles (identical duplicates dropped and logged; conflicting duplicates are critical).
- Timestamp monotonicity, 5-minute alignment, UTC consistency (critical).
- OHLC invariants: `low <= min(open, close)`, `high >= max(open, close)`, all prices > 0, volume >= 0 (critical).
- Missing candles: coverage measured **per calendar week and per quarter, not only in aggregate**. Critical if any week has more than 2% missing, any quarter more than 0.5% missing, or any single gap exceeds 6 hours without a documented explanation.
- Abnormal volume and price jumps in the **research period** are listed for review, not auto-corrected. Any exclusion rule is decided in Phase 1, recorded, and applied uniformly before any outcome-based result exists.
- Funding series: spacing between realized settlements must be 1, 4 or 8 hours only; a spacing over 8 hours counts as a missing settlement; missing settlements at most 0.5% per quarter (critical otherwise); every non-8-hour period is listed in the integrity report.

**Holdout data.** The forward holdout (Section 15) lies in the future and is not acquired in Phase 1. G1 covers the research period only. The same structural checks run on holdout data at Phase 11, Step 5, and no return, volatility, price-level or outcome statistic may be computed on it before the single evaluation.

**Data version freeze.** At G1 the SHA-256 of every dataset file is recorded. Any later data change (re-download, patch, re-exclusion) requires a new protocol version.

The integrity report is committed. If G1 fails: STOP, no modelling.

---

## 5. Cost Model

Taker fills only. No maker orders, no rebates, no BNB or VIP discounts.

| Component | Optimistic | Base | **Conservative (primary gate)** |
|---|---:|---:|---:|
| Taker fee per side (bps) | 5.0 | 5.0 | 5.0 |
| Half-spread per side (bps) | 0.10 | 0.25 | 0.50 |
| Slippage per side (bps) | 0.50 | 1.00 | 2.00 |
| **Round-trip total (bps)** | **11.2** | **12.5** | **15.0** |

Plus actual realized funding (Section 6.7) in every scenario.

Notes:

- **Fee tier:** Binance Regular user, USD-M, taker 0.05% (5 bps). Source: Binance futures fee support article (updated 2026-05-01). Re-verify on the freeze date. The current rate is applied uniformly across the historical period; this is a stated simplification.
- **Spread:** OHLCV has no bid/ask. Spread and slippage are **fixed assumptions**, not estimates from data, chosen to be deliberately pessimistic for a highly liquid contract. They cannot be calibrated from OHLCV.
- **Size impact:** not modelled; notional is small relative to BTCUSDT depth (stated assumption).
- **Fee base:** charged on notional at entry and exit; the entry/exit notional difference is ignored.
- **Gate:** the Edge Gate uses Conservative only. Optimistic and Base are reported, never gated.
- **Freeze:** all cost values are frozen before any real-outcome result is seen.

Every result reports the decomposition:

```text
Gross P&L (bps)  = 1e4 * (exit_open / entry_open - 1)
Fees             = 2 * fee
Spread           = 2 * half_spread
Slippage         = 2 * slippage
Funding          = sum of settled funding in the hold interval (long pays when rate > 0)
Net P&L (bps)    = Gross - Fees - Spread - Slippage - Funding      (first-order additive convention)
```

---

## 6. Trade Protocol

### 6.1 Direction

Long-only. Long/short is a separate later research branch with its own protocol (funding asymmetry, different costs). It is not mixed in.

### 6.2 Entry rule

At the close of candle `t`, if the system is flat and sample `t` is eligible, then:

```text
if p_t >= theta:  enter long at open[t+1]
else:             no trade
```

- `p_t` is the **calibrated** probability of the label event (Section 7) from the fold's model and calibrator (in the holdout, from the single sealed final fit, Section 15.3).
- `theta` is the fold's threshold, selected only by nested validation (Section 9.4); in the holdout it is the single sealed value.
- Eligible means: no missing candles in the feature or label window, and `t + W` falls inside the current evaluation block (a research test block, an inner block V, or the whole holdout), so no trade can exit outside its block. `W = 14` candles.

### 6.3 Position rule

- One position at a time. No pyramiding, no reversal, no scaling.
- No new signal is evaluated while a position is open.
- After an exit fill at the open of candle `s`, the first eligible signal is evaluated at the close of candle `s` (entry at open of `s+1`). Consecutive trades therefore never overlap and always have at least one full candle between exit and next entry.

### 6.4 Exit rule

- **Fixed-horizon family (FH):** exit at `open[t+1+H]`. No stop, no target, no trailing.
- **Triple-barrier family (TB):** barriers evaluated on candle **closes only** (no intrabar ambiguity). For `j = 1..H_max`, with `r_j = close[t+j] / open[t+1] - 1`: exit at `open[t+j+1]` at the first `j` where `r_j >= +B_t` or `r_j <= -B_t`, or at `j = H_max` if neither occurs. `B_t = k * sigma_t * sqrt(H_max)`, where `sigma_t` is the standard deviation of 1-candle close-to-close log returns over the trailing 288 candles ending at the close of `t`.
- No other exits exist.

### 6.5 Position sizing

Fixed notional of 10,000 USDT per trade at 1x. **This is a simulation convention only.** The primary metric and every gate criterion are expressed in **basis points per unit of notional** and do not depend on account size. There is no compounding, no volatility or probability scaling, and no reinvestment.

The equity curve is the chronological **cumulative sum of per-trade net bps**. Drawdown is the peak-to-trough decline of that curve in bps, quoted as a percentage of notional for readability (100 bps = 1%). Changing the 10,000 USDT figure would not change any result.

### 6.6 Non-overlapping completed trades

A **qualifying trade** is a completed trade whose entry fill and exit fill both fall inside the same evaluation block (a research test block, an inner block V, or the whole holdout). Because of the position rule, intervals `[entry_fill_time, exit_fill_time)` of qualifying trades never overlap and label windows of consecutive trades never overlap. All trade counts in this protocol (C1, H1) count qualifying trades only. Signals that fire but are blocked by an open position are not trades.

### 6.7 Funding

For every trade, funding is the sum of realized settlement rates `rate_T` for settlement times `T` in the half-open interval `[entry_fill_time, exit_fill_time)`. Funding in bps is `1e4 * sum(rate_T)`, charged to longs when positive and credited when negative. Settlement times are the realized timestamps from the funding history, whatever the interval. Actual rates are used in all three cost scenarios. Funding stays tied to the actual timestamp, including inside permutation tests.

---

## 7. Labels

Entry and exit follow the executable trade, not a stylised close-to-close return.

**FH label (horizon `H` in candles):**

```text
gross_bps_t = 1e4 * (open[t+1+H] / open[t+1] - 1)
y_t = 1  if gross_bps_t > 15.0      (15.0 = Conservative round-trip cost, fixed)
y_t = 0  otherwise
```

The calibrated probability therefore estimates "this trade would beat conservative round-trip costs, before funding".

**TB label (`H_max`, multiplier `k`):** `y_t = 1` iff the upper barrier is the first barrier hit (Section 6.4); timeouts and lower hits are 0.

Label window length: at most 13 candles after `t`. A safe `W = 14` is used for purging.

Candidate horizons are exactly those in the trial grid (Section 11). No other horizon may be evaluated.

---

## 8. Features

Two fixed, pre-declared feature sets. No data-driven feature selection, no importance-based pruning, no mutual-information screening on real outcomes before selection (that would be peeking outside registered trials). Importance, correlation and stability are computed **only after selection, as diagnostics on the selected trial**, and cannot change the selection.

**FS-1 (6 features):**

| # | Name | Definition |
|---|---|---|
| 1 | ret_6 | `ln(close_t / close_{t-6})` |
| 2 | body_ratio | `(close_t - open_t) / max(high_t - low_t, eps)` |
| 3 | ema_dist | `close_t / EMA21(close)_t - 1` |
| 4 | rsi_14 | Wilder RSI, 14 |
| 5 | rel_vol_48 | `volume_t / mean(volume over t-47..t)` |
| 6 | atr_norm_14 | `ATR14_t / close_t` (Wilder) |

**FS-2 (10 features)** = FS-1 plus:

| # | Name | Definition |
|---|---|---|
| 7 | roc_12 | `close_t / close_{t-12} - 1` |
| 8 | roll_vol_48 | std of 1-candle log returns over 48 candles |
| 9 | dist_high_48 | `close_t / max(high over t-47..t) - 1` |
| 10 | dist_low_48 | `close_t / min(low over t-47..t) - 1` |

All features are scale-free ratios computed from trailing windows only. No fitted scaler is used. VWAP is **not** a feature in this protocol; it appears only in baseline B4. Any future feature addition is a new trial under a new hypothesis.

---

## 9. Validation Pipeline

### 9.1 Outer walk-forward geometry (research period)

| Item | Value |
|---|---|
| Research period | 2020-01-01 00:00 UTC to 2025-09-30 23:55 UTC |
| Test block | one calendar quarter |
| Rolling training window | the 18 months immediately before the test block |
| Step | 3 months |
| Outer folds | **17** (first test block 2021-Q3, last test block 2025-Q3) |

Example, fold 1: train 2020-01-01 to 2021-06-30, test 2021-07-01 to 2021-09-30. Fold 17: train 2024-01-01 to 2025-06-30, test 2025-07-01 to 2025-09-30.

No random shuffling anywhere. Every prediction uses only information available at its own time. This rolling retraining geometry applies to the **research period only**. The holdout uses a different, non-adaptive procedure (Section 15.3).

### 9.2 Purging and embargo

- The last **302 candles (288 embargo + 14 purge)** of every training sub-block (F, K, V below) are dropped. This removes any sample whose label window reaches into the next block and a one-day buffer against serial dependence.
- Feature computation may read earlier raw candles as past inputs; it never reads future candles.
- A unit test must assert that no training sample's label window overlaps the next block and that no test sample feeds any fitting step.

### 9.3 Inner split inside each outer training window

```text
|<------------- 18-month outer training window -------------->|  test block
|   F: months 1-12   | K: months 13-15 | V: months 16-18 |
|   fit model        | fit calibrator  | choose theta    |
   (each block loses its last 302 candles)
```

- **F:** fit XGBoost (fixed hyperparameters, no early stopping, no inner hyperparameter search).
- **K:** fit the calibrator on model scores for K (isotonic or Platt, per trial config). Nothing from V or the test block is used.
- **V:** select `theta` (Section 9.4).
- The model is **not** refit after `theta` is selected. The test block uses model(F) + calibrator(K) + theta(V).

### 9.4 Probability threshold methodology

Label base rates differ widely between families (a triple-barrier "upper barrier first" event can be rare), so the grid is defined **relative to the base rate** rather than as absolute probabilities that might be unreachable.

Let `pi_K` be the mean label on block K (after purge). Candidate grid (fixed): `theta = pi_K + delta`, with `delta` in `{0.00, 0.02, 0.04, 0.06, 0.08, 0.10, 0.15}` (values with `theta >= 1` are discarded).

On V, simulate the Section 6 trade protocol under **Conservative costs** for each `theta`, using V as the evaluation block. A `theta` is eligible if it yields at least 30 qualifying trades on V. Select the eligible `theta` with the highest mean net bps per trade; ties go to the higher `theta`. If no `theta` is eligible, or the best eligible `theta` has mean net bps <= 0 on V, the fold **abstains** (no trades in that test block). Abstention is a valid, expected outcome.

`theta` is never tuned on a test block or on the holdout.

### 9.5 Model configurations (frozen in config)

| ID | Description |
|---|---|
| M-S | XGBoost, max_depth 3, n_estimators 300, learning_rate 0.05, subsample 0.8, colsample_bytree 0.8, min_child_weight 50, reg_lambda 5 |
| M-D | XGBoost, max_depth 5, n_estimators 300, learning_rate 0.05, subsample 0.8, colsample_bytree 0.8, min_child_weight 20, reg_lambda 5 |

Objective `binary:logistic`, no class re-weighting, global seed 42. Exact vectors live in the Freeze Config. Calibration options: ISO (isotonic) or PLT (Platt scaling).

### 9.6 Synthetic controls (Phase 7, not trials)

Run on synthetic data only, never on real research outcomes:

- **Control A (null):** random-walk series with realistic volatility. The pipeline plus the Section 14 permutation procedure must not report a significant positive result (p > 0.05).
- **Control B (planted edge):** inject a known predictable component larger than conservative costs. The pipeline must recover positive net expectancy of at least half the planted amount.
- **Control C (leak injection):** add a deliberate look-ahead feature. The automated leakage tests must flag it.

Phase 7 does not complete until all three pass.

---

## 10. Baselines

Baselines are rule-based with **no fitted parameters**. They use the identical data, trade protocol (Section 6), fixed-hold exit, sizing and Conservative costs, evaluated on the same 17 test blocks and, in Phase 11 only, over the whole holdout as one block. They are evaluated for `H` in `{3, 6, 12}`.

| ID | Rule |
|---|---|
| B1 | Buy and hold across each test block (reported for context only, not used in the margin test) |
| B2 | Momentum: long if `close_t > close_{t-12}` |
| B3 | Trend: long if `EMA21_t > EMA55_t` and `close_t > EMA21_t` |
| B4 | VWAP: long if `close_t > VWAP_t` and at least 12 candles since 00:00 UTC, where VWAP is anchored to the UTC day (reset 00:00 UTC) using typical price `(H+L+C)/3` weighted by volume |

NO-TRADE (0 bps) is an implicit baseline; criterion C2 requires beating it by a margin. Baselines are not trials (no free parameters, evaluated once). Changing any baseline rule or parameter after the freeze is prohibited without a new protocol version.

For the baseline margin (C3), `B*` is the best of B2-B4 at the horizon matched to the selected trial (`H`, or `H_max` for TB trials), which is the conservative choice.

---

## 11. Trials: Definition, Budget and Pre-registered Grid

### 11.1 Definition of one trial

**One trial = one distinct, fully specified pipeline configuration (ConfigID) executed over the full research-period walk-forward (all 17 folds) against real outcomes.**

A ConfigID is the tuple: label family and parameters, feature set, model hyperparameter set, calibration method, threshold grid and selection rule, trade rule, seed.

| Question | Rule |
|---|---|
| Each hyperparameter configuration | **Counts** as a trial |
| Hyperparameter search | Not permitted inside the pipeline. Each distinct vector evaluated is a separate trial |
| Feature change (add, remove, change a window) | **Counts** as a new trial |
| Horizon, barrier, label change | **Counts** as a new trial |
| Calibration method change | **Counts** as a new trial |
| Threshold selection (Section 9.4) and calibrator fitting | Mechanical parts of the pipeline, **not** trials; replicated inside every permutation |
| Cost scenarios | Same trial. Optimistic, Base and Conservative are reporting views of one run. Changing cost values after freeze is prohibited |
| Seed | Fixed at 42 for all trials. Varying seeds to get a new draw is prohibited. A seed-stability check may be run on the selected trial afterwards as a diagnostic only |
| Baselines | Not trials (fixed, no free parameters), see Section 10 |
| Failed, crashed, aborted, invalid or discarded runs | **Count.** Any ConfigID that began executing against real research-period outcomes consumes budget regardless of outcome |
| Synthetic-data runs, unit tests | Do not count |
| Looking at feature-outcome relationships on real research data outside a registered trial | Prohibited |

A trial invalidated by a **documented implementation defect** may be re-run once with an identical specification after the fix. A defect qualifies only if it is evidenced independently of the trial's performance metrics (a failing test, a crash, a data-alignment or leakage error) and is documented **before** the rerun. Unfavourable results never qualify. The defect-audit checklist (failing unit test or crash; timestamp or alignment error; leakage-test failure; cost or funding mismatch against a hand-computed trade; non-reproducibility under a fixed seed; config-hash mismatch) is fixed in the registry before Phase 8 and applied identically whatever the results look like (including when G2 passes). Both runs are published. The rerun consumes a budget slot but is not a new distinct ConfigID for the permutation null.

### 11.2 Budget

**Total budget: 50 trials. Pre-registered grid: 48 configurations. 2 slots reserved for bug reruns.** The grid is non-adaptive: it is committed in full before the first real-outcome run, and no configuration may be added based on results. Trial counters are cumulative and never reset.

### 11.3 Pre-registered grid

**Family FH (24 trials):** `H` in {3, 6, 12} x feature set in {FS-1, FS-2} x model in {M-S, M-D} x calibration in {ISO, PLT}. IDs `TR-FH-001` to `TR-FH-024`.

**Family TB (24 trials):** (`H_max`, `k`) in {6, 12} x {1.0, 1.5, 2.0} x feature set in {FS-1, FS-2} x calibration in {ISO, PLT}, model M-S. IDs `TR-TB-001` to `TR-TB-024`.

Anything outside this grid requires a new protocol version (Section 16).

---

## 12. Primary Metric and Selection Rule

**Primary metric `M`:** pooled mean **net P&L per qualifying trade, in bps, under Conservative costs including actual funding**, over all qualifying trades across the 17 test blocks (trade-weighted).

Secondary metrics (reported, never substitutes): net return, profit factor, maximum drawdown, Sharpe-like ratio, win rate, trade count, average holding time, per-fold results, Optimistic and Base results, calibration error. The primary metric cannot be changed after any real-outcome result is seen.

**Eligibility:** a trial is eligible if it has at least 500 qualifying trades (C1). Ineligible trials score `-infinity`.

**Selection:** `T*` = the eligible trial with the highest `M`. Ties go to the trial with fewer features, then lower ConfigID. **Only `T*` is eligible to pass the gate.** If `T*` fails any criterion, the research gate fails. The runner-up is never substituted (that would add a hidden selection layer).

The full leaderboard of all executed trials, including failures, is published in the final report.

---

## 13. Edge Gate G2 (Research Period)

`T*` must satisfy **all** of the following. Thresholds are committed before any real-outcome result.

| ID | Criterion | Threshold |
|---|---|---|
| C1 | Qualifying OOS trades (pooled, non-overlapping) | >= 500 |
| C2 | Expectancy floor: `M` under Conservative costs | >= +2.0 bps/trade |
| C3 | Baseline margin: `M - M(B*)` under identical protocol and costs | >= +2.0 bps/trade (absolute, not percentage) |
| C4 | Fold stability: folds with positive Conservative net P&L (zero-trade folds do not count as positive) | >= 13 of 17 |
| C5 | Concentration: share of total net P&L from any single fold | <= 35% |
| C6 | Maximum drawdown of the pooled chronological equity curve | <= 20% of notional (2,000 bps) |
| C7 | Calibration sanity: pooled OOS expected calibration error (10 equal-frequency bins, all eligible test candles) | <= 0.05 |
| C8 | Best-of-N permutation test (Section 14) | p <= 0.05 |

If any criterion fails: **STOP** (Section 16). The gate has no override.

### 13.1 Trade-count feasibility (documentation, not a relaxation)

Capacity is the maximum number of qualifying trades one-position-at-a-time can produce. Consecutive entries are at least `H+1` candles apart in the FH family; TB trades hold at most `H_max` candles, so TB capacity is at least the FH capacity at the same horizon.

Research test blocks: 17 quarters, 1,553 days, about 447,000 candles. Forward holdout: 486 days (2027-01-01 to 2028-04-30), about 140,000 candles.

| Horizon (candles) | Research capacity | 500 trades as % of capacity | Holdout capacity | 150 trades as % of capacity |
|---:|---:|---:|---:|---:|
| 3 | about 111,800 | 0.45% | about 35,000 | 0.43% |
| 6 | about 63,900 | 0.78% | about 20,000 | 0.75% |
| 12 | about 34,400 | 1.45% | about 10,800 | 1.39% |

**Holdout length derivation (H1 is not weakened).** The C1 floor of 500 trades over 1,553 days is a rate of 0.322 trades per day. A `T*` at that floor needs at least `150 / 0.322 = 466` holdout days to expect 150 trades. Fifteen calendar months (455 days) falls short (about 147 expected). **Sixteen calendar months (486 days) is the shortest whole-month duration that works** (about 156 expected at the floor). A `T*` with more research trades needs fewer days: for expected 150 trades, 12 months (365 days) would need about 638 research trades, and 6 months about 1,280. Because `T*` is unknown at freeze, the length is set for the floor case.

Conclusions:

- The thresholds (500, 150, 17 folds, 30 inner trades on V) are arithmetically compatible with long-only, one-position-at-a-time and every horizon in the grid. 500 trades is about 29 trades per fold on average, the same order as the 30-trade eligibility count on V.
- The binding constraint is **selectivity**, not capacity. A model without real skill will either abstain in many folds or fail the V-expectancy test, which produces too few trades, too few positive folds (C4: at most 4 of 17 folds may abstain or lose), or a holdout with fewer than 150 trades.
- These thresholds are **intentionally strict and are not relaxed to reach a pass**. An insufficient trade count means failure at G2 (C1) or INSUFFICIENT EVIDENCE at G3 (H1), never a lowered threshold, a longer holdout, or a resampled holdout.
- At the C1 floor the expected holdout count (about 156) leaves only a thin margin over 150, and a `T*` that trades less often in the forward period than in research will end as INSUFFICIENT EVIDENCE. This is accepted. The sealed threshold is applied for 16 months, so activity depends on it staying appropriate. A sealed fit that abstains produces zero holdout trades and therefore INSUFFICIENT EVIDENCE.

---

## 14. Permutation Test (best-of-N)

**Purpose:** estimate how often the best result among the whole trial set arises by chance under a null where features carry no information about future outcomes, so that the 48-trial search is fully accounted for.

### 14.1 What is permuted

For every candle `t`, define its **outcome path**: the ratios needed to simulate a trade entered after `t`, namely `open[t+1+j] / open[t+1]` and `close[t+j] / open[t+1]` for `j = 1..12`. Outcome paths are computed from the real series.

Features stay exactly as computed on real data. Only the assignment of outcome paths to candles is permuted:

1. Split the research period into UTC-day blocks (288 candles, aligned to 00:00 UTC).
2. Stratify days by **(calendar quarter x weekday/weekend)**.
3. Within each stratum, randomly shuffle the order of day blocks. Candle at position `p` of day `d` receives the outcome path of position `p` of day `sigma(d)`. Time-of-day alignment and within-day autocorrelation of outcomes are preserved; the link between features and outcomes is broken.
4. Funding stays attached to the real timestamp. Costs are unchanged. The walk-forward geometry, purge and embargo are unchanged. TB barrier widths `B_t` use the real candle's own `sigma_t` (a feature-side quantity); only the outcome path is swapped.

This is a block permutation with 288-candle blocks (more than 20x the label window), not independent candle shuffling.

### 14.2 Procedure

For `b = 1..B` (**B = 200**; B is never reduced silently. If the Phase 7 measurement shows about 200 x 48 full pipeline evaluations is genuinely impractical, work stops and the decision is taken explicitly before Phase 8):

1. Build permuted outcome assignment `b` using seed `42 + b` (recorded).
2. For **every distinct ConfigID in the executed trial set** (N, normally 48): retrain the **complete pipeline** on permuted data (labels regenerated from permuted paths, model fit on F, calibrator on K, `theta` on V, all 17 folds), and compute `S_i^(b)` (same definition as the observed score, including the 500-trade eligibility rule).
3. Record `M^(b) = max_i S_i^(b)`, running the same selection rule as Section 12.

Observed statistic: `S_obs = M(T*)`, the best-of-N value on real data.

```text
p = (1 + #{ b : M^(b) >= S_obs }) / (B + 1)
```

With B = 200 the smallest attainable p is about 0.005.

### 14.3 Notes

- N for the null equals the number of distinct ConfigIDs actually executed, never fewer than the pre-registered grid, and cumulative across research cycles on the same data.
- Baseline and gate criteria other than C8 are not part of the permutation statistic.
- The permutation test is run once, after all trials are complete. Its results cannot trigger new trials.
- The holdout is never permuted or otherwise reused.

---

## 15. Final Holdout (G3): Forward Holdout

The final holdout is **forward data that does not exist yet**. It starts after the protocol is frozen and after every research and strategy decision is sealed, so no earlier work, chart viewing or backtest can have touched it.

### 15.1 Dates (decision D21)

| Period | Dates (UTC) | Status |
|---|---|---|
| Research | 2020-01-01 00:00 to 2025-09-30 23:55 | Used for Sections 9 to 14. Prior exposure of this period is UNKNOWN and disclosed as a limitation (Section 15.6) |
| **Retired window** | 2025-10-15 00:00 to 2026-09-30 23:55 | **RETIRED as the final holdout due to unresolved prior exposure.** Never used as a holdout |
| Unused interval | 2025-10-01 00:00 to 2026-12-31 23:55 | Excluded from training, calibration, selection, evaluation and the holdout. Contains the retired window and replaces the earlier 14-day embargo. Not acquired in Phase 1. Only the 288 candles before the holdout start may later be read, as past inputs to trailing features |
| **Forward holdout** | **2027-01-01 00:00 to 2028-04-30 23:55** | 16 calendar months, 486 days. Fixed before it begins. Length derived in Section 13.1 |

**Timing rules**

- The Freeze tag must be dated before 2027-01-01, and the `holdout-sealed` tag (Section 15.3, Step 3) must be dated before the holdout start.
- If G2 and the seal are not complete by 2026-12-15, the start moves to the first day of a later calendar month and the length stays 16 calendar months. The amendment is recorded before the original start. Dates may move only later, never earlier, never be shortened or extended, and never be changed for any reason other than schedule (no holdout data exists to influence it).
- Once the holdout has started, its dates are immutable.

### 15.2 G3 outcome space

The outcomes are PASS, FAIL or INSUFFICIENT EVIDENCE, decided by H1 to H5 (Section 15.5) after the full holdout period only.

### 15.3 G3 evaluation procedure (sealed single fit, forward evaluation)

**Step 1: freeze `T*`.** `T*` is fixed at G2 (Phase 10). Nothing about it may change afterwards.

**Step 2: sealed final fit (only if G2 passed).** Using only research-period data, run the Section 9.3 procedure once on the 18 months ending at the research end:

```text
Training window: 2024-04-01 to 2025-09-30
F (fit model):          2024-04-01 to 2025-03-31
K (fit calibrator):     2025-04-01 to 2025-06-30
V (choose theta):       2025-07-01 to 2025-09-30
(each block loses its last 302 candles; theta rule and abstention rule as in Section 9.4)
```

The outputs are three artifacts: the model, the calibrator and one `theta` value (or an abstention, in which case the holdout will contain no trades). The unused interval and the holdout are not used.

**Step 3: seal.** The artifacts and their SHA-256 hashes are written to the registry and committed to Git, with annotated tag `holdout-sealed`, **before the holdout start date**. All research and strategy decisions end here.

**Step 4: waiting period (2027-01-01 to 2028-04-30).** No change to `T*`, the artifacts, the Freeze Config, this protocol, or any code that affects evaluation. Any such change voids the holdout (it is burned) and a new cycle is needed. Holdout data is not downloaded, opened or analyzed. Market prices will of course be visible to the researcher during this period; no observation of them may be used for any decision, and the hash lock and tags make any change detectable.

**Step 5: acquisition (only after 2028-04-30 23:55 UTC has passed).** Acquire holdout OHLCV and funding from the two approved sources (archive, then REST cross-check), plus the 288 candles before 2027-01-01. Run the Section 4.4 structural checks only. If a critical check fails, re-acquire once from the alternate source. If it still fails, the result is `INSUFFICIENT EVIDENCE (data)` and the holdout is burned.

**Step 6: single evaluation.** Apply the sealed artifacts unchanged to the entire holdout in one batch run, using the Section 6 trade protocol and Conservative costs, with the whole holdout as one evaluation block (trades must complete inside it). The baselines (Section 10, no fitting) are evaluated over the same block at the matched horizon. The run emits no intermediate or per-block results.

**Step 7: decision.** H1 to H5 are computed and the decision is made only after the complete holdout period has been evaluated.

No holdout outcome is used for retraining, calibration, threshold selection, feature selection, model selection, protocol changes or any other adaptation. There are no updates, so later parts of the holdout never use earlier holdout outcomes. The sealed model will be 15 to 31 months old during the holdout. This is intentional and conservative: it is stricter than periodic retraining and keeps the holdout free of learning. The cost assumptions frozen at the freeze apply regardless of any fee or funding-schedule changes during the holdout; such changes are recorded as a note only.

### 15.4 Rules

- **Single use.** `T*` and the sealed artifacts are evaluated exactly once.
- Forward holdout data may not be used for feature selection, model selection, hyperparameters, threshold tuning, calibration choices, market selection, protocol changes or anything else.
- **If the holdout fails or is voided, it is burned.** It cannot be reused for tuning or re-testing. A new research cycle must use fresh future data.
- No holdout statistic of any kind may be computed before Step 6.
- No threshold relaxation, extension, shortening or resampling of the holdout.

### 15.5 Holdout pass rule

| ID | Criterion | Threshold |
|---|---|---|
| H1 | Qualifying completed trades (Section 6.6) | >= 150 |
| H2 | `M` under Conservative costs | >= +2.0 bps/trade |
| H3 | One-sided 90% lower confidence bound on mean net bps (block bootstrap over the trade sequence, block size 10 trades, 10,000 resamples, seed 42) | > 0 |
| H4 | Margin over the best matched baseline on the holdout, same protocol and costs | >= +2.0 bps/trade |
| H5 | Maximum drawdown of the cumulative net-bps curve | <= 10% of notional (1,000 bps) |

**Insufficient evidence:** if H1 fails (including when the sealed fit abstained), the result is `INSUFFICIENT EVIDENCE`. The threshold is **not** relaxed and the holdout is **not** extended or resampled. The edge is treated as not validated, the holdout is burned, and any further confirmation requires fresh forward data under a new protocol version.

Otherwise: all of H2-H5 satisfied is `PASS`; any failure is `FAIL`.

### 15.6 Prior exposure record

`prior_exposure` is still recorded in the Freeze Config, as stated by the researcher:

- An earlier BTC bot backtest run around August 2026. Its data start and end dates are **UNKNOWN** (no files verified).
- BTC prices and charts viewed during this project and earlier research. Dates **UNKNOWN**.

Consequences:

- The retired window (2025-10-15 to 2026-09-30) cannot be treated as untouched and is not used as a holdout.
- The forward holdout starts after the freeze and after the seal, so it cannot overlap any earlier exposure by construction.
- The research period (2020-01-01 to 2025-09-30) may have been examined by earlier work, including decisions about indicator choices. This is disclosed as a limitation in the Freeze Config and in the final report. It does not weaken any gate.
- The record cannot be edited after the tag.

---

## 16. Outcomes and Stop Rule

| Outcome | Condition | Consequence |
|---|---|---|
| **EDGE VALIDATED** | G2 pass and G3 pass | Path A: proceed to forward paper trading and `PLATFORM_VISION.md` |
| **NO EDGE** | G2 fail | Path B: stop. Document findings. No sealed fit is made and the holdout never starts being evaluated |
| **HOLDOUT FAIL** | G2 pass, G3 fail (H2-H5) | Path B. Holdout burned |
| **INSUFFICIENT EVIDENCE** | G3 H1 fails | Path B. Holdout burned. Needs fresh forward data |

The earliest possible G3 decision is after 2028-04-30. Until then, no new strategy work, platform work or paper trading is allowed (Section 21, rule 11).

After a G2 failure, allowed actions are limited to the defect audit and bug reruns defined in Section 11.1 (2 reserved slots). Not allowed: changing parameters, adding configurations, or relaxing thresholds to reach a pass.

Any new research cycle requires a new protocol version with a documented hypothesis. Trial counters are **cumulative on the same data**, so the permutation null grows with every added trial. The preferred route is fresh data (a later forward period) rather than more trials on the same research period.

---

## 17. Claude Policy

Claude is outside every decision path in this research. It must not generate or modify signals, select trades, tune thresholds, choose the winning model, or inspect the holdout before the single evaluation. Claude may assist with code, documentation, and post-hoc summaries, and any suggestion is validated independently.

---

## 18. Tooling and Repository

Stack: Python, Pandas (or Polars), NumPy, Scikit-learn, XGBoost, Parquet, DuckDB, Matplotlib/Plotly, Jupyter, Git. No production database or backend.

Components from the earlier research harness (data integrity checks, cost model, walk-forward, feature screen) may be reused only if they pass this protocol's tests. The prior feature screen must not be run on real research outcomes outside registered trials.

```text
edgefoundry/
  configs/        protocol_v2_freeze.yaml, trial_grid.yaml
  data/           raw/ (read-only), processed/
  src/            data, features, labels, baselines, models, validation, costs, experiments
  tests/
  experiments/    registry and per-trial results
  reports/
  docs/           RESEARCH_PLAN.md
  README.md  CHANGELOG.md  pyproject.toml
```

Documentation is limited to `README.md`, `RESEARCH_PLAN.md`, `CHANGELOG.md` until a module requires more. Correctness comes before reproducibility, reproducibility before efficiency, efficiency before optimization.

**Experiment registry** (Phase 2). Every real-outcome run needs an ID and records: experiment ID, trial number, ConfigID, date, git commit, data hash, config hash, seed, status (VALID, INVALID, ABORTED), reason for invalidation, results, decision. No run may execute without a registry entry.

---

## 19. FREEZE BEFORE CODE

**No implementation begins until the following is complete.** This is Phase 0 and gate G0.

1. Confirm no **Open** decision remains in Section 20 (O3 is closed by design and O5 is not applied) and complete the fee and funding-schedule verification on the freeze date.
2. Create `configs/protocol_v2_freeze.yaml` containing, at minimum:
   - **instrument** (exchange, symbol, contract type, quote currency, leverage convention)
   - **data source** (OHLCV source, funding source, funding schedule, timezone and candle convention) and the fee tier with its verification date
   - **dates** (research period, unused interval, forward holdout, walk-forward geometry)
   - **holdout** (forward holdout dates 2027-01-01 to 2028-04-30, the retired window and unused interval, the start-date postponement rule, single-use and burn rules, the Section 15.3 sealed-fit procedure with the `holdout-sealed` tag, and the `prior_exposure` record as stated in Section 15.6)
   - **cost model** (all three scenarios, fee, half-spread, slippage, funding convention)
   - **label and horizon** definitions (FH and TB, label cost threshold 15.0 bps, window `W = 14`)
   - **trade rule** (entry, position rule, exit rules, sizing, eligibility)
   - **threshold method** (base-rate-relative grid and `delta` values, inner split sizes, eligibility count, abstention rule, calibration method list)
   - **primary metric** and the selection rule
   - **gate thresholds** (C1-C8, H1-H5)
   - **trial budget** and definition (50 total, 48 pre-registered, 2 reruns)
   - **permutation procedure** (outcome-path definition, stratification, block length, B, seeds)
   - feature set definitions, model hyperparameter vectors, seed, bootstrap parameters, the defect-audit checklist, and the fee and funding-schedule verification (source and date)
3. Create `configs/trial_grid.yaml` with all 48 pre-registered ConfigIDs. (Data-version hashes are recorded later, at G1, in the registry and `CHANGELOG.md`, because the data does not exist at freeze.)
4. Compute SHA-256 hashes of both files and record them in `CHANGELOG.md`. Both files use LF line endings, enforced by `.gitattributes`; any later edit requires recomputing the hashes.
5. Commit both files and this document to Git and create tag `protocol-v2.0-frozen`. The Freeze tag must be dated before 2027-01-01. Holdout data is not acquired until after 2028-04-30.
6. The code must load these files at start-up and **refuse to run if either hash differs from the recorded value** (structural enforcement, not intent).

**Amendments:** any change after the tag requires a new protocol version and a recorded reason. An amendment made after any real-outcome result has been seen does not reset the trial counters.

Phase 1 may start only after step 5 is complete.

---

## 20. Decision Register

**Status:** Settled and Approved = agreed; Open = needs input or verification before freeze.

| ID | Decision | Value | Status |
|---|---|---|---|
| D01 | Direction | Long-only first; long/short is a separate branch | Settled |
| D02 | Trade-entry rule | Enter long at next open if calibrated `p >= theta` while flat | Settled (design) |
| D03 | Threshold methodology | Nested: F/K/V inner split, `theta` chosen on V under Conservative costs, never on test or holdout | Settled (design) |
| D04 | Threshold grid, min 30 inner trades, abstention rule | `theta = pi_K + delta`, `delta` in {0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.15} (relative to the base rate so rare TB labels remain tradable) | Approved |
| D05 | Calibration | Inner split K, no leakage; isotonic or Platt as trial dimension | Settled (design) |
| D06 | Position rule | One position at a time, no overlap, one-candle gap after exit | Settled |
| D07 | Exit rule | FH exit at `open[t+1+H]`; TB on closes, exit at next open | Settled (design); TB parameters Approved |
| D08 | Position sizing | Fixed notional, no compounding; 10,000 USDT at 1x is a simulation convention only; all metrics in bps of notional | Settled (design); convention value Approved |
| D09 | Primary metric | Net expectancy per trade, bps, Conservative costs incl. funding | Settled |
| D10 | Expectancy floor | >= +2.0 bps/trade | Approved |
| D11 | Baseline margin | >= +2.0 bps/trade absolute, matched horizon, best of B2-B4 | Approved |
| D12 | Trial definition | Section 11.1 | Approved |
| D13 | Total trial budget | 50 (48 pre-registered grid + 2 bug reruns) | Approved |
| D14 | Min OOS qualifying trades | >= 500 | Approved |
| D15 | Min holdout qualifying trades | >= 150 (unchanged); holdout length set to 16 months so H1 is feasible at the C1 floor (Section 13.1); else INSUFFICIENT EVIDENCE | Approved |
| D16 | Permutation procedure | Day-block outcome-path permutation, stratified, full retrain, best-of-N, B = 200 | Settled (design); parameters Approved |
| D17 | Cost assumptions | 11.2 / 12.5 / 15.0 bps round trip, taker only, fixed spread and slippage | Approved |
| D18 | Gating cost scenario | Conservative | Settled |
| D19 | Walk-forward geometry | 18-month train, 3-month test, 17 folds, 302-candle drop | Approved |
| D20 | Other gate thresholds | C4 13/17, C5 35%, C6 20%, C7 ECE 0.05, p 0.05; H3 90% bound, H5 10% | Approved |
| D21 | Holdout dates | **Forward holdout 2027-01-01 00:00 to 2028-04-30 23:55 UTC** (16 calendar months, 486 days). Retired window 2025-10-15 to 2026-09-30 (unresolved prior exposure). Unused interval 2025-10-01 to 2026-12-31 | Approved 2026-10-07 |
| D22 | Holdout single-use and burn rule | Section 15.4 | Settled |
| D30 | G3 evaluation procedure | Sealed single final fit (training 2024-04-01 to 2025-09-30), artifacts sealed and tagged before the holdout starts, no changes during the holdout, data acquired only after it ends, one batch evaluation, no updates, decision after full period | Settled (design); fit window Approved |
| D23 | Instrument | Binance USD-M BTCUSDT USDT-margined linear perpetual, long-only, 1x notional convention | Approved (O1) |
| D24 | Exchange and OHLCV source | Binance public USD-M futures BTCUSDT 5m archive, REST cross-check | Approved (O2) |
| D25 | Fee tier | Regular user, taker 5 bps. Preliminary check 2026-10-07 against the Binance support article updated 2026-05-01; must be re-verified on the freeze date and the source and date recorded | Approved; **verification pending** |
| D26 | Funding source and schedule | Binance USD-M funding history; default 8-hour settlements, interval may change, realized timestamps authoritative; verified 2026-10-07 on the official Binance funding FAQ (updated 2026-03-06) | Approved; verified |
| D27 | Timezone and candle convention | UTC, candle labelled by open time | Settled |
| D28 | Feature sets, model vectors, seeds | Section 8 and 9.5; model seed 42, H3 bootstrap seed 42, permutation seeds 42 + b | Approved |
| D29 | Permutation compute | B = 200 target; feasibility of about 200 x 48 evaluations verified before Phase 8; no silent reduction, stop and ask if impractical | Approved (O4) |

**Open items in detail:**

- **O3 (prior exposure): closed by design (D21 approved 2026-10-07).** The retired window is no longer used. `prior_exposure` is recorded as UNKNOWN for pre-freeze work and disclosed as a limitation of the research period (Section 15.6).
- **O5 (optional, not applied): model staleness.** The research period ends 2025-09-30, so the sealed model will be 15 to 31 months old during the holdout. This is conservative, not a leak. If you want a fresher model, the research period could be extended to 2026-09-30 (21 folds, C4 becomes 16 of 21, final-fit window 2025-04-01 to 2026-09-30). Decision 2026-10-07: **not applied**; the research period stays unchanged.
- **Verification on the freeze date:** the taker fee (D25) is re-verified and recorded with source and date. The funding schedule (D26) was verified on 2026-10-07; re-confirm only if the freeze date is later.

---

## 21. Non-Negotiable Rules

1. No look-ahead bias; no random shuffling of time-series data.
2. Purging and embargo are mandatory and unit-tested.
3. Costs, including funding, are applied before any result is judged; the Conservative scenario is the gate.
4. Calibration and threshold selection use inner splits only; nothing is tuned on a test block or the holdout.
5. Every real-outcome run is logged; failed and invalid runs count toward the budget.
6. The trial grid is pre-registered and non-adaptive; the budget cannot be exceeded without a new protocol version.
7. Gate thresholds, the primary metric and the permutation procedure are committed before any result; hashes are enforced in code.
8. Only the top-ranked trial may pass the gate; no runner-up substitution.
9. The holdout is forward data, single-use, evaluated with a sealed final fit that is never updated, with no protocol changes while it runs, its data acquired only after it ends, decided only after the full period, and burned if used.
10. A holdout with too few trades is INSUFFICIENT EVIDENCE; thresholds are never relaxed.
11. Claude is outside the decision path; no LSTM, no extra indicators, no dashboard, no self-learning, no production infrastructure before G3.
12. No real-money trading.
13. **NO EDGE -> NO TRADE.**

---

**Final research question:** under these frozen assumptions, does this specific ML approach show a robust, repeatable edge on unseen BTC/USDT 5-minute data after realistic costs? If yes, build the larger platform. If no, stop. Research first, platform second.
