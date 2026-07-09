"""Data models for the Ross Cameron momentum strategy engine.

All models are plain dataclasses so the engine stays deterministic,
dependency-free, and easy to unit test. Times are naive datetimes assumed
to be US/Eastern (the session the strategy trades).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


@dataclass(frozen=True)
class Bar:
    """One OHLCV bar (the engine is designed for 1-minute bars)."""

    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class GapperSnapshot:
    """Pre-market scanner snapshot for one candidate symbol.

    Field semantics follow the research docs (docs/research/): the Five
    Pillars are evaluated against this snapshot, and the dilution flags
    implement the "who is on the other side" guardrail (G6).
    """

    symbol: str
    price: float
    prev_close: float
    day_change_pct: float           # % change vs prior close at scan time
    gap_pct: float                  # opening/pre-market gap vs prior close
    premarket_high: float
    avg_daily_volume_30d: int
    day_volume: int                 # cumulative volume at scan time
    float_shares: int
    has_news_catalyst: bool
    catalyst_headline: str = ""
    dilution_flags: tuple[str, ...] = ()   # e.g. ("S-3 shelf", "active ATM")
    halted: bool = False

    @property
    def relative_volume(self) -> float:
        if self.avg_daily_volume_30d <= 0:
            return 0.0
        return self.day_volume / self.avg_daily_volume_30d


@dataclass(frozen=True)
class ScreenResult:
    """Outcome of the Five Pillars screen for one snapshot."""

    snapshot: GapperSnapshot
    passed: bool
    failed_pillars: tuple[str, ...] = ()

    @property
    def symbol(self) -> str:
        return self.snapshot.symbol


class SetupType(str, Enum):
    OPENING_RANGE_BREAKOUT = "opening_range_breakout"
    BULL_FLAG = "bull_flag"
    MICRO_PULLBACK = "micro_pullback"
    FLAT_TOP_BREAKOUT = "flat_top_breakout"


@dataclass(frozen=True)
class Signal:
    """An armed (not yet triggered) entry order proposal.

    ``entry`` is a stop-buy trigger; the engine only fills when the market
    trades through it (G4: entries happen at planned triggers, never by
    chasing an extended move).
    """

    symbol: str
    setup: SetupType
    entry: float
    stop: float
    armed_at: datetime

    @property
    def risk_per_share(self) -> float:
        return self.entry - self.stop

    def first_target(self, reward_risk: float) -> float:
        return self.entry + reward_risk * self.risk_per_share


class ExitReason(str, Enum):
    STOP = "stop"
    FIRST_TARGET_SCALE = "first_target_scale"
    TRAIL = "trail"
    TIME_FLATTEN = "time_flatten"
    STALL = "stall"
    HALT = "halt"
    DAILY_MAX_LOSS = "daily_max_loss"


@dataclass
class Position:
    symbol: str
    setup: SetupType
    shares: int
    entry_price: float
    stop: float
    first_target: float
    opened_at: datetime
    initial_risk_per_share: float
    scaled: bool = False            # True once half was sold at first target
    bars_held: int = 0
    high_water: float = 0.0

    def r_multiple(self, price: float) -> float:
        if self.initial_risk_per_share <= 0:
            return 0.0
        return (price - self.entry_price) / self.initial_risk_per_share


@dataclass(frozen=True)
class Fill:
    """One realized exit (a position can close across several fills)."""

    shares: int
    price: float
    reason: ExitReason
    ts: datetime


@dataclass
class TradeRecord:
    """A completed round trip, possibly closed via multiple fills."""

    symbol: str
    setup: SetupType
    shares: int
    entry_price: float
    opened_at: datetime
    fills: list[Fill] = field(default_factory=list)

    @property
    def closed_shares(self) -> int:
        return sum(f.shares for f in self.fills)

    @property
    def pnl(self) -> float:
        return sum((f.price - self.entry_price) * f.shares for f in self.fills)

    @property
    def closed_at(self) -> Optional[datetime]:
        return self.fills[-1].ts if self.fills else None

    @property
    def is_winner(self) -> bool:
        return self.pnl > 0
