# Ross Cameron (Warrior Trading): Trading Strategy & Edge — Research Report

> **Research date:** 2026-07-09 · **Method:** multi-angle web research (5 search angles, 15+ sources), claims
> labeled by source class. Strategy mechanics are drawn from Warrior Trading's own published materials
> (authoritative for *what he teaches*); performance claims are labeled self-reported vs. independently
> documented. This document describes a strategy for research purposes — it is not financial advice, and the
> regulatory record below (FTC v. Warrior Trading) is essential context for any replication attempt.

---

## TL;DR

Ross Cameron is a small-cap **momentum day trader** and founder of Warrior Trading, one of the largest
day-trading education businesses. His strategy is narrow and mechanical: **long-biased momentum scalping of
low-float small-cap stocks ($1–$20) that are already up 10%+ on the day on 5x+ relative volume with a news
catalyst**, traded almost entirely in the first 30–90 minutes of the session using 1-minute/5-minute charts,
Level 2/tape reading, and hotkeys. His claimed edge is not a high win rate on big moves but **asymmetric
expectancy at high frequency**: ~70% win rate with winners ~2–4x the size of losers, produced by tight stops,
selling into strength, and compounding hundreds of small "base hits."

His track record is unusually well-documented for a retail trader — he grew a **$583.15 account (Jan 2017) past
$1M (May 2019) and past $10M (2022)**, with brokerage statements audited by third-party accounting firms — but
the **FTC sued Warrior Trading and Cameron in April 2022** for deceptive earnings claims, resulting in a **$3M
settlement**, and found that *the vast majority of Warrior Trading customers lost money*. The honest synthesis:
the strategy's edge appears real but small-capacity, execution-intensive, and — on the FTC's evidence — **not
replicable by the typical student**.

---

## 1. Who he is, and what is actually verified

| Claim | Status |
|---|---|
| Founder/CEO of Warrior Trading (Great Barrington, MA); day trades small caps live on YouTube/streams daily | Well documented |
| Started the "small account challenge" with **$583.15 on Jan 1, 2017** | Self-reported, consistent across sources |
| Crossed **$100k in ~45 days**; crossed **$1M in May 2019** | Self-reported; brokerage statements for the challenge period audited by **Citrin Cooperman** |
| Cumulative trading profits **>$10M (crossed 2022, account still growing)** | Self-reported; audited by **SingerLewak** "according to AICPA standards" per Warrior Trading |
| Author of *How to Day Trade: The Plain Truth* (2023) | Published |
| FTC sued him and Warrior Trading; **$3M settlement (2022)** | **Independently verified — FTC primary documents** |

Two things can be true at once, and here they are:

1. **The audits are meaningful.** Publishing accountant-audited brokerage statements is far beyond what almost
   any trading educator does. The audit evidence supports that *Cameron himself* genuinely produced these
   profits trading real money ([Warrior Trading: verified earnings](https://www.warriortrading.com/ross-camerons-verified-day-trading-earnings/),
   [challenge page](https://www.warriortrading.com/583-to-1mil/),
   [Entrepreneur essay](https://www.entrepreneur.com/money-finance/how-i-turned-583-into-10-million-by-day-trading/456246)).
2. **The audits verify his account, not the strategy's transferability.** The FTC complaint established that
   during 2018–2021 the *vast majority of customer accounts lost money*
   ([FTC press release, Apr 2022](https://www.ftc.gov/news-events/news/press-releases/2022/04/federal-trade-commission-cracks-down-warrior-trading-misleading-consumers-false-investment-promises)).

Caveat on the challenge framing: the $583→$10M arc includes account top-ups being replaced by profits and, more
importantly, reflects a professional with years of prior experience restarting small — not a beginner's
expected path. Warrior Trading itself now carries "results not typical" disclosures.

---

## 2. The niche: what he trades and when

- **Instrument:** U.S. small-cap / micro-cap common stocks, long side almost exclusively. He is a *buyer of
  momentum*, not a short seller.
- **Price range:** roughly **$1.00–$20.00** — cheap enough for retail-sized accounts to take meaningful share
  size, above the sub-$1 penny-stock zone he treats as untradeable
  ([Warrior Trading — Stock Selection PDF](https://cdn.warriortrading.com/warriortrading.com/assets/Warrior%20Trading%20-%20Stock%20Selection.pdf)).
- **Time window:** pre-market scanning from ~7:00–9:30am ET; the bulk of trading between **9:30 and 10:00–11:30am
  ET**. Gap-and-Go profits "are usually realized between 9:30 and 10:00" ([Gap and Go](https://www.warriortrading.com/gap-go/)).
  He deliberately avoids the midday chop and afternoons, especially when rebuilding after losses.
- **Holding period:** minutes. In analyzed recap periods his average winners lasted ~4 minutes and losers ~7–14
  minutes ([Traders Union profile](https://tradersunion.com/persons/ross-cameron/), Warrior Trading recaps).
- **Style:** momentum scalping on 1-min and 5-min charts (occasionally a 10-second chart for timing), riding the
  "**front side**" of a move and being flat before the inevitable fade.

---

## 3. Stock selection: the Five Pillars

The heart of the system is a scan-driven checklist. A stock must satisfy essentially **all five** criteria to be
tradeable ([Stock Selection PDF](https://cdn.warriortrading.com/warriortrading.com/assets/Warrior%20Trading%20-%20Stock%20Selection.pdf),
[TradingView "5 Pillars" community indicator](https://www.tradingview.com/script/mbqMf3pF-Ross-Cameron-5-Pillars-Filter/)):

| # | Pillar | Threshold he teaches | Rationale |
|---|---|---|---|
| 1 | **Relative volume** | **≥ 5x** the ~30-day average daily volume (his momentum-strategy article allows ≥2x as a floor) | Proof that today is abnormal; liquidity to get in *and out* |
| 2 | **Already up on the day** | **≥ +10%** change vs. prior close | He only trades stocks *already moving* — demand is proven, not predicted |
| 3 | **News catalyst** | Headline that justifies the move (earnings, FDA, contract, PR) | Gaps/squeezes without news are treated as higher-risk and prone to sudden reversal |
| 4 | **Price** | **$1.00 – $20.00** | Popular with small retail accounts → crowd participation; sub-$1 excluded as too risky |
| 5 | **Float** | **Low float — under ~10–20M shares ideal**; up to ~50–100M acceptable for momentum names | Scarce supply + surging demand = the 50–100%+ intraday moves the strategy needs. Large floats rarely move >10% intraday |

(The float threshold is stated with different cutoffs across his materials — <10M in the "5 Pillars" framing,
<20M "preferred" in the Stock Selection doc, <100M with <20M "ideal" in the
[momentum strategy article](https://www.warriortrading.com/momentum-day-trading-strategy/). The constant is:
the lower the float, the better.)

**Key insight:** this is a *statistical pre-filter*, not a prediction. Cameron's claim is that virtually all of
his profits come from the tiny subset of stocks that pass this scan on a given day — usually just a handful —
and that most losing traders fail simply because they trade stocks outside this profile (no volume, no
catalyst, heavy float) where no outsized move is structurally possible.

---

## 4. The daily workflow

1. **Pre-market gap scan (~7:00–9:15am ET):** run a "Top Gappers" scanner for stocks gapping **>4%** vs. prior
   close ([Gap and Go](https://www.warriortrading.com/gap-go/)). His own tooling (Day Trade Dash; historically
   Trade Ideas–style scanners) is configured around the five pillars.
2. **Catalyst check:** for each gapper, find the news. No headline → discard or downgrade.
3. **Build a short watchlist** (typically 2–5 names) and mark **pre-market highs**, pre-market flag levels, and
   prior resistance.
4. **At the open (9:30):** trade the watchlist with the setups below, most aggressively in the first 30 minutes.
5. **Intraday re-scanning:** high-of-day (HOD) momentum scanners surface new names breaking out during the
   morning ([third-party replication of his scans](https://github.com/Jayanth7416/ross-cameron-stock-scanner)).
6. **Recap and journal:** every trade logged; daily recaps published — the source of his self-reported stats.

---

## 5. The setups

All setups are variations of one theme: **buy a brief pause inside a strong uptrend, risk the low of the pause,
sell into the next burst of strength.**

### 5.1 Gap and Go (the opening play)
- Universe: 4%+ pre-market gappers with news, passing the pillars.
- Entry (either): **break of pre-market high**, or the **1-minute opening-range breakout** — buy the first
  1-minute candle's high with a stop at that candle's low; enter on a pullback/consolidation near pre-market
  highs when possible ([Gap and Go](https://www.warriortrading.com/gap-go/),
  [terminology page](https://www.warriortrading.com/gap-and-go-definition-day-trading-terminology/)).
- Confirmation: **volume surging in on the breakout**; most profits banked before 10:00am.

### 5.2 Bull flag / momentum pullback (the bread-and-butter)
- Context: stock in a strong markup on the 1-min/5-min chart.
- Pattern: a pullback of **2–3 red candles** (the flag) after a strong pole.
- Entry: **the first candle to make a new high** after the pullback.
- Stop: **the low of the pullback**.
- Target discipline: minimum **2:1** reward-to-risk ([momentum day trading strategy](https://www.warriortrading.com/momentum-day-trading-strategy/)).

### 5.3 Micro pullback (the scalper's refinement)
- A compressed bull flag: just a **1–3 candle pause** (often a single red or doji candle) very early in a
  breakout on the 1-minute chart, before any extended run.
- Works best on liquid stocks **under ~$10** during strong breakouts.
- Entry as price reclaims the pause high; stop **just under the pullback low** — risk is only a few cents,
  allowing **larger share size** for the same dollar risk
  ([micro pullback strategy](https://www.warriortrading.com/pull-back-trading-strategy/)).
- His filter question: *"Is this setup tight, clean, and high-conviction? If not, skip it."*

### 5.4 Flat-top breakout
- Horizontal resistance tested repeatedly while higher lows compress underneath; buy the break of the flat top,
  stop under the consolidation. Listed alongside bull flags as the two entry-qualifying "momentum chart
  patterns" ([momentum day trading strategy](https://www.warriortrading.com/momentum-day-trading-strategy/)).

### 5.5 High-of-day break
- Continuation entry when a qualifying stock reclaims/breaks its intraday high, often flagged by HOD scanners.

---

## 6. Execution mechanics

- **Level 2 + Time & Sales (tape reading):** locate large bids/offers, judge whether buyers are aggressive
  (lifting the offer) before committing; used to time entries around key levels and to detect when a big seller
  caps the move ([tape reading](https://www.warriortrading.com/what-is-tape-reading-in-trading/)).
- **Hotkeys:** pre-configured buy/sell/stop hotkeys (Lightspeed / Sterling-compatible platforms) so entries and
  exits execute in fractions of a second — treated as non-negotiable for this style
  ([tools FAQ](https://support.warriortrading.com/support/solutions/articles/19000080962-what-software-and-trading-tools-do-you-use-and-recommend-for-when-i-trade-live-)).
- **Scaling out, not all-out:** standard exit is to **sell half at the first target** (e.g. +20¢ on 20¢ risk),
  move the stop to breakeven on the remainder, and trail for the "home run" leg
  ([momentum day trading strategy](https://www.warriortrading.com/momentum-day-trading-strategy/)).
- **Adding through breakouts:** on strong tape he re-adds size as new consolidations break, compounding a
  winner rather than holding a static position.
- **Broker/platform:** Lightspeed Trader historically; his own Day Trade Dash suite for scanning/charts/news.

---

## 7. Risk management (the part he calls the actual edge)

- **2:1 minimum profit-to-loss ratio** on every planned trade: risk $0.20/share to target $0.40+; risk $100 to
  make $200 ([momentum day trading strategy](https://www.warriortrading.com/momentum-day-trading-strategy/)).
- **Stops at structure, not round numbers:** low of the pullback / low of the first candle / under the
  consolidation — always defined *before* entry.
- **Daily max loss:** a hard daily stop-out level ("max loss red day"). After hitting it, the account gets
  defensive: max loss cut to **½ or ¼ of normal**, share-size caps, sometimes **one trade per day** until
  consistency returns ([bounce-back writeup](https://www.warriortrading.com/how-i-bounced-back-after-my-max-loss-red-day/)).
- **"Trader Rehab":** his named protocol for losing streaks — size down hard, take only A+ setups, stop while
  green in the morning, no afternoon trading, rebuild the cushion before restoring size.
- **Cushion-based sizing:** trade small until the day is green, then press with "house money"; the daily goal
  in his teaching era was modest (e.g. ~$2k/day) relative to his best days — consistency over home runs.
- **Behavioral rules:** "Go slow." "You don't try to make big moves when the weather is bad — you batten down
  the hatches and focus on surviving."

---

## 8. The edge, quantified — and where it actually comes from

### His self-reported numbers (from published recaps/metrics; not independently audited per-metric)

| Metric | Value |
|---|---|
| Win rate ("accuracy") | **~68–72%** |
| Average winner vs. average loser (example analyzed period) | **~$500 vs. ~$114 (≈4.4:1)**; he targets ≥2:1 |
| Typical hold time | Winners ~4 min; losers ~7–14 min |
| Cumulative profits | **>$10M** (audited brokerage statements, per §1) |
| Account low point | Started challenge with $583.15; he has said the strategy stops scaling smoothly in the millions-per-year range because of small-cap liquidity |

With a ~70% win rate *and* winners 2–4x losers, expectancy per trade is strongly positive; the strategy then
relies on **frequency** (many trades per morning) and **compounding**. Note the one behavioral wart visible in
his own stats: losers are held *longer* than winners — even for him, cutting losses is the hard part.

### The structural sources of the edge

1. **A repeatable supply/demand anomaly.** Low float + retail-magnet price + catalyst + 5x volume creates
   short-lived, self-reinforcing demand imbalances (FOMO buyers, short squeezes, slippage-driven spikes). The
   scan finds the only stocks where 20–100% intraday moves are *mechanically possible*.
2. **Selection discipline as edge.** He trades ~2–5 qualifying names a day and skips everything else. Most of
   the "edge" is refusing to trade where the anomaly isn't present.
3. **Asymmetric bet structure.** Structure-based stops a few cents below entry vs. targets 2x+ away, sized so
   any single loss is trivial vs. the daily P&L.
4. **Execution speed.** Hotkeys + tape reading capture moves measured in seconds-to-minutes that slower
   participants cannot.
5. **Capacity constraint = protection.** The niche is too small for institutions: you cannot deploy $50M into
   a 10M-float $5 stock. This is why the edge persists — and also why it **cannot scale** past a certain
   personal-account size (the very "scalable" claim the FTC challenged).
6. **Regime dependence.** The strategy feeds on hot-money markets (2020–2021 being the extreme). In cold tapes
   the number of qualifying stocks per day approaches zero — his own guidance is to trade less, not to force it.

---

## 8b. What annual rate of return does this imply?

Short version: **the strategy does not have a scale-invariant annual return.** It produces a roughly fixed
*dollar* edge (expectancy per trade × trades per day), so percentage return collapses as capital grows. Any
single "X% per year" number is meaningless without an account size attached.

### His realized numbers (from the audited cumulative figures)

| Window | From → To | Multiple | Implied annualized return |
|---|---|---|---|
| Calendar 2017 | $583.15 → ~$335,000 | ×574 | **≈ +57,000% (year one)** |
| Jan 2017 → May 2019 ($1M mark) | $583.15 → $1.0M | ×1,715 (~2.4 yrs) | ≈ ×22–23/yr ≈ **+2,100%/yr** |
| Jan 2017 → Dec 2025 (full record) | $583.15 → $18,810,638 cumulative | ×32,257 (9 yrs) | ≈ ×3.17/yr ≈ **+217%/yr CAGR** |

Cumulative audited profits: **$10.73M through Dec 2023**, **$18.81M through Dec 2025**
([verified earnings](https://www.warriortrading.com/ross-camerons-verified-day-trading-earnings/),
[2024](https://www.warriortrading.com/verified-earnings-2024/) / [2025 statements](https://www.warriortrading.com/verified-earnings-2025/),
[net-worth analysis](https://www.financialtechwiz.com/post/ross-cameron-net-worth/)). These "CAGR" figures are
stylized — in practice profits are withdrawn rather than fully compounded, which is exactly the point: the
stable quantity is **dollar income, not percentage return**. In dollar terms his record reads: ~$335k (2017),
~$1.7M/yr average 2018–2023, ~$4M/yr average 2024–2025 (hot momentum tape).

### Why percentage return falls as the account grows

The strategy's capacity ceiling (low-float small caps tolerate only low-six-figure position sizes before the
order *is* the move) means the same skill that returned +57,000% on $583 produces low-hundreds-of-percent on
low-seven-figure working capital, and would produce near-index-like returns on institutional size — which is
why no fund runs this and why the edge persists for individuals.

### The honest "predicted" return, by scenario

- **A random person adopting the strategy (unconditional expectation): negative.** Per the FTC complaint, the
  vast majority of Warrior Trading customer accounts lost money; academic base rates put sustained day-trading
  profitability at ~1–3% of participants. The median outcome is loss of most risk capital plus course costs.
- **Conditioned on being one of the few skilled, disciplined executors on small capital (<$100k):** the
  strategy's own arithmetic (~70% win rate, ≥2:1 reward/risk, tight dollar risk, many trades/day) supports
  high-double-digit to low-triple-digit percent annual returns, degrading with account size. Cameron's ×574
  first year is the extreme right tail of the right tail — the reason he is famous, not the expectation.
- **As a fund-style scalable strategy: not applicable.** The FTC specifically challenged the "scalable" claim;
  the capacity ceiling is structural.

Benchmark for calibration: the S&P 500's long-run total return is ~10%/yr. Warrior Trading is now legally
prohibited from making unsubstantiated earnings-potential claims, and its own disclosures state results are
not typical.

## 9. Criticisms, controversies, and the replicability question

> Deep dive: the mechanisms behind "the vast majority of customers lost money" — behavioral biases, the cost
> stack, dilution dynamics, and the replication gap — are documented with sources in the companion report
> [`why-retail-traders-lose.md`](./why-retail-traders-lose.md).

### The FTC case (the central controversy)

- **April 2022:** the FTC sued Warrior Trading and Ross Cameron, alleging deceptive earnings claims in
  violation of the FTC Act and the Telemarketing Sales Rule. Marketing from **January 2018 to March 2021**
  showcased Cameron's results as "profitable" and "scalable" while, per the complaint, **"the vast majority of
  customer accounts actually lost money"** — many customers losing thousands trading on top of thousands paid
  for courses ([FTC press release](https://www.ftc.gov/news-events/news/press-releases/2022/04/federal-trade-commission-cracks-down-warrior-trading-misleading-consumers-false-investment-promises),
  [complaint PDF](https://www.ftc.gov/system/files/ftc_gov/pdf/2023198WarriorTradingComplaint_0.pdf)).
- **Settlement:** **$3M** to refund consumers + a prohibition on unsubstantiated earnings claims
  ([case page](https://www.ftc.gov/legal-library/browse/cases-proceedings/2023198-warrior-trading-inc-ftc-v)).
- **January 2023:** FTC mailed **$2.9M in refunds to 20,402 customers** (~$142 average)
  ([FTC refunds release](https://www.ftc.gov/news-events/news/press-releases/2023/01/ftc-returns-more-29-million-consumers-harmed-warrior-trading)).
- Importantly, the FTC action targeted the *marketing*, not the mechanics of the strategy, and did not allege
  his own trading results were fabricated.

### The base-rate problem

Academic studies of day-trader populations consistently find severe negative skew: ~3% of Brazilian futures
day traders profitable over a year (1.1% above minimum wage); ~1% of Taiwanese day traders consistently
profitable after costs; 70–95% of retail day traders losing money over time
([study roundups](https://www.quantifiedstrategies.com/day-trading-statistics/),
[Trade That Swing](https://tradethatswing.com/the-day-trading-success-rate-the-real-answer-and-statistics/)).
Against that base rate, "learn my system" marketing faces a survivorship-bias objection Cameron himself now has
to disclaim: he is the visible survivor; the failed accounts aren't on YouTube.

### Why most students can't replicate it (a sober reading)

- **Skill intensity:** tape reading, sub-minute execution, and split-second discretion resist codification —
  the checklist is teachable; the reflexes are not.
- **Psychological load:** the system's math dies the moment a trader lets one loser run (see his own
  loser-hold-time stats); most people can't sustain the discipline under real money stress.
- **Costs and frictions:** commissions/ECN fees, slippage on illiquid names, PDT capital requirements, and
  (for sub-$25k accounts) trade-count limits all eat a thin edge.
- **Regime dependence:** students who learned in a hot tape bleed out in a cold one.
- **Capacity:** even executed perfectly, the edge lives in a small pond — it is a good personal income
  strategy, not an asset-management strategy.

### Other criticisms found

- Refund-policy and billing complaints (BBB, Trustpilot mixed reviews).
- A litigious posture toward critics ([beststockstrategy review](https://beststockstrategy.com/warrior-trading/),
  [ProConsumer](https://www.proconsumer.com/company/warrior-trading/)) — worth knowing when weighing sources
  on both sides, since several "reviews" in this space are competitors.

---

## 10. Mapping the strategy onto this repo (TradingAgents)

TradingAgents makes **daily-horizon BUY/HOLD/SELL decisions** from analyst reports; Cameron's system is an
**intraday, tick/candle-level execution strategy**. A faithful port is out of scope for the current
architecture (no intraday bars, Level 2, or order execution). What *does* transfer cleanly:

1. **The Five Pillars as a universe screener** (dataflows layer): price $1–$20, day change ≥ +10%, relative
   volume ≥ 5x vs. 30-day average, float below threshold, and a fresh news catalyst — a deterministic pre-filter
   producing a daily "momentum watchlist" before any LLM agent runs.
2. **A "momentum analyst" persona** (analysts layer): a technical analyst variant prompted around gap
   continuation, bull-flag/HOD structure, and relative volume rather than MACD/RSI mean-reversion framing.
3. **Risk-manager rules that mirror his**: enforce minimum 2:1 reward/risk on proposed trades, a daily max-loss
   circuit breaker, and post-loss size-down ("Trader Rehab") logic in the risk management team.
4. **Honest expectations**: the FTC record is a useful reminder for this repo's own disclaimers — backtests of
   momentum scalping without slippage/liquidity modeling on low-float names will wildly overstate results.

---

## Sources

**Primary / regulatory**
- [FTC press release — FTC Cracks Down on Warrior Trading (Apr 2022)](https://www.ftc.gov/news-events/news/press-releases/2022/04/federal-trade-commission-cracks-down-warrior-trading-misleading-consumers-false-investment-promises)
- [FTC — Warrior Trading complaint (PDF)](https://www.ftc.gov/system/files/ftc_gov/pdf/2023198WarriorTradingComplaint_0.pdf)
- [FTC — case page: FTC v. Warrior Trading, Inc.](https://www.ftc.gov/legal-library/browse/cases-proceedings/2023198-warrior-trading-inc-ftc-v)
- [FTC — $2.9M refunds to 20,402 consumers (Jan 2023)](https://www.ftc.gov/news-events/news/press-releases/2023/01/ftc-returns-more-29-million-consumers-harmed-warrior-trading)

**Warrior Trading / Ross Cameron materials (authoritative for what he teaches; self-interested on performance)**
- [Warrior Trading — Stock Selection PDF (the Five Pillars)](https://cdn.warriortrading.com/warriortrading.com/assets/Warrior%20Trading%20-%20Stock%20Selection.pdf)
- [Momentum Day Trading Strategy](https://www.warriortrading.com/momentum-day-trading-strategy/) ·
  [Gap and Go](https://www.warriortrading.com/gap-go/) ·
  [Gap and Go terminology](https://www.warriortrading.com/gap-and-go-definition-day-trading-terminology/) ·
  [Micro pullback strategy](https://www.warriortrading.com/pull-back-trading-strategy/) ·
  [Tape reading](https://www.warriortrading.com/what-is-tape-reading-in-trading/)
- [$583 → $1M challenge page](https://www.warriortrading.com/583-to-1mil/) ·
  [Verified earnings](https://www.warriortrading.com/ross-camerons-verified-day-trading-earnings/) ·
  [Max-loss red day recovery](https://www.warriortrading.com/how-i-bounced-back-after-my-max-loss-red-day/) ·
  [Tools FAQ](https://support.warriortrading.com/support/solutions/articles/19000080962-what-software-and-trading-tools-do-you-use-and-recommend-for-when-i-trade-live-)
- [Entrepreneur — "I Turned $583 into $10 Million" (Cameron)](https://www.entrepreneur.com/money-finance/how-i-turned-583-into-10-million-by-day-trading/456246)

**Independent / secondary**
- [Berkshire Eagle — $3M settlement coverage](https://www.berkshireeagle.com/news/southern_berkshires/warrior-trading-ross-cameron-great-barrington-federal-trade-commission-court-complaint-misleading-claims/article_9f4f529e-c193-11ec-8c26-ab838f5c1889.html) ·
  [Berkshire Edge](https://theberkshireedge.com/great-barrington-stock-trading-company-agrees-to-3-million-settlement-with-feds/)
- [Traders Union — Ross Cameron profile (stats)](https://tradersunion.com/persons/ross-cameron/)
- [ebizfacts — Warrior Trading review](https://ebizfacts.com/ross-cameron-warrior-trading-review/) ·
  [Bullish Bears review](https://bullishbears.com/warrior-trading-review/)
- [TradingView — "Ross Cameron 5 Pillars Filter" community indicator](https://www.tradingview.com/script/mbqMf3pF-Ross-Cameron-5-Pillars-Filter/) ·
  [Third-party scanner replication (GitHub)](https://github.com/Jayanth7416/ross-cameron-stock-scanner)
- Day-trading base rates: [QuantifiedStrategies](https://www.quantifiedstrategies.com/day-trading-statistics/) ·
  [Trade That Swing](https://tradethatswing.com/the-day-trading-success-rate-the-real-answer-and-statistics/)
