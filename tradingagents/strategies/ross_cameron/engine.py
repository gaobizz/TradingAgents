"""Session engine: runs the strategy autonomously over 1-minute bars.

The engine is a deterministic state machine (paper execution only — it
emits trade records, never broker orders):

    flat ──arm──▶ armed ──trigger──▶ long ──first target──▶ scaled ──▶ flat
      ▲             │ (ttl/chase)      │ (stop/stall/time)     │ (trail/time)
      └─────────────┴──────────────────┴───────────────────────┘

Fill model (deliberately pessimistic, G-cost):
- entries are stop-buys: fill at max(trigger, bar open) + slippage ticks,
  skipped entirely when the bar opens more than ``chase_tolerance_pct``
  past the trigger (G4 — never chase);
- protective stops fill at min(stop, bar open) - slippage ticks;
- when a stop and a target are touched by the same bar, the stop is
  assumed to fill first.

Every rejection (screen, arm, size, chase, halt) is written to the
session report's ``skips`` list so an unattended run is auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .config import CameronConfig, DEFAULT_CONFIG
from .models import (
    Bar,
    ExitReason,
    Fill,
    Position,
    ScreenResult,
    Signal,
    TradeRecord,
)
from .risk import RiskGovernor
from .setups import TICK, detect_intraday, detect_opening_range_breakout


@dataclass
class SessionReport:
    equity_start: float
    trades: list[TradeRecord] = field(default_factory=list)
    skips: list[dict] = field(default_factory=list)
    halted_reason: str = ""
    next_session_multiplier: float = 1.0

    @property
    def realized_pnl(self) -> float:
        return sum(t.pnl for t in self.trades)

    @property
    def equity_end(self) -> float:
        return self.equity_start + self.realized_pnl

    def metrics(self) -> dict:
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        losses = [t.pnl for t in self.trades if t.pnl < 0]
        gross_win, gross_loss = sum(wins), -sum(losses)
        return {
            "trades": len(self.trades),
            "net_pnl": round(self.realized_pnl, 2),
            "win_rate": round(len(wins) / len(self.trades), 4) if self.trades else 0.0,
            "avg_win": round(gross_win / len(wins), 2) if wins else 0.0,
            "avg_loss": round(gross_loss / len(losses), 2) if losses else 0.0,
            "profit_factor": round(gross_win / gross_loss, 3) if gross_loss else None,
            "largest_loss": round(min(losses), 2) if losses else 0.0,
            "halted": self.halted_reason,
        }


class CameronEngine:
    """Runs one session over a screened watchlist. One position at a time."""

    def __init__(
        self,
        cfg: CameronConfig = DEFAULT_CONFIG,
        equity: float = 30_000.0,
        carryover_multiplier: float = 1.0,
    ) -> None:
        cfg.validate()
        self.cfg = cfg
        self.governor = RiskGovernor(cfg, equity, carryover_multiplier)
        self.report = SessionReport(equity_start=equity)
        self._history: dict[str, list[Bar]] = {}
        self._armed: Optional[Signal] = None
        self._armed_age = 0
        self._position: Optional[Position] = None
        self._record: Optional[TradeRecord] = None
        self._orb_armed: set[str] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run_session(
        self,
        watchlist: list[ScreenResult],
        bars_by_symbol: dict[str, list[Bar]],
    ) -> SessionReport:
        """Replay a full session of 1-minute bars for the screened watchlist."""
        order = [r.symbol for r in watchlist if r.passed]
        snapshots = {r.symbol: r.snapshot for r in watchlist}
        timeline = sorted(
            {b.ts for sym in order for b in bars_by_symbol.get(sym, [])}
        )
        indexed = {
            sym: {b.ts: b for b in bars_by_symbol.get(sym, [])} for sym in order
        }

        for ts in timeline:
            for sym in order:
                bar = indexed[sym].get(ts)
                if bar is None:
                    continue
                self._on_bar(sym, bar, snapshots[sym])

        self._final_flatten(order, bars_by_symbol)
        self.report.halted_reason = self.governor.state.halted_reason
        self.report.next_session_multiplier = self.governor.next_session_multiplier()
        return self.report

    # ------------------------------------------------------------------
    # Bar processing
    # ------------------------------------------------------------------
    def _on_bar(self, symbol: str, bar: Bar, snapshot) -> None:
        history = self._history.setdefault(symbol, [])
        history.append(bar)

        if self._position is not None and self._position.symbol == symbol:
            self._manage_position(bar)

        if self._position is None:
            if self._armed is not None and self._armed.symbol == symbol:
                self._handle_armed(bar, snapshot)
            elif self._armed is None:
                self._try_arm(symbol, bar, snapshot, history)

    # ------------------------------------------------------------------
    # Arming
    # ------------------------------------------------------------------
    def _try_arm(self, symbol: str, bar: Bar, snapshot, history: list[Bar]) -> None:
        ok, reason = self.governor.can_enter(bar.ts, open_positions=0)
        if not ok:
            return  # outside window / halted / caps — silent: expected, frequent

        if symbol not in self._orb_armed and len(history) == 1:
            self._orb_armed.add(symbol)
            signal = detect_opening_range_breakout(
                symbol, history, self.cfg, premarket_high=snapshot.premarket_high
            )
        else:
            signal = detect_intraday(symbol, history, self.cfg)
        if signal is None:
            return

        ok, reason = self.governor.validate_signal(signal)
        if not ok:
            self._skip(bar.ts, symbol, "validate", reason)
            return
        self._armed, self._armed_age = signal, 0

    def _handle_armed(self, bar: Bar, snapshot) -> None:
        signal = self._armed
        assert signal is not None
        self._armed_age += 1
        if self._armed_age > self.cfg.signal_ttl_bars:
            self._disarm()
            return

        if bar.high < signal.entry:
            return  # not triggered yet

        # G4: never chase a bar that gapped past the trigger.
        if bar.open > signal.entry * (1 + self.cfg.chase_tolerance_pct / 100.0):
            self._skip(bar.ts, signal.symbol, "chase_guard", "bar opened beyond trigger tolerance")
            self._disarm()
            return

        ok, reason = self.governor.can_enter(bar.ts, open_positions=0)
        if not ok:
            self._skip(bar.ts, signal.symbol, "entry_gate", reason)
            self._disarm()
            return

        history = self._history[signal.symbol]
        shares = self.governor.size(signal, history[:-1], snapshot.float_shares)
        if shares <= 0:
            self._skip(bar.ts, signal.symbol, "sizing", "participation/risk caps left no size")
            self._disarm()
            return

        slip = self.cfg.slippage_ticks * TICK
        fill_price = round(max(signal.entry, bar.open) + slip, 4)
        self._position = Position(
            symbol=signal.symbol,
            setup=signal.setup,
            shares=shares,
            entry_price=fill_price,
            stop=signal.stop,
            first_target=round(fill_price + self.cfg.min_reward_risk * (fill_price - signal.stop), 4),
            opened_at=bar.ts,
            initial_risk_per_share=fill_price - signal.stop,
            high_water=fill_price,
        )
        self._record = TradeRecord(
            symbol=signal.symbol,
            setup=signal.setup,
            shares=shares,
            entry_price=fill_price,
            opened_at=bar.ts,
        )
        self.governor.on_trade_opened()
        self._disarm()

    def _disarm(self) -> None:
        self._armed, self._armed_age = None, 0

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------
    def _manage_position(self, bar: Bar) -> None:
        pos = self._position
        assert pos is not None
        cfg = self.cfg
        slip = cfg.slippage_ticks * TICK

        # G1: circuit breaker tripped while in a position → flatten first.
        if self.governor.state.halted:
            self._exit_all(bar.open, ExitReason.DAILY_MAX_LOSS, bar.ts)
            return
        # G7: hard flat time — never hold into the close/overnight.
        if bar.ts.time() >= cfg.flatten_by:
            self._exit_all(bar.open, ExitReason.TIME_FLATTEN, bar.ts)
            return

        # Protective stop (pessimistic: checked before targets).
        if bar.open <= pos.stop or bar.low <= pos.stop:
            price = min(pos.stop, bar.open) - slip
            reason = ExitReason.TRAIL if pos.scaled else ExitReason.STOP
            self._exit_all(price, reason, bar.ts)
            return

        # First target: sell half into strength, stop to breakeven (G2:
        # the trade pays for itself before it is allowed to run).
        if not pos.scaled and bar.high >= pos.first_target:
            price = max(pos.first_target, bar.open)
            half = pos.shares // 2
            if half == 0:
                self._exit_all(price, ExitReason.FIRST_TARGET_SCALE, bar.ts)
                return
            self._fill(half, price, ExitReason.FIRST_TARGET_SCALE, bar.ts)
            pos.shares -= half
            pos.scaled = True
            new_stop = max(pos.stop, pos.entry_price)
            assert RiskGovernor.validate_stop_move(pos.stop, new_stop)
            pos.stop = new_stop

        pos.bars_held += 1
        pos.high_water = max(pos.high_water, bar.high)

        # G-disposition: winners run, but dead trades don't get to marinate.
        if not pos.scaled and pos.bars_held >= cfg.stall_exit_bars:
            self._exit_all(bar.close, ExitReason.STALL, bar.ts)
            return

        # Bar-low trail once scaled: stops only ratchet upward (G2).
        if pos.scaled:
            new_stop = max(pos.stop, bar.low)
            assert RiskGovernor.validate_stop_move(pos.stop, new_stop)
            pos.stop = new_stop

    def _fill(self, shares: int, price: float, reason: ExitReason, ts: datetime) -> None:
        assert self._record is not None
        self._record.fills.append(Fill(shares=shares, price=round(price, 4), reason=reason, ts=ts))

    def _exit_all(self, price: float, reason: ExitReason, ts: datetime) -> None:
        pos = self._position
        assert pos is not None and self._record is not None
        self._fill(pos.shares, price, reason, ts)
        record = self._record
        self._position, self._record = None, None
        self.governor.on_trade_closed(record)
        self.report.trades.append(record)

    def _final_flatten(self, order: list[str], bars_by_symbol: dict[str, list[Bar]]) -> None:
        if self._position is None:
            return
        bars = bars_by_symbol.get(self._position.symbol, [])
        if bars:
            last = bars[-1]
            self._exit_all(last.close, ExitReason.TIME_FLATTEN, last.ts)

    def _skip(self, ts: datetime, symbol: str, stage: str, reason: str) -> None:
        self.report.skips.append(
            {"ts": ts.isoformat(), "symbol": symbol, "stage": stage, "reason": reason}
        )
