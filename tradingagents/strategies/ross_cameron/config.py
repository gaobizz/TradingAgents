"""Configuration for the Ross Cameron momentum strategy engine.

Every threshold is sourced from the research docs:

- docs/research/ross-cameron-strategy.md   (what the strategy prescribes)
- docs/research/why-retail-traders-lose.md (the failure-mode guardrails)
- docs/strategy/cameron-autonomous-execution-spec.md (rule IDs G1..G13)

Values that come straight from Warrior Trading's published materials are
marked "pillar"; values that exist to counter a documented retail failure
mode are marked with their guardrail ID (G-number). Change them via
``CameronConfig(...)`` overrides, not by editing the defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time


@dataclass(frozen=True)
class CameronConfig:
    # ------------------------------------------------------------------
    # Five Pillars screen (pillar values; see research report section 3)
    # ------------------------------------------------------------------
    min_price: float = 1.0                  # pillar 4: price floor
    max_price: float = 20.0                 # pillar 4: price ceiling
    min_day_change_pct: float = 10.0        # pillar 2: already up on the day
    min_relative_volume: float = 5.0        # pillar 1: 5x 30-day average
    max_float_shares: int = 20_000_000      # pillar 5: low float preferred
    require_catalyst: bool = True           # pillar 3: news catalyst
    min_gap_pct: float = 4.0                # pre-market gap scan threshold
    block_dilution_flagged: bool = True     # G6: issuer sells the spike
    max_watchlist_size: int = 5             # focus: a handful of A+ names

    # ------------------------------------------------------------------
    # Setup detection (1-minute bars)
    # ------------------------------------------------------------------
    min_reward_risk: float = 2.0            # 2:1 minimum profit-to-loss (G2)
    max_stop_distance_pct: float = 5.0      # reject signals with stops wider
                                            # than this % of entry price
    flag_min_pullback_bars: int = 2         # bull flag: 2..3 red candles
    flag_max_pullback_bars: int = 3
    flag_max_retrace: float = 0.5           # pullback must hold >50% of pole
    micro_min_pause_bars: int = 1           # micro pullback: 1..3 bar pause
    micro_max_pause_bars: int = 3
    flat_top_min_touches: int = 3
    flat_top_tolerance_pct: float = 0.3     # highs within 0.3% = same level
    signal_ttl_bars: int = 10               # armed trigger expires unfilled
    chase_tolerance_pct: float = 0.5        # G4: if price gaps >0.5% past the
                                            # trigger, skip — do not chase
    slippage_ticks: int = 1                 # adverse ticks assumed on stop-order
                                            # fills (entries and protective stops)

    # ------------------------------------------------------------------
    # Position sizing (fixed fractional dollar risk)
    # ------------------------------------------------------------------
    risk_per_trade_pct: float = 0.5         # % of equity risked per trade (G1)
    max_position_notional_pct: float = 50.0 # position value cap, % of equity
    max_participation_pct: float = 20.0     # G5: shares <= this % of average
                                            # volume of the last 5 one-min bars
    max_float_position_pct: float = 0.05    # shares <= 0.05% of the float

    # ------------------------------------------------------------------
    # Session risk governor (failure-mode guardrails)
    # ------------------------------------------------------------------
    daily_max_loss_pct: float = 1.5         # G1: hard daily circuit breaker
                                            # (= 3 full-risk losers)
    max_trades_per_day: int = 10            # G3: scarcity over activity
    max_open_positions: int = 1             # focus; no basket of lottery tickets
    rehab_consecutive_losses: int = 3       # G1/anti-revenge: after 3 straight
    rehab_risk_multiplier: float = 0.25     #   losers, risk drops to 25%
    next_day_after_max_loss_multiplier: float = 0.5  # size-down carryover day
    stall_exit_bars: int = 10               # G-disposition: exit if the trade
                                            #   goes nowhere for N bars
    entries_start: time = time(9, 30)       # regular session open (ET)
    no_entries_after: time = time(10, 30)   # edge decays after the open
    flatten_by: time = time(15, 55)         # never hold overnight
    # NOTE (G8, regime): with max_open_positions=1 and the Five Pillars
    # screen, days with no qualifying gappers produce zero trades by
    # construction — the engine never manufactures activity.

    def validate(self) -> None:
        """Fail loudly on nonsensical parameter combinations (unattended runs)."""
        problems: list[str] = []
        if self.min_price <= 0 or self.max_price <= self.min_price:
            problems.append("price band must satisfy 0 < min_price < max_price")
        if self.min_reward_risk < 1.0:
            problems.append("min_reward_risk below 1:1 defeats the edge (G2)")
        if not 0 < self.risk_per_trade_pct <= 2.0:
            problems.append("risk_per_trade_pct must be in (0, 2] (G1)")
        if self.daily_max_loss_pct < self.risk_per_trade_pct:
            problems.append("daily_max_loss_pct must cover at least one full-risk trade")
        if not 0 < self.rehab_risk_multiplier <= 1.0:
            problems.append("rehab_risk_multiplier must be in (0, 1]")
        if self.flag_min_pullback_bars > self.flag_max_pullback_bars:
            problems.append("bull-flag pullback bar range is inverted")
        if self.no_entries_after <= self.entries_start:
            problems.append("no_entries_after must be later than entries_start")
        if problems:
            raise ValueError("CameronConfig invalid: " + "; ".join(problems))


DEFAULT_CONFIG = CameronConfig()
