# Cameron Momentum System — Autonomous Execution Spec (Draft v0.1)

> **Status: DRAFT — paper/simulation only.** This spec turns the strategy documented in
> [`docs/research/ross-cameron-strategy.md`](../research/ross-cameron-strategy.md) into a fully mechanical
> rule set that software can execute without a human in the loop, with the retail failure modes documented in
> [`docs/research/why-retail-traders-lose.md`](../research/why-retail-traders-lose.md) encoded as **hard
> guardrails**. The reference implementation lives in `tradingagents/strategies/ross_cameron/` and is tested
> in `tests/test_cameron_strategy.py`. It emits paper trades only — there is deliberately no broker adapter in
> v0.1 (see §10 promotion gates). Nothing here is financial advice; the base-rate evidence says the expected
> outcome of trading this style without verified edge is a loss.

---

## 1. Objective and non-goals

**Objective:** replicate the *decision structure* of Ross Cameron's small-cap momentum strategy — Five
Pillars selection, morning-only momentum setups, asymmetric bracket exits, hard loss governance — as a
deterministic, auditable, unattended system.

**Non-goals (v0.1):** live brokerage execution; short selling; options; tape-reading discretion (replaced
with mechanical volume/structure rules); catalyst *quality* judgment (a candidate LLM extension via the
TradingAgents News Analyst); multi-position portfolio management.

**Honesty clause:** the human strategy's edge partly lives in skills this system does not pretend to have
(sub-second tape reads, catalyst nuance). Where a rule replaces judgment, the rule is *stricter*, not
looser — fewer trades, earlier exits, smaller size.

## 2. Architecture

```
premarket data ──▶ Screener (Five Pillars + dilution/halt) ──▶ ranked watchlist (≤5)
                                                                    │
1-min bars ──▶ CameronEngine (state machine: flat→armed→long→scaled→flat)
                    │ every entry/size/stop change must pass
                    ▼
               RiskGovernor (G1..G8 guardrails, session-scoped)
                    │
                    ▼
               SessionReport (trades, skips log, metrics, next-day size-down)
```

| Component | File | Responsibility |
|---|---|---|
| Config | `config.py` | Every threshold, validated at startup (`validate()` fails loudly) |
| Screener | `screener.py` | Five Pillars + gap + dilution + halt checks; ranked watchlist |
| Setups | `setups.py` | ORB, bull flag, micro pullback, flat top as exact bar logic |
| Risk | `risk.py` | Sizing, circuit breakers, rehab, stop monotonicity |
| Engine | `engine.py` | Bar replay, pessimistic fills, exits, audit log |

## 3. Data requirements

| Input | Frequency | Fields | Candidate sources |
|---|---|---|---|
| Gapper scan snapshot | pre-market, 9:00–9:25 ET | price, prev close, gap %, day change %, pre-market high, day volume, 30-day avg volume, float, halt flag | Polygon/Alpha Vantage snapshot + FMP/Finviz float |
| News catalyst flag | with snapshot | boolean + headline | vendor news feed (or TradingAgents News Analyst) |
| Dilution flags | daily | S-3/shelf on file, active ATM, recent offerings, cash runway < 2 quarters | SEC EDGAR full-text (S-3, 424B5, ATM agreements) |
| Intraday bars | 1-minute, RTH | OHLCV | Polygon / Alpha Vantage intraday |

**Data staleness rule:** in any live/paper deployment, a bar feed gap > 2 minutes on a symbol with an open
position ⇒ exit at next available price and halt the session (fail-safe, not fail-open).

## 4. Parameters (defaults and provenance)

All defaults live in `CameronConfig`; the authoritative values are the code. Summary:

| Parameter | Default | Provenance |
|---|---|---|
| Price band | $1–$20 | Pillar 4 (research §3) |
| Day change | ≥ +10% | Pillar 2 |
| Relative volume | ≥ 5× 30-day avg | Pillar 1 |
| Float | ≤ 20M shares | Pillar 5 |
| Catalyst required | yes | Pillar 3 |
| Gap scan | ≥ +4% | Gap-and-Go routine |
| Reward:risk minimum | 2:1 | His stated rule |
| Risk per trade | 0.5% of equity | Conservative end of his guidance |
| Daily max loss | 1.5% of equity (3 full-risk losers) | G1 |
| Max trades/day | 10 | G3 |
| Entry window | 9:30–10:30 ET | Edge concentration at the open |
| Flat by | 15:55 ET (and stall-exit after 10 bars) | G7; no overnight |
| Slippage model | +1 tick adverse on stop fills | G-cost realism |

## 5. Daily schedule (ET)

1. **09:00–09:25** — pull gapper snapshots; fetch float, news, dilution flags; run `build_watchlist`
   (§ ranked by relative volume, max 5 names). Zero qualifying names ⇒ **no session** (G8: regime filter is
   structural — the system never manufactures trades).
2. **09:30** — engine starts consuming 1-min bars. The first completed bar of each watchlist symbol may arm
   the opening-range-breakout signal.
3. **09:30–10:30** — entry window: detectors arm at most one signal at a time; one open position at a time.
4. **10:30–15:55** — no new entries; open positions manage exits only.
5. **15:55** — hard flatten anything still open (in practice the stall rule closes positions much earlier).
6. **Post-session** — persist `SessionReport` (trades, skip log, metrics); carry `next_session_multiplier`
   into the next session (size-down day after a max-loss day).

## 6. Setup definitions (exact, as implemented)

All entries are **stop-buy triggers above structure** with a **stop at structure low** — the system never
buys a falling price and never enters without a defined invalidation (G2). A signal is rejected outright if
the stop distance exceeds 5% of entry. Armed signals expire after 10 bars untriggered.

- **Opening-range breakout (Gap-and-Go):** armed off the first completed 1-min bar; trigger = first-bar high
  + $0.01 (or pre-market high + $0.01 if higher); stop = first-bar low.
- **Bull flag:** pole = ≥2 consecutive green bars; pullback = 2–3 consecutive red bars retracing < 50% of the
  pole and holding above the pole low; trigger = last pullback bar high + $0.01 (the "first candle to make a
  new high"); stop = pullback low.
- **Micro pullback:** impulse = green bar making the 10-bar high; pause = 1–3 bars that stop making highs but
  hold above the impulse bar's midpoint; trigger = pause high + $0.01; stop = pause low.
- **Flat top:** ≥3 of the trailing 6 bars with highs within 0.3% of the window high and rising lows;
  trigger = resistance + $0.01; stop = window low.

**Fill model (pessimistic by design):** entry fills at max(trigger, bar open) + 1 tick; if a bar *opens* more
than 0.5% beyond the trigger the signal is cancelled, not chased (G4). Protective stops fill at min(stop, bar
open) − 1 tick. When one bar touches both stop and target, the stop is assumed to fill first.

**Exit ladder:** sell half at +2R and move the stop to breakeven (the trade pays for itself before it may
run); then trail the remainder at each completed bar's low; exit any unscaled position that has gone nowhere
for 10 bars (stall rule — the anti-disposition mechanic); flatten everything by 15:55.

## 7. Position sizing

```
risk_$   = equity × 0.5% × rehab_multiplier × carryover_multiplier
risk_$   = min(risk_$, room left under the daily max-loss breaker)
shares   = floor(risk_$ / (entry − stop))
shares   = min(shares,
               50% of equity / entry,                  # notional cap
               20% × avg volume of last 5 one-min bars, # participation cap (G5)
               0.05% × float)                           # footprint cap
```

The participation and float caps are the anti-"replication gap" rule: the audited human edge exists at a
size the tape can absorb; an autonomous copy must be small relative to the liquidity it consumes.

## 8. Guardrails — failure findings → enforced rules

| ID | Documented failure mode (research doc §) | Rule in this system | Enforced in |
|---|---|---|---|
| G1 | Uncapped losses, revenge trading, martingale (§2.5) | Fixed dollar risk/trade; daily −1.5% circuit breaker halts the session; 3 straight losers ⇒ risk ×0.25; next session after a max-loss day ⇒ risk ×0.5; no averaging down (no add-to-loser path exists) | `risk.py` |
| G2 | Disposition effect — winners cut, losers ridden (§2.2) | 2:1 minimum asymmetry at signal construction; stop defined before entry; stops may only ratchet up (`validate_stop_move`); scale-half + breakeven automates "let it run" | `setups.py`, `risk.py`, `engine.py` |
| G3 | Overtrading / overconfidence (§2.1) | ≤10 trades/day, 1 open position, ≤5 watchlist names; no signal ⇒ no trade | `config.py`, `risk.py` |
| G4 | Attention-chasing, FOMO entries (§2.3) | Entries only at pre-armed triggers; bars opening >0.5% past the trigger are skipped; extended moves produce no signal by construction | `engine.py` |
| G5 | Replication gap — size/latency vs the tape (§3.5) | Participation ≤20% of recent 1-min volume; ≤0.05% of float; adverse-tick fill model | `risk.py`, `engine.py` |
| G6 | Issuer dilution — "the company sells the spike" (§3.3) | Snapshots with dilution flags (shelf/ATM/offering) are screened out before the watchlist | `screener.py` |
| G7 | Marinating in dead trades; overnight lottery holds (§2.4) | Entry window ends 10:30; stall exit after 10 flat bars; hard flatten 15:55; long-only, no overnight | `engine.py` |
| G8 | Regime blindness — forcing a hot-tape playbook in a cold tape (§3.5) | Five Pillars are absolute, not relative: a day with no qualifying gappers is a no-trade day by construction | `screener.py` |

Cross-cutting: every rejection is written to the session report's `skips` log with timestamp, stage, and
reason — an unattended system must be auditable after the fact; and `CameronConfig.validate()` refuses to
start with self-defeating parameters (e.g. sub-1:1 reward:risk).

## 9. Kill switches and failure handling

- **Daily circuit breaker** (G1) — halts entries and flattens any open position at the next bar.
- **Stale data / feed error** — flatten and halt (fail-safe; §3).
- **Halt flag on a snapshot** — candidate excluded; v0.1 does not model intraday LULD halts and therefore
  **must not run live** until it does (see §11).
- **Weekly stop (deployment layer):** two max-loss days in one week ⇒ no trading for the rest of the week.
  Session-scoped code cannot see the week; the scheduler that launches sessions owns this rule.

## 9b. Replay harness (running the sim gate)

`replay.py` + `polygon_data.py` implement the §10 sim gate over Polygon.io historical data:

```bash
export POLYGON_API_KEY=...
# one session (discovers that day's gappers, builds 09:25 snapshots, replays RTH bars)
python -m tradingagents.strategies.ross_cameron.replay --date 2026-07-08
# a month, compounding equity and chaining the G1 size-down across sessions
python -m tradingagents.strategies.ross_cameron.replay --start 2026-06-01 --end 2026-06-30 --json june.json
# free API tier: stay under 5 requests/minute (responses are cached, re-runs are free)
python -m tradingagents.strategies.ross_cameron.replay --date 2026-07-08 --throttle 12.5
```

Point-in-time honesty rules the harness enforces:
- the 09:25 snapshot uses **pre-market bars only** (price, pre-market high, cumulative volume) and
  information knowable before the open (prior closes, 30-day average volume, overnight headlines) — no
  lookahead into the session being traded;
- candidate discovery reproduces the raw gap scanner (gap ≥4% vs. the previous *trading* day, loose price
  band, ≥500k shares) and leaves the real screening to the Five Pillars;
- relative volume at scan time is pre-market volume over the 30-day average — stricter than intraday RVOL,
  which biases toward fewer candidates (the conservative direction);
- float uses Polygon shares outstanding (overstates float → biases toward rejection); dilution flags are
  unavailable and stay empty — G6 remains an EDGAR integration item;
- the aggregate report (`RangeResult.metrics()`) provides exactly the §10 gate numbers: profit factor,
  win rate, max drawdown on the compounded equity curve, and max-loss-day count.

## 10. Promotion gates (sim → paper → live-micro)

| Gate | Requirement before advancing |
|---|---|
| Sim → paper | ≥60 replayed sessions on historical 1-min data **net of the pessimistic fill model**: profit factor ≥1.3, max drawdown ≤6% of equity, no guardrail breach in the audit log |
| Paper → live-micro | ≥40 live paper sessions on a real-time feed meeting the same bar; slippage observed ≤ modeled; a human reviews the skip log weekly |
| Live-micro | Real orders at minimum size only (100-share lots), full G1–G8 active, PDT-compliant account ≥$30k, kill switch wired to a human-reachable off button |

If sim results only clear the bar with the *optimistic* assumptions removed (no slippage, fills at trigger),
the strategy fails the gate — that is precisely the backtest mirage documented in the failure research.

## 11. Known gaps in v0.1 (why this stays paper-only)

1. **LULD halts:** low-float gappers halt constantly; halt-resume gaps can jump a stop by 20%+. Needs a halt
   feed and resume logic before any live order.
2. **Catalyst quality:** `has_news_catalyst` is a boolean; a stale PR and an FDA approval currently look the
   same. Candidate: route headlines through the TradingAgents News Analyst for a catalyst grade, and require
   grade ≥ B for the pillar to pass.
3. **Short-sale restriction / SSR and locate dynamics** are unmodeled (long-only mitigates but squeeze
   mechanics affect longs too).
4. **Float data quality:** float figures from free vendors are often stale after offerings — which is exactly
   when they matter (ties to G6).
5. **Single-position focus** leaves capacity unused on multi-gapper days; deliberate for v0.1.

## 12. Roadmap: capturing the discretionary layer

The taught strategy has a discretionary layer (tape reading, "catalyst feel") this spec deliberately replaced
with stricter mechanical rules. Cameron's public content — thousands of hours of narrated live trading and
recap videos — makes parts of it learnable, in increasing order of ambition:

1. **Rule mining from transcripts (cheap, high yield).** Pull public video transcripts, LLM-extract his
   stated heuristics (when he skips a trade, what makes news "good", reversal-time habits, red flags like
   recent offerings or one-and-done pops), and distill them into (a) a catalyst-grading rubric and (b)
   additional mechanical vetoes for this engine. Must sample his red-day/loss videos too, or the mined rules
   inherit selection bias.
2. **Catalyst grading (closes §11.2).** "Catalyst feel" is mostly a taxonomy he says out loud: FDA approval >
   phase data > contract win > partnership > vague PR, weighted by recency, magnitude, and float context.
   That converts into a graded score — deterministic keyword taxonomy first, optionally a TradingAgents News
   Analyst LLM pass — with the pillar requiring grade ≥ B instead of a boolean.
3. **Tape-reading proxies (partial).** True tape reading needs Level 2 depth; Polygon trades/quotes (paid
   tiers) support proxies for what he verbalizes: buying acceleration into the trigger, prints at the ask vs.
   bid, repeated rejections at one offer ("big seller"), halt-resume behavior. These become entry-confirmation
   filters, not judgment.
4. **Behavioral cloning from screen recordings (research-grade; not recommended next).** Vision models over
   recorded Level 2 + his executions. Expensive to label, fragile out of regime, ToS-sensitive at scale, and
   it imports a survivor's reflexes without his adaptivity.

The honest boundary: the sub-second reflex component is exactly the part the replication-gap research says
does not transfer. This system's counter is structural (no-chase guard, pessimistic fills, participation
caps) — it refuses the situations where reflexes decide the outcome, rather than pretending to have them.

## 13. Compliance and honesty notes

- The FTC action against Warrior Trading was about *marketing outcomes*, and the base-rate research is
  unambiguous: most people who trade this style lose. This system's guardrails bound losses; they do not
  manufacture edge. Only the promotion gates (§10) can demonstrate edge, and only prospectively.
- Any published results from this system must report net-of-cost figures, the full skip/audit log
  methodology, and the number of sessions — no cherry-picked windows (that is the survivorship trap the
  research documents).
