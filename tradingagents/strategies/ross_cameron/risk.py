"""Risk governor: the failure-mode research encoded as hard, code-level rules.

Every rule here counters a documented way retail traders lose money
(docs/research/why-retail-traders-lose.md). The governor is deliberately
NOT an advisor — the engine cannot enter, size, or move a stop without
passing through it, and its refusals are final for the session.

Guardrail IDs (G1..G8) cross-reference the execution spec:
- G1 mechanical loss caps: per-trade dollar risk, daily circuit breaker,
  post-loss size-down ("trader rehab"), no re-entry spiral.
- G2 asymmetry before entry: minimum reward:risk, stops never widen.
- G3 scarcity over activity: max trades/day, max open positions.
- G4 no chasing (enforced in the engine's fill model).
- G5 liquidity/participation caps (you are not filling a guru's size).
- G6 dilution screen (enforced in the screener).
- G7 time discipline: entry window, stall exits, flat by close.
- G8 regime: zero qualifying setups means zero trades, by construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .config import CameronConfig
from .models import Bar, Signal, TradeRecord


@dataclass
class SessionRiskState:
    equity_start: float
    realized_pnl: float = 0.0
    trades_opened: int = 0
    consecutive_losses: int = 0
    halted_reason: str = ""
    carryover_multiplier: float = 1.0   # size-down inherited from a max-loss day
    records: list[TradeRecord] = field(default_factory=list)

    @property
    def halted(self) -> bool:
        return bool(self.halted_reason)


class RiskGovernor:
    """Session-scoped gatekeeper for entries, sizing, and stop changes."""

    def __init__(
        self,
        cfg: CameronConfig,
        equity: float,
        carryover_multiplier: float = 1.0,
    ) -> None:
        cfg.validate()
        if equity <= 0:
            raise ValueError("equity must be positive")
        self.cfg = cfg
        self.state = SessionRiskState(
            equity_start=equity, carryover_multiplier=carryover_multiplier
        )

    # ------------------------------------------------------------------
    # Entry gate
    # ------------------------------------------------------------------
    def can_enter(self, now: datetime, open_positions: int) -> tuple[bool, str]:
        cfg, st = self.cfg, self.state
        t = now.time()
        if st.halted:
            return False, f"session halted: {st.halted_reason}"
        if t < cfg.entries_start:
            return False, "before entry window (G7)"
        if t >= cfg.no_entries_after:
            return False, "after entry cutoff (G7)"
        if open_positions >= cfg.max_open_positions:
            return False, "max open positions reached (G3)"
        if st.trades_opened >= cfg.max_trades_per_day:
            return False, "max trades per day reached (G3)"
        return True, ""

    def validate_signal(self, signal: Signal) -> tuple[bool, str]:
        """G2: asymmetry must exist before entry, never be hoped for after."""
        if signal.risk_per_share <= 0:
            return False, "non-positive risk per share"
        if self.cfg.min_reward_risk < 1.0:
            return False, "config allows sub-1:1 reward:risk (G2)"
        return True, ""

    # ------------------------------------------------------------------
    # Sizing (G1 dollar risk, G5 participation caps)
    # ------------------------------------------------------------------
    def risk_multiplier(self) -> float:
        m = self.state.carryover_multiplier
        if self.state.consecutive_losses >= self.cfg.rehab_consecutive_losses:
            m *= self.cfg.rehab_risk_multiplier
        return m

    def size(self, signal: Signal, recent_bars: list[Bar], float_shares: int) -> int:
        cfg, st = self.cfg, self.state
        risk_dollars = st.equity_start * (cfg.risk_per_trade_pct / 100.0) * self.risk_multiplier()
        # Never risk more than the room left under the daily circuit breaker.
        loss_room = st.equity_start * (cfg.daily_max_loss_pct / 100.0) + min(st.realized_pnl, 0.0)
        risk_dollars = min(risk_dollars, max(loss_room, 0.0))
        if risk_dollars <= 0:
            return 0

        # Epsilon counters float noise in cent-quantized price differences
        # (e.g. 5.00 - 4.85) so the floor division doesn't drop a share.
        shares = int(risk_dollars / signal.risk_per_share + 1e-9)
        # Notional cap: a scalp is not an all-in bet.
        max_notional = st.equity_start * (cfg.max_position_notional_pct / 100.0)
        shares = min(shares, int(max_notional / signal.entry))
        # G5: participation cap vs. recent traded volume — the replication
        # gap is latency + size; an autonomous account must be small
        # relative to the tape it trades.
        if recent_bars:
            window = recent_bars[-5:]
            avg_volume = sum(b.volume for b in window) / len(window)
            shares = min(shares, int(avg_volume * cfg.max_participation_pct / 100.0))
        if float_shares > 0:
            shares = min(shares, int(float_shares * cfg.max_float_position_pct / 100.0))
        return max(shares, 0)

    # ------------------------------------------------------------------
    # Stop management (G2: stops tighten or hold; they never widen)
    # ------------------------------------------------------------------
    @staticmethod
    def validate_stop_move(current_stop: float, proposed_stop: float) -> bool:
        return proposed_stop >= current_stop

    # ------------------------------------------------------------------
    # Trade lifecycle
    # ------------------------------------------------------------------
    def on_trade_opened(self) -> None:
        self.state.trades_opened += 1

    def on_trade_closed(self, record: TradeRecord) -> None:
        st = self.state
        st.records.append(record)
        st.realized_pnl += record.pnl
        if record.is_winner:
            st.consecutive_losses = 0
        elif record.pnl < 0:
            st.consecutive_losses += 1
        # G1: hard daily circuit breaker — no discretion, no "one more trade".
        max_loss = st.equity_start * (self.cfg.daily_max_loss_pct / 100.0)
        if st.realized_pnl <= -max_loss:
            st.halted_reason = (
                f"daily max loss hit ({st.realized_pnl:+.2f} vs -{max_loss:.2f} limit)"
            )

    def next_session_multiplier(self) -> float:
        """Size-down carryover for the session after a max-loss day (G1)."""
        if self.state.halted:
            return self.cfg.next_day_after_max_loss_multiplier
        return 1.0
