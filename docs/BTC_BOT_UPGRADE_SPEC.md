# BTC Bot Upgrade Spec: "Best ROI for Invest"

> Instructions for Claude Code. Read this entire file before writing any code.
> Work phase by phase (section 8), following the run mode in section 11: run all phases in one go and stop only at the stop points listed there.
> **Language:** the bot's user-facing language is Vietnamese (section 6). Also write all phase summaries, questions to me, `docs/AUDIT.md` and `docs/RESULTS.md` in Vietnamese. Code, identifiers and code comments may stay in English.
> **Theme:** I like the bot's current look. Keep it exactly as it is (section 6.4).

## 0. Context

This repo contains a statistical (non-AI) BTC bot that writes a weekly Vietnamese report ("Báo cáo bot BTC"). The report includes:
- a buy score ("Tỷ lệ nên mua") and a sell score ("Tỷ lệ nên bán");
- buy buckets (Phải mua ≥80%, Cân nhắc mua 60–80%) and sell buckets (Nên bán ≥85%, Cân nhắc bán 70–85%);
- price thresholds, win probabilities at 1/3/6/12 months, a ranking of indicator sets, sell-side criteria and a hold/take-profit simulation.

Current data sources: Binance, CoinGecko, Alternative.me Fear & Greed, Coin Metrics. Scoring starts 2020-08-02, weekly evaluation, walk-forward.

Problems observed in the 2026-10-28 report. Treat these as hypotheses to verify in the code, not as facts:
1. The primary objective is win rate (price higher after N months), not return or cost basis.
2. History is short (~1.5 cycles). "Phải mua" has only 5 independent episodes, and many sell criteria have only 3–7.
3. Selection bias: many indicator sets are tested on the same window and the best one is picked ("Bộ bot tìm được").
4. Instability: Phương án 1 and 2 win only 21–28% when signalling "Phải mua", which is worse than the 54–63% base rate. Phương án 4 wins 60% in the first half vs 25% in the second. The Fear & Greed weight is −1.09, opposite to the economic prior.
5. The all-indicators set (10 features) does worse than Pi Cycle alone (59% vs 84% at 6 months), which points to overfitting or collinearity.
6. Only slow cycle indicators are used, so there is no edge at the 1-month horizon ("Phải mua" wins 54% at 1 month, equal to the base rate).
7. Buy decisions are stepwise buckets with no position sizing and no comparison against plain DCA.

## 1. Ground rules (non-negotiable)

- **Advisory only.** The bot never places orders, never stores exchange API keys with trade or withdraw permission, and never uses leverage or derivatives positions. It reads public data and writes reports.
- **No look-ahead.** Every feature value used at decision date t must have been publicly available at t. Apply publication lags and use as-of joins only.
- **Holdout is locked.** The final test period (section 5) can only be evaluated with an explicit `--final` flag, which logs the run. Nothing is ever tuned on it.
- **Log every experiment** to `experiments/registry.csv` (timestamp, git hash, config hash, features, params, metrics). Report the total number of trials alongside results.
- **Simplicity wins ties.** A new feature or layer stays only if it improves out-of-sample metrics in an ablation test. Otherwise remove it.
- **Fail safe to DCA.** If required data is stale or missing, or a model check fails, the recommendation falls back to multiplier = 1.0 (plain DCA) and the report states why.
- **Don't break the current report or its theme.** Before refactoring, freeze current outputs with regression tests. Keep the existing visual theme (colors, fonts, layout, table style, icons, section order). New sections reuse existing styles and components; never introduce a new design.
- **Vietnamese everywhere the user looks.** All user-facing text is Vietnamese, comes from one translation file, and follows Vietnamese number and date formats (section 6).
- **Optimize the bad case, not the average.** When choosing between candidates, prefer the one with the better 10th-percentile outcome (P10) if medians are close.
- Keep secrets out of the repo. Configuration lives in `config/*.yaml` and `.env`.

## 2. Objective (replaces win rate)

The bot answers one question each week: "How much of this week's budget should I deploy?" It is judged against plain DCA with identical contributions.

### 2.1 Simulation
- Each week a budget `B` is added to cash.
- Strategy buys `amount_t = clip(m_t × B, 0, cash_t)` where the multiplier `m_t ∈ [0.25, 2.0]`. It is never 0, so the bot never fully stops buying.
- Unspent budget stays in a reserve (0% yield by default, configurable).
- Baseline DCA buys exactly `B` every week.
- Costs per buy: fee 0.10% + slippage 0.05% (configurable).

### 2.2 Metrics
Compute per split, per halving cycle, and over rolling windows (104-week windows starting every 4 weeks; report median and P10).
- **Primary: equity ratio** = (BTC_strat × P_T + cash_strat) / (BTC_dca × P_T + cash_dca) at the end of each window.
- **Cost-basis advantage (CBA)** = avg_cost_DCA / avg_cost_strategy − 1, on deployed USD.
- **Idle cash drag**: average reserve as % of total contributions, and the share of weeks with reserve > 3×B.
- Max drawdown of equity, time under water, Sortino, Calmar.
- Win rate at 1/3/6/12 months is kept as a **diagnostic only**, always shown with its episode count and confidence interval.

## 3. Data layer

Raw snapshots are immutable: `data/raw/<source>/<YYYY-MM-DD>.parquet`. Features are built into `data/features.parquet` with an `available_at` column per row.

Verify each endpoint, field name and licence before relying on it. If a series is unavailable, mark the feature `disabled` in config and continue; don't block the phase.

| Group | Series | Source | History | Publication lag |
|---|---|---|---|---|
| Price | Daily close, OHLCV | Coin Metrics community (`PriceUSD`), Binance klines for recent OHLCV and volume | ~2010+ | 1 day |
| Valuation | Market cap, MVRV (`CapMrktCurUSD`, `CapMVRVCur`); realized cap = market cap / MVRV if `CapRealUSD` isn't in the free tier | Coin Metrics community | ~2010+ | 1 day |
| Mining | Hash rate, issuance USD (`HashRate`, `IssTotUSD`) | Coin Metrics community | ~2010+ | 1 day |
| Sentiment | Fear & Greed | Alternative.me | 2018-02+ | 1 day |
| Derivatives | Funding rate BTCUSDT (`/fapi/v1/fundingRate`) | Binance USDⓈ-M | 2019-09+ | 0 (8h) |
| Derivatives | Open interest (`/futures/data/openInterestHist`) only keeps ~30 days | Binance | forward-collected | 0 |
| Derivatives | Quarterly futures basis vs spot | Binance delivery klines | 2020+ | 0 |
| Liquidity | Stablecoin total supply | DefiLlama stablecoins API | ~2018+ | 1 day |
| Flows | US spot BTC ETF daily net flows (optional, scraping is fragile) | public daily tables, e.g. Farside | 2024-01+ | 1 day |
| Macro | `DTWEXBGS` (broad USD), `DFII10` (10y real yield), `NASDAQCOM`, `M2SL` (monthly) | FRED (free API key) | long | 1 day; M2 ~30–45 days |
| Events | FOMC decision dates, CPI and PCE release dates, monthly options expiry (last Friday) | `config/events.yaml`, maintained by hand | — | known in advance |

Start a daily job immediately that records open interest and funding, because the history can't be downloaded later.

Data quality tests (run on every fetch): gaps, duplicate dates, non-monotonic dates, outliers (>5σ daily change flagged, not removed), staleness (>3 days old → fallback to DCA).

## 4. Features and decision model

### 4.1 Feature catalogue
Each feature is registered in `features/catalogue.py` with: name, group, formula, minimum history, `cheap_when` (low/high, the economic prior for a buyer), and normalization.

Normalization: point-in-time percentile rank over the trailing 208 weeks (4 years). Before 104 weeks of history exist, the feature is NaN and unused.

**Group A: cycle and valuation (long history, core model)**
| Feature | Formula | cheap_when |
|---|---|---|
| `mvrv` | market cap / realized cap | low |
| `mvrv_z` | (MC − RC) / std(MC, expanding) | low |
| `pi_ratio` | SMA111(P) / (2 × SMA350(P)) | low |
| `p_200wma` | P / SMA(P, 200 weeks) | low |
| `mayer` | P / SMA200d(P) | low |
| `puell` | IssTotUSD / SMA365(IssTotUSD) | low |
| `dd_ath` | P / running ATH − 1 | low (deeper drawdown) |
| `nupl` | 1 − 1 / MVRV | low |
| `halving_phase` | days since last halving / days in cycle, bucketed in quarters | no prior; max one cycle feature, low weight (only ~4 cycles exist) |
| `hash_ribbon_buy` | event: SMA30(hash rate) crosses back above SMA60 after ≥10 days below | event = cheap |

Halving dates: 2012-11-28, 2016-07-09, 2020-05-11, 2024-04-20.

**Group B: positioning and short-term (short history, overlay only)**
| Feature | Definition | cheap_when |
|---|---|---|
| `funding_7d` | 7-day mean funding rate | low / negative |
| `basis_ann` | annualized quarterly basis | low |
| `oi_to_mcap` | open interest / market cap (forward-collected) | low after a sharp drop |
| `stable_supply_30d` | 30-day % change in stablecoin supply | high = supportive |
| `etf_flow_5d` | 5-day sum of ETF net flows | high = supportive |
| `fng` | Fear & Greed | low (contrarian) |
| `rsi_14w`, `rsi_14d` | RSI | low |
| `vol_rel_20w` | weekly volume / 20-week mean | context |
| `capitulation` | weekly drop >10% with volume >2× the 20-week mean | event = cheap |

Note on `fng`: the current model learned a negative weight. On training data only, test the contrarian and momentum interpretations. Keep the one that is stable across folds and has an economic rationale. If neither is stable, drop the feature.

**Group C: macro and event risk (filters)**
- `usd_13w_chg`: 13-week change in `DTWEXBGS` (rising fast = risk-off).
- `real_yield_13w_chg`: 13-week change in `DFII10` (rising fast = risk-off).
- `nasdaq_above_200d`: flag.
- `m2_yoy`: lagged YoY change in `M2SL`.
- `event_window`: within 48 hours before a FOMC, CPI or PCE release, or a monthly options expiry.

### 4.2 Three-layer decision
`m_t = clip(m_A × f_B × f_C, 0.25, 2.0)`

**Layer A: core multiplier (Group A only, trained on 2011+)**
- Targets: forward 26-week and 52-week log return; also the binary "forward return > 0" for diagnostics.
- Try models in this order and stop at the simplest one that passes section 5:
  1. Equal-weight composite of sign-adjusted percentiles.
  2. Ridge or L2-logistic regression with sign constraints matching `cheap_when` (bounded optimization). Drop any feature whose sign flips across folds.
  3. Monotonic gradient boosting (LightGBM `monotone_constraints`), only if 1 and 2 fail and it beats them out of sample.
- Maximum 4 features in the final core model. If two features have |ρ| > 0.8, keep one.
- Map `score_A ∈ [0, 1]` to `m_A` with a monotone step table, tuned on train/validation only. Starting point, aligned with the current buckets:
  - score ≥ 0.80 (Phải mua) → 2.0
  - 0.60–0.80 (Cân nhắc mua) → 1.25
  - 0.40–0.60 → 0.75
  - < 0.40 (Không nên mua) → 0.25

**Layer B: timing overlay (Group B)**
- `f_B ∈ [0.75, 1.25]`. Because history is short, the effect is capped.
- If a rule has fewer than 10 independent episodes in the data, force `f_B = 1.0` for that rule.
- Add one feature at a time. Keep it only if ablation shows a better P10 equity ratio without lowering the median by more than 1%.

**Layer C: risk overlay (Group C)**
- `event_window`: delay the buy to the first day after the event. Never cancel it.
- Candidate rule (keep only if it passes ablation): if USD and real yields both rise fast and Nasdaq is below its 200-day average, cap `m_t` at 1.25.

**Reserve rules**
- Reserve is used only when `m_t > 1`.
- If reserve exceeds 12×B, force `m_t ≥ 1.0` so cash isn't hoarded indefinitely.

### 4.3 Sell side (conservative)
- Keep existing criteria. Any criterion with fewer than 10 independent episodes is "display only": shown in the report, never triggers an action.
- Action rule: sell 10% of BTC when ≥2 independent groups trigger (valuation plus positioning or momentum), 30% when ≥3. Never sell more than 50% within any 26 weeks. Rebuying happens through the buy layer.
- Compare against hold with the same metrics. If selling doesn't improve P10 equity ratio and max drawdown in at least 3 of 4 cycles, the sell side remains advisory text only.

## 5. Validation protocol

- **Splits:** train 2011-01-01 → 2019-12-31; validation 2020-01-01 → 2022-12-31; final holdout 2023-01-01 → latest (locked).
- Group B and C features only exist for part of this range. Evaluate them with walk-forward inside their available data and flag this clearly in results.
- **Walk-forward:** expanding window, refit every 13 weeks. Purge training samples whose label window overlaps the test window. Embargo = label horizon (26 or 52 weeks).
- **Independent episodes:** consecutive weeks in the same bucket count as one episode. Always report episodes, not only weeks.
- **Uncertainty:** block bootstrap with 26-week blocks, 2,000 resamples, 95% CIs for equity ratio and CBA.
- **Placebo test:** shuffle the multiplier series in 26-week blocks (1,000 runs). Report the real strategy's percentile; it must beat at least 95% of placebos.
- **Multiple testing:** report the number of trials from the registry and compute the Deflated Sharpe Ratio (Bailey & López de Prado) for the final candidate.
- **Cycle breakdown** (halving-aligned): pre-2012-11-28, 2012-11-28 → 2016-07-09, 2016-07-09 → 2020-05-11, 2020-05-11 → 2024-04-20, 2024-04-20 → now.
- **Reproduce the current bot** as a multiplier strategy (Phải mua → 2.0, Cân nhắc mua → 1.25, Không nên mua → 0.25) to measure its true equity ratio vs DCA. This is the benchmark every new candidate must beat.

### Acceptance criteria (all must hold to ship)
1. Median rolling equity ratio vs DCA > 1.00 in validation and in holdout, and P10 ≥ 0.97.
2. Equity ratio > 1.00 in at least 3 of 4 full halving cycles.
3. Max drawdown no worse than DCA by more than 5 percentage points.
4. Beats at least 95% of placebo runs.
5. Average idle cash ≤ 25% of contributions.
6. Every active rule has ≥10 independent episodes; otherwise it is display only.
7. Better than the reproduced current bot on criteria 1 and 2.
8. All tests pass and the regression diff of the report has been reviewed.

If the new model fails, keep the current bot and document why. A failed upgrade is an acceptable outcome; a misleading one is not.

## 6. Vietnamese language, theme and report

### 6.1 Language
- Default and only required locale: `vi`. Set in config as `ui.language: vi`.
- Vietnamese applies to everything a user sees: the report, any web UI or dashboard (labels, buttons, tooltips, empty states), chart titles, axes and legends, notifications (Telegram, email or similar if the bot has them), warnings, fallback and error messages, and CLI output meant for the user.
- Logs, code, identifiers, code comments and tests may stay in English.
- Put every user-facing string in `bot/i18n/vi.yaml` and read it through a helper, e.g. `t("buy.score_label")`. No hard-coded user-facing strings in code or templates. Structure it so another language could be added later, but only build `vi` now.
- Use UTF-8 everywhere. If the bot renders images, charts or PDFs, use a font that has full Vietnamese diacritics (for example Be Vietnam Pro or Noto Sans) and check that text like "Cân nhắc mua", "Sụt giảm", "Tỷ lệ nên bán" renders correctly.
- Write natural Vietnamese, as in the current report. Don't translate word by word from English.

### 6.2 Number, money and date format (vi-VN)
Put these in `bot/i18n/fmt.py` and use them everywhere:
| Type | Format | Example |
|---|---|---|
| USD price | thousands with ".", symbol after | `80.754 $` |
| Decimal | comma | `0,49`, `1,37` |
| Percent | no space | `79%`, `-5%`, `+19%` |
| Date | dd/mm/yyyy | `28/10/2026` |
| Date and time | HH:mm dd/mm/yyyy, Vietnam time (Asia/Ho_Chi_Minh, UTC+7) | `01:00 29/10/2026` |
| BTC amount | 4–8 decimals with comma | `0,0248 BTC` |

Store event times in `events.yaml` in UTC and display them converted to Vietnam time.

### 6.3 Glossary (keep terms consistent)
Existing terms stay exactly as they are now: Tỷ lệ nên mua, Tỷ lệ nên bán, Phải mua, Cân nhắc mua, Không nên mua, Nên bán, Cân nhắc bán, Không nên bán, Giữ, Chốt lời, Mốc, Khoảng tin cậy, Trung vị, Số đợt.

New terms:
| English (code) | Vietnamese (UI) |
|---|---|
| multiplier | Hệ số mua |
| weekly budget | Ngân sách tuần |
| DCA baseline | Mua đều (DCA) |
| equity ratio | Tỷ số tài sản so với mua đều |
| cost-basis advantage (CBA) | Lợi thế giá vốn |
| reserve | Quỹ dự trữ |
| idle cash | Tiền mặt chờ |
| max drawdown | Sụt giảm lớn nhất |
| P10 | Kịch bản xấu (10% tệ nhất) |
| independent episode | Đợt độc lập |
| low evidence | Ít bằng chứng |
| holdout | Giai đoạn kiểm tra cuối |
| placebo test | Kiểm tra với tín hiệu ngẫu nhiên |
| fallback to DCA | Chế độ an toàn: mua đều |
| event window | Sát ngày sự kiện vĩ mô |
| layer A / B / C | Lớp chu kỳ / Lớp ngắn hạn / Lớp vĩ mô |

### 6.4 Theme (keep the current look)
- In Phase 0, document the current theme in `docs/AUDIT.md`: colors, fonts, spacing, table style, bold and emoji usage, section order, and the file or component where each is defined.
- Don't change any of it. New sections and charts reuse the same styles, components and table formats as the existing ones.
- Add a snapshot test of the rendered report (and of the UI, if there is one) on a fixed data snapshot, so any visual change shows up as a diff for me to approve.

### 6.5 New report section
Add a section **"Khuyến nghị giải ngân tuần này"** containing:
- Hệ số mua `m_t`, số tiền đề xuất theo ngân sách tuần `B` trong config, và lớp nào quyết định (A, B hay C).
- Mức bằng chứng: số đợt độc lập, khoảng tin cậy 95%, cờ "ít bằng chứng" khi dưới 10 đợt.
- So sánh với DCA (backtest): equity ratio trung vị và P10, CBA, sụt giảm lớn nhất.
- Sự kiện vĩ mô trong 7 ngày tới (từ `events.yaml`) và lệnh có bị hoãn không.
- Độ mới của dữ liệu. Nếu fallback: "Dữ liệu thiếu hoặc cũ → mua đều như DCA (hệ số 1,0)".

In the indicator-set ranking, mark with ⚠ any set that has fewer than 10 episodes or whose result differs by more than 20 percentage points between the two halves.

## 7. Engineering

```
bot/
  data/        fetchers per source, pit_store.py, quality.py
  features/    catalogue.py, normalize.py
  models/      core.py (layer A), overlays.py (B, C), sell.py
  backtest/    engine.py, metrics.py, baselines.py (DCA, current bot)
  validation/  splits.py, bootstrap.py, placebo.py, registry.py, dsr.py
  report/      vi_report.py (uses the existing theme and templates)
  i18n/        vi.yaml (all user-facing strings), fmt.py (vi-VN formats)
config/        bot.yaml, events.yaml
experiments/   registry.csv
docs/          AUDIT.md, RESULTS.md
tests/
```

- Python 3.11+, pandas, numpy, scipy, scikit-learn; LightGBM optional.
- Type hints and docstrings. `pytest` with small cached fixtures; no network calls in tests.
- Deterministic seeds. Provide `make test`, `make backtest`, `make report`.

Example `config/bot.yaml`:
```yaml
budget:
  weekly_usd: 100
  multiplier_min: 0.25
  multiplier_max: 2.0
  reserve_cap_weeks: 12
costs:
  fee: 0.001
  slippage: 0.0005
splits:
  train: [2011-01-01, 2019-12-31]
  validation: [2020-01-01, 2022-12-31]
  holdout: [2023-01-01, null]   # locked, --final only
validation:
  refit_every_weeks: 13
  embargo_weeks: 26
  bootstrap_block_weeks: 26
  bootstrap_n: 2000
  placebo_n: 1000
  min_episodes: 10
  rolling_window_weeks: 104
ui:
  language: vi
  timezone: Asia/Ho_Chi_Minh
  keep_theme: true      # never change existing styles
risk:
  advisory_only: true
  stale_data_days: 3
  event_delay: true
features:
  disabled: []   # filled when a source is unavailable
```

## 8. Phases (stop after each one)

| Phase | Work | Deliverable |
|---|---|---|
| 0. Audit | Map the repo, the data flow, and the current website hosting and deploy setup (10.1); explain how every report number is computed; list look-ahead risks, overlapping-label sample inflation, and how the "best set" is chosen. Document the current theme (6.4) and list every user-facing string and where it is hard-coded. Add regression and snapshot tests that freeze current report output and look on a fixed data snapshot. No behavior change. | `docs/AUDIT.md` (Vietnamese), tests |
| 1. Data | Point-in-time store, new fetchers with 2010+ history, quality tests, daily forward recording of OI and funding. | fetchers, tests |
| 2. Backtest | DCA baseline, multiplier strategy, costs, all metrics, rolling windows. Reproduce the current bot as a multiplier strategy and report its real equity ratio vs DCA. | engine, first benchmark table |
| 3. Validation | Splits, purge/embargo, bootstrap, placebo, registry, Deflated Sharpe Ratio. | toolkit, tests |
| 4. Core layer A | Rebuild on 2011+ data, ablation table, comparison with the current bot. | model, ablation report |
| 5. Overlays | Add layers B and C one feature or rule at a time; keep only what passes ablation. | ablation report |
| 6. Sell side | Evaluate take-profit rules vs hold. | report |
| 7. Final holdout | One run with `--final`. Document all acceptance criteria, trial count, CIs and failures. | `docs/RESULTS.md` (Vietnamese) |
| 8. Ship | Move all user-facing strings to `vi.yaml`, apply vi-VN formats, add the new report section, fail-safes. Snapshot tests must show the theme unchanged; only the new section is a new diff. | updated Vietnamese report |
| 9. Deploy | GitHub Actions (CI, daily run, data commits), website settings, source checks from the runner, safe release with rollback (section 10). | live site, `docs/DEPLOY.md` (Vietnamese), list of GitHub settings I must change by hand |

At the end of every phase, append to `docs/PROGRESS.md` (in Vietnamese): a short summary, files changed, test results, a key-metrics table, and open questions. Then continue or stop according to section 11.

## 9. Don'ts

- Don't tune thresholds on the holdout, or after having seen holdout results.
- Don't count overlapping weekly labels as independent samples.
- Don't keep a feature because it "makes sense"; it must pass ablation.
- Don't report any win rate without its episode count and confidence interval.
- Don't silently skip data errors; fall back to DCA and say so in the report.
- Don't connect trading or withdrawal APIs, and don't add leverage.
- Don't hard-code user-facing text, show English to the user, or use English number formats (`80,754.00`) in the UI.
- Don't change the theme, colors, fonts or layout without my explicit approval.
- Don't commit secrets, and don't publish my personal budget, holdings or wallet addresses on the website.
- Don't let one blocked or broken data source take the whole website down.

## 10. GitHub and website deployment

### 10.1 Detect the current setup (Phase 0)
- Find how the website is built and hosted today: `.github/workflows/`, a `gh-pages` branch, `CNAME`, a `docs/` Pages source, `netlify.toml`, `vercel.json`, or a static site generator config. Record it in `docs/AUDIT.md`.
- Keep the current host, URL and custom domain. Only if there is no automated deploy, use GitHub Pages with GitHub Actions as described below.
- The site reuses the existing templates and CSS (theme rule 6.4). The built site must pass the snapshot tests.

### 10.2 Website settings
- `<html lang="vi">`, `<meta charset="utf-8">`, and a mobile viewport meta tag.
- Title "Báo cáo bot BTC" and a Vietnamese meta description.
- At the top of the page: "Cập nhật lúc HH:mm dd/mm/yyyy (giờ Việt Nam)" and data freshness per source.
- If it is a GitHub Pages project site (`https://<user>.github.io/<repo>/`), use relative links or a `site.base_url` from config so assets and links work under `/<repo>/`.
- Wide tables scroll horizontally inside their own container on phones, without changing the look.
- If data is stale or a fallback happened, show a banner: "⚠ Dữ liệu chưa cập nhật, đang hiển thị báo cáo gần nhất" (or the specific fallback message).
- **Privacy:** treat the site as public. Show the multiplier and the amount per 100 $ of budget ("trên mỗi 100 $ ngân sách"), not my personal budget or holdings. Personal settings live in `config/personal.yaml`, which is git-ignored and only used for local output. Note: GitHub Pages for a private repo needs a paid GitHub plan, and on most plans the published site is still public.

Add to `config/bot.yaml`:
```yaml
site:
  title: "Báo cáo bot BTC"
  base_url: ""          # e.g. "/<repo>" for a project Pages site
  show_personal_budget: false
  amount_example_usd: 100
```

### 10.3 Workflows (`.github/workflows/`)
- `ci.yml`: on `push` and `pull_request`. Install dependencies, run `make test` (unit, regression and snapshot tests, no network).
- `daily.yml`: on `schedule` with `cron: "0 1 * * *"` (01:00 UTC = 08:00 Vietnam time, after the daily and the Monday weekly candle close at 00:00 UTC), plus `workflow_dispatch` for manual runs. Steps: checkout → set up Python with pip cache → fetch data → quality checks → build features → generate report → build site → run tests → commit new data → deploy.
- Deploy with the official Pages actions (`actions/configure-pages`, `actions/upload-pages-artifact`, `actions/deploy-pages`) using `permissions: pages: write, id-token: write` on the deploy job and `contents: write` only on the data-commit job. Pin every action to its current stable major version, preferably by commit SHA.
- Add `concurrency: { group: btc-bot, cancel-in-progress: false }` so two runs never overlap.
- Cron runs in UTC. Use `Asia/Ho_Chi_Minh` only for formatting displayed times.
- Known GitHub behavior: scheduled runs can start late at busy times, and in public repos scheduled workflows are disabled after 60 days without repository activity. The daily data commit to the default branch keeps the repo active.

### 10.4 Data persistence
- Commit raw snapshots and forward-collected series (open interest, funding) under `data/` from the workflow, as `github-actions[bot]`, with a message like `data: cập nhật 28/10/2026`.
- Never commit data that failed quality checks.
- Keep files small (compressed parquet). If `data/` grows past ~100 MB, move old snapshots to release assets.

### 10.5 Network access from GitHub runners
- GitHub-hosted runners are in US data centers, and Binance's main APIs (`api.binance.com`, `fapi.binance.com`) often return HTTP 451 or 403 from there. In the first run, test every data source from the runner and log the status of each in `docs/DEPLOY.md`.
- If Binance is blocked: take spot price and volume from Coin Metrics or CoinGecko (or `data-api.binance.vision` for spot market data, if reachable). For funding and basis, try another public source, run the data job on a self-hosted runner (my own computer or a VPS in Vietnam), or mark those features `disabled`.
- One failed source must never fail the whole run: use the fallback, show the banner, and still publish the last good report.

### 10.6 Secrets
- `FRED_API_KEY` is stored as a GitHub Actions secret and read from the environment. No exchange API keys exist anywhere.
- `.gitignore` includes `.env`, local caches and `config/personal.yaml`.

### 10.7 Safe release and rollback
- Before the first deploy, tag the current production version as `v1-before-upgrade`.
- Do the upgrade on a branch (e.g. `upgrade/best-roi`). Before merging, run the build on the branch and give me the built site as a downloadable workflow artifact to check.
- Deploy only from `main`, and only when CI is green.
- Rollback: revert the merge commit on `main`, or redeploy from the `v1-before-upgrade` tag. Write both procedures in `docs/DEPLOY.md`.

## 11. Run mode (one prompt)

**Before any change**
- If the repo has uncommitted changes, stop and ask me what to do with them.
- Tag the current version `v1-before-upgrade`, then create and work on the branch `upgrade/best-roi`.

**While running**
- Run Phases 0 to 9 in order without waiting for approval between phases.
- After each phase, commit on the upgrade branch (`phase N: ...`) and append the Vietnamese phase summary to `docs/PROGRESS.md`.
- If the session ends or is interrupted, read `docs/PROGRESS.md` when I say "Tiếp tục", and continue from the first unfinished phase.

**Stop and ask me only when**
1. A test fails and the fix would change the bot's current behavior or theme.
2. The new model fails the acceptance criteria in section 5. In that case, report why, keep the current bot's logic, and only ship the safe parts (Vietnamese language, formats, fail-safes, deploy). Don't ship the new model.
3. You need a secret, an account, or a paid service.
4. The site is built on the upgrade branch (Phase 9). Give me the artifact, the list of GitHub settings I must change by hand, and a short Vietnamese summary of results, then wait for me to say **"OK deploy"**.

**Never** push to `main`, merge, or deploy anything live before I say "OK deploy".
