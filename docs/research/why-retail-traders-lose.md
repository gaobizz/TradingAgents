# Why the Average Retail Trader Loses — Evidence and Lessons

> **Research date:** 2026-07-09 · Companion to [`ross-cameron-strategy.md`](./ross-cameron-strategy.md).
> The FTC found that "the vast majority" of Warrior Trading customer accounts lost money while Cameron himself
> made audited millions in the same stocks. This document collects the best available evidence on *why* that
> asymmetry is the norm — across academic cohort studies, behavioral finance, and market microstructure — and
> distills it into guardrails worth encoding (in a trader's rules, and in TradingAgents' risk layer).

---

## TL;DR

Retail losses are not one mistake — they are a **stack** of behavioral biases sitting on top of a structural
cost machine. The average retail trader (a) trades far too much out of overconfidence, (b) buys
attention-grabbing lottery-like stocks precisely when they're most likely to mean-revert, (c) sells winners
~50% faster than losers (the disposition effect — backwards relative to expectancy), (d) pays a
spread/slippage/fee stack that exceeds any thin edge, (e) is often literally trading against the issuing
company's dilution machine in small caps, and (f) doesn't measurably learn from experience. Each mechanism is
individually well-documented; together they reliably produce the observed base rates: **~1–3% of day traders
are durably profitable, and the average equity-fund investor has underperformed the S&P 500 for 15 straight
years.** Every one of these failure modes has a mechanical countermeasure — listed at the end.

---

## 1. The scoreboard: how badly, exactly

| Population | Result | Source |
|---|---|---|
| 66,465 US discount-broker households, 1991–96 | Average household: 16.4%/yr vs market 17.9%; the most active quintile: **11.4%/yr** — a ~6.5pt penalty for trading; average turnover 75%/yr | [Barber & Odean 2000, *Trading Is Hazardous to Your Wealth*](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=219228) |
| All Taiwan Stock Exchange day traders, 1992–2006 (3.7B transactions) | Day traders lose **23.9 bps per day** net of fees; **<1% consistently profitable**, ~3% net-positive in a typical year; survival 44%/24%/15% at 1/2/3 years | [Barber, Lee, Liu & Odean](https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20and%20Learning%20110217.pdf) |
| All new Brazilian equity-futures day traders, 2013–15 | Of those who persisted 300+ sessions, **97% lost money**; ~1% earned more than minimum wage | Chague, De-Losso & Giovannetti, via [study roundups](https://www.quantifiedstrategies.com/day-trading-statistics/) |
| US equity-fund investors (DALBAR QAIB) | 2024: average equity investor **16.54% vs S&P 25.02%** (−848 bps, second-worst gap in a decade); **15 consecutive years** of underperformance | [DALBAR 2025 release](https://www.dalbar.com/press-release/investors-missed-the-best-of-2024s-market-gains-latest-dalbar-investor-behavior-report-finds/) |
| Retail options traders, Nov 2019–Jun 2021 | **~$2.1B aggregate losses**; ~$364k lost *per day* on debit orders after costs; trading costs $6.4B indirect + $0.9B direct | [Bryzgalova, Pavlova & Sikorskaya, J. Finance 2023](https://onlinelibrary.wiley.com/doi/10.1111/jofi.13285) / [MIT Sloan summary](https://mitsloan.mit.edu/ideas-made-to-matter/retail-investors-lose-big-options-markets-research-shows) |
| 0DTE options (now >75% of retail S&P option trades) | 0DTE trades lose **4.7%** vs +0.19% for non-0DTE; quoted spreads on cheap weeklies average up to **12.6%** | [Beckmeyer, Branger & Gayda](https://papers.ssrn.com/sol3/Delivery.cfm/4404704.pdf?abstractid=4404704&mirid=1) |
| Robinhood herding episodes, 2018–20 | Top stocks bought each day: **−4.7% abnormal return over the next 20 days** | [Barber, Huang, Odean & Schwarz, J. Finance 2022](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3715077) |
| Lottery-stock holders | Underperform by **2–3%/yr**; effect strongest among low-income investors | [Kumar 2009, *Who Gambles in the Stock Market?*](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2009.01483.x) |
| Retail CFD/forex accounts | Broker-disclosed loss rates of ~70–90% | EU/UK mandated disclosures, [roundup](https://www.quantifiedstrategies.com/what-percentage-of-day-traders-fail-statistics/) |
| Warrior Trading customers, 2018–2021 | "The **vast majority** of customer accounts lost money" | [FTC complaint](https://www.ftc.gov/system/files/ftc_gov/pdf/2023198WarriorTradingComplaint_0.pdf) |

Two distinct populations, same direction: **investors** underperform by percentage points per year (bad
timing), while **active day traders** lose outright at 90%+ rates (bias stack × cost stack × frequency).

---

## 2. The behavioral failure modes

### 2.1 Overconfidence → overtrading
The foundational result: trading volume itself is the tax. Barber & Odean's most-active households earned
11.4% vs the market's 17.9%; turnover, not stock selection, explained the gap. Frequency multiplies every
other error and every cost. Men trade more and lose more than women; leverage magnifies it
([Leveraging Overconfidence](https://gflec.org/wp-content/uploads/2023/04/Ko-Barber-Huang-Odean-Leveraging-Overconfidence-CB2023.pdf)).

### 2.2 The disposition effect — selling winners, riding losers
Odean's study of 10,000 retail accounts: investors realize gains **~50% more readily than losses**, and the
winners they sell subsequently *outperform* the losers they keep — the behavior is not explained by taxes,
rebalancing, or information ([Odean 1998](https://faculty.haas.berkeley.edu/odean/papers%20current%20versions/areinvestorsreluctant.pdf),
[Shefrin & Statman 1985](https://en.wikipedia.org/wiki/Disposition_effect)). This is the exact inverse of
positive expectancy ("cut losses, let winners run"). Notably, even Ross Cameron's own published stats show
losers held longer than winners (~7–14 min vs ~4 min) — the bias is universal; his system survives it only
because his loss *sizes* are capped tightly.

### 2.3 Attention-induced buying — trading the same stocks as everyone else, late
Retail concentrates purchases in whatever grabs attention (news, top-gainer lists, social feeds). The
Robinhood study found intense herding episodes were followed by **−4.7% abnormal returns in 20 days**. The
top-gappers scan *is* an attention list: by the time a stock is on every scanner, the marginal buyer is late.
Momentum specialists profit by selling into precisely this flow — the average participant *is* the flow.

### 2.4 Lottery preference — overpaying for skewness
Kumar: retail systematically overweights low-priced, high-volatility, high-skewness "lottery" stocks, which
underperform by 2–3%/yr; demand for them rises in downturns, and the burden falls heaviest on those who can
least afford it. **The Five-Pillars universe (a $2 stock up 40% on news) is the purest lottery-stock
concentrate in the market.** Holding these names has negative average returns — any edge must come from
timing and exit discipline, never from exposure itself.

### 2.5 Loss aversion under fire — revenge trading, averaging down, pulled stops
Emotional cascade after a loss: re-enter impulsively, widen or delete the stop, average down, oversize to
"get it back." Industry and FINRA-cited analyses identify emotional post-loss decision-making — not strategy
choice — as the primary proximate driver of blowups ([overview](https://www.axi.com/int/blog/education/revenge-trading);
even [Warrior Trading's own article](https://www.warriortrading.com/revenge-trading/) calls revenge trading
"the leading cause of trader failure"). A single uncapped loss can erase months of correct 2:1 trades.

### 2.6 Return chasing and panic selling — the behavior gap
DALBAR's 30-year series shows fund investors reliably buy after rallies and sell after declines; poor timing
alone cost ~0.53%/yr pre-Covid and ~1.01%/yr post-Covid, compounding to the 15-year underperformance streak
([DALBAR](https://www.dalbar.com/press-release/investors-missed-the-best-of-2024s-market-gains-latest-dalbar-investor-behavior-report-finds/),
[PLANADVISER summary](https://www.planadviser.com/investors-bad-behavior-led-sharp-underperformance-2024/)).

### 2.7 The illusion of learning
The most sobering finding: experience mostly doesn't help. In Taiwan, the vast majority of day traders lose,
keep trading anyway, and do not rationally update on their own ability; the authors conclude "trading to
learn" is about as rational as "playing roulette to learn"
([Do Day Traders Rationally Learn About Their Ability?](https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20and%20Learning%20110217.pdf)).
Survivorship bias supplies the fuel: the visible winners (gurus, streamers, auditors of their own success)
are the ~1% right tail, so newcomers systematically overestimate base rates.

---

## 3. The structural failure modes (the house edge)

### 3.1 The cost stack eats thin edges
Every trade pays spread + commission/ECN fees + slippage; short-term gains are then taxed as ordinary income.
Taiwan's 23.9 bps/day loss is *net of fees* — costs turn near-zero-sum into reliably negative-sum. In options
the effect is extreme: indirect costs (spreads/price impact, $6.4B) ran **7x** direct commissions ($0.9B);
retail's favorite cheap weeklies carry spreads up to 12.6% of premium. High-frequency styles multiply the
stack by hundreds of trades per month.

### 3.2 Adverse selection — who's on the other side
Retail flow is bought (payment for order flow) and internalized by wholesalers because it is, on average,
profitable to trade against ([Bryzgalova et al.](https://onlinelibrary.wiley.com/doi/10.1111/jofi.13285)).
In fast small-cap tape, the counterparty set is market makers, algos, and experienced short sellers.

### 3.3 In small caps, the issuer sells the spike — dilution as a business model
The mechanism most specific to the low-float gapper niche: unprofitable micro-caps keep shelf registrations
and **at-the-market (ATM) offering programs** ready, and sell new shares directly into exactly the
volume/price spikes that momentum scanners flag. The company is a seller with effectively unlimited
inventory; positions can be diluted 20–40% before holders notice, producing the classic "gaps up on news,
bleeds for weeks" arc ([ATM explainer](https://dilutionwatch.com/articles/atm-offering-explained.html),
[small-cap dilution guide](https://www.merlintrader.com/dilution-atm-pipe-guide/)). Add outright promotion
and pump-and-dump schemes, and *holding* these stocks means being the liquidity for insiders. Red flags:
fresh shelf filing (S-3), <$5M cash runway, history of offerings, spike on light PR.

### 3.4 Undercapitalization and the PDT trap
Under $25k, the pattern-day-trader rule caps round trips, pushing small accounts into overnight holds or
options; more fundamentally, a trader risking rent money cannot honor a 1% stop psychologically — position
sizing discipline collapses exactly when it matters
([analysis](https://www.fxstreet.com/education/why-do-most-retail-traders-fail-and-what-can-i-do-to-improve-my-chances-of-success-202503311406)).

### 3.5 The replication gap — why students can't copy the guru
Signal-following (chatrooms, alerts, streams) adds seconds-to-minutes of latency to a strategy whose edge
lives in the **first seconds** of a breakout. The educator buys the micro pullback; the audience's market
orders fill the educator's exit. Slippage that looks tiny per trade compounds ruinously at scalping frequency
([execution latency](https://bullrush.com/execution-speed-slippage-trading-performance-explain/)). Add regime
dependence — cohorts trained in hot tapes (2020–21) carried aggressive playbooks into cold ones — and the
FTC's observed outcome (guru verified-profitable, majority of students negative) is the *expected* result,
not a paradox.

---

## 4. Synthesis: the same stock, two opposite trades

Put sections 2 and 3 together and the Warrior Trading asymmetry resolves cleanly. A low-float gapper is
simultaneously:

- to a **disciplined specialist**: a 4-minute rental — enter on a defined pattern with a 10¢ stop, sell half
  into the next surge, flat by 10:30, edge = speed + selectivity + capped losses;
- to the **average participant**: a lottery ticket bought on attention (late), held through the backside
  (disposition), averaged down into an ATM offering (adverse selection), funded with money that can't afford
  the stop (undercapitalization), repeated until the account is gone (no learning loop).

Identical instrument, opposite expectancies. **The retail crowd's biases are not incidental to the
specialist's edge — they are its source.** That is the single most important lesson in this file.

---

## 5. Lessons — encoded as guardrails

### For any trader (each counters a documented failure mode)

1. **Cap the downside mechanically, not aspirationally** (vs §2.5): hard per-trade stop at structure, hard
   daily max-loss circuit breaker, automatic size-down protocol after red days. Never widen a stop; never
   average down in a day trade.
2. **Enforce asymmetry before entry** (vs §2.2): no trade without a predefined invalidation level and ≥2:1
   reward-to-risk. Audit your own realized stats monthly — win rate, avg win vs avg loss, hold-time of
   winners vs losers. If losers live longer than winners, the disposition effect is running you.
3. **Trade scarcity, not activity** (vs §2.1): a hard cap on trades/day and a checklist filter (the
   Five-Pillars idea generalizes: *only* take setups where an outsized move is structurally possible).
   Boredom trades are pure cost-stack donations.
4. **Treat attention as a contrarian risk flag** (vs §2.3): if a ticker is on every scanner and feed and you
   have no defined plan, you are the exit liquidity, not the trade.
5. **Never hold the lottery ticket** (vs §2.4, §3.3): in dilution-prone small caps, exposure itself has
   negative expected value. Before touching a gapper, check the share-count trend, shelf/ATM filings, and
   cash runway; assume the issuer sells strength. Time-limit every position.
6. **Price the cost stack first** (vs §3.1): expected edge must clear spread + fees + realistic slippage *at
   your latency*, not the guru's. If the spread is a visible fraction of the expected move (0DTE options,
   thin small caps at size), the trade is dead on arrival.
7. **Separate investing from speculating** (vs §2.6): core capital in boring, rarely-touched index exposure
   (the behavior gap is closed by not acting); a small, firewalled account for active trading, sized so a
   100% loss is tuition, not ruin.
8. **Respect regime** (vs §3.5): track how many A+ setups the market offers per week; when the count drops,
   cut size and frequency instead of forcing the old playbook.
9. **Assume survivorship bias in all marketing** (vs §2.7): visible winners are the right tail. The FTC
   settlement exists because "look at my results" reliably misleads about *your* expected results.
10. **Measure or you will not learn**: the Taiwan evidence says raw experience doesn't teach; only a journal
    with per-trade metrics converts losses into information.

### For TradingAgents (this repo)

- **Risk team as hard gate, not advisor**: implement max daily loss, per-position size caps, and a minimum
  reward/risk requirement as deterministic checks on the Trader's proposals (code, not prompt), mirroring
  guardrails 1–2.
- **Anti-disposition logic**: require every BUY decision to carry an explicit invalidation level and a
  time-stop; flag any plan that adds to a losing position.
- **Attention/sentiment inversion**: teach the Sentiment Analyst that extreme retail attention spikes
  historically precede negative short-horizon abnormal returns (Robinhood −4.7%/20d) — high buzz should
  *raise* the risk score, not just the conviction score.
- **Dilution screen in fundamentals dataflow**: for small-cap candidates, surface shares-outstanding trend,
  recent/pending offerings (S-3, ATM), and cash runway as a first-class "who is on the other side" signal.
- **Cost-realistic backtests**: net expectancy after spread/slippage models scaled to liquidity; report
  results split by regime, and treat any strategy whose edge disappears at realistic latency as invalid.
- **Base-rate humility in reporting**: any strategy documentation (including the Ross Cameron report) should
  carry the population base rates alongside the survivor's numbers — this file is that context.

---

## Sources

**Academic / primary**
- [Barber & Odean (2000), *Trading Is Hazardous to Your Wealth*, J. Finance](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=219228)
- [Odean (1998), *Are Investors Reluctant to Realize Their Losses?*, J. Finance](https://faculty.haas.berkeley.edu/odean/papers%20current%20versions/areinvestorsreluctant.pdf)
- [Barber, Lee, Liu & Odean, *Do Day Traders Rationally Learn About Their Ability?*](https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20and%20Learning%20110217.pdf) ·
  [*The Cross-Section of Speculator Skill* (Taiwan day trading)](https://www.sciencedirect.com/science/article/abs/pii/S1386418113000190)
- [Barber, Huang, Odean & Schwarz (2022), *Attention-Induced Trading and Returns: Evidence from Robinhood Users*, J. Finance](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3715077)
- [Kumar (2009), *Who Gambles in the Stock Market?*, J. Finance](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2009.01483.x)
- [Bryzgalova, Pavlova & Sikorskaya (2023), *Retail Trading in Options and the Rise of the Big Three Wholesalers*, J. Finance](https://onlinelibrary.wiley.com/doi/10.1111/jofi.13285) ·
  [MIT Sloan summary](https://mitsloan.mit.edu/ideas-made-to-matter/retail-investors-lose-big-options-markets-research-shows)
- [Beckmeyer, Branger & Gayda, *Retail Traders Love 0DTE Options… But Should They?*](https://papers.ssrn.com/sol3/Delivery.cfm/4404704.pdf?abstractid=4404704&mirid=1)
- [Ko, Barber, Huang & Odean, *Leveraging Overconfidence*](https://gflec.org/wp-content/uploads/2023/04/Ko-Barber-Huang-Odean-Leveraging-Overconfidence-CB2023.pdf)
- [FTC v. Warrior Trading — complaint](https://www.ftc.gov/system/files/ftc_gov/pdf/2023198WarriorTradingComplaint_0.pdf) and
  [press release](https://www.ftc.gov/news-events/news/press-releases/2022/04/federal-trade-commission-cracks-down-warrior-trading-misleading-consumers-false-investment-promises)

**Industry / secondary**
- [DALBAR QAIB 2025 press release](https://www.dalbar.com/press-release/investors-missed-the-best-of-2024s-market-gains-latest-dalbar-investor-behavior-report-finds/) ·
  [PLANADVISER coverage](https://www.planadviser.com/investors-bad-behavior-led-sharp-underperformance-2024/)
- Day-trading base-rate roundups: [QuantifiedStrategies](https://www.quantifiedstrategies.com/day-trading-statistics/) ·
  [Trade That Swing](https://tradethatswing.com/the-day-trading-success-rate-the-real-answer-and-statistics/) ·
  [CurrentMarketValuation](https://www.currentmarketvaluation.com/posts/the-data-on-day-trading.php)
- Small-cap dilution mechanics: [DilutionWatch — ATM offerings explained](https://dilutionwatch.com/articles/atm-offering-explained.html) ·
  [MerlinTrader — Dilution/ATM/PIPE guide](https://www.merlintrader.com/dilution-atm-pipe-guide/)
- Execution/latency: [BullRush — execution speed & slippage](https://bullrush.com/execution-speed-slippage-trading-performance-explain/)
- Behavioral overviews: [Evidence Investor — the disposition effect](https://www.evidenceinvestor.com/post/the-disposition-effect-why-traders-sell-at-the-wrong-time) ·
  [Axi — revenge trading](https://www.axi.com/int/blog/education/revenge-trading) ·
  [Warrior Trading — revenge trading](https://www.warriortrading.com/revenge-trading/)
