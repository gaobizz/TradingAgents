"""Ross Cameron-style small-cap momentum strategy (research/paper only).

A deterministic, autonomously-executable draft of the strategy documented
in docs/research/ross-cameron-strategy.md, with the retail failure-mode
guardrails from docs/research/why-retail-traders-lose.md encoded as hard
rules. See docs/strategy/cameron-autonomous-execution-spec.md for the
full specification and the G1..G8 guardrail table.

This package simulates decisions over bar data. It does not connect to a
broker, and nothing in it is financial advice.
"""

from .catalyst import (
    CatalystGrade,
    grade_catalyst,
    grade_headline,
    make_llm_grader,
    meets_minimum_grade,
)
from .config import CameronConfig, DEFAULT_CONFIG
from .engine import CameronEngine, SessionReport
from .models import (
    Bar,
    ExitReason,
    Fill,
    GapperSnapshot,
    Position,
    ScreenResult,
    SetupType,
    Signal,
    TradeRecord,
)
from .risk import RiskGovernor, SessionRiskState
from .screener import build_watchlist, screen_snapshot
from .setups import (
    detect_bull_flag,
    detect_flat_top,
    detect_intraday,
    detect_micro_pullback,
    detect_opening_range_breakout,
)

__all__ = [
    "Bar",
    "CameronConfig",
    "CameronEngine",
    "CatalystGrade",
    "DEFAULT_CONFIG",
    "ExitReason",
    "Fill",
    "GapperSnapshot",
    "Position",
    "RiskGovernor",
    "ScreenResult",
    "SessionReport",
    "SessionRiskState",
    "SetupType",
    "Signal",
    "TradeRecord",
    "build_watchlist",
    "detect_bull_flag",
    "detect_flat_top",
    "detect_intraday",
    "detect_micro_pullback",
    "detect_opening_range_breakout",
    "grade_catalyst",
    "grade_headline",
    "make_llm_grader",
    "meets_minimum_grade",
    "screen_snapshot",
]
