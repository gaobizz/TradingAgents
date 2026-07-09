"""Five Pillars pre-market screen.

Implements the stock-selection layer of the strategy: a deterministic
filter that reduces the gapper scan to the handful of names where an
outsized intraday move is structurally possible. A snapshot must pass
every pillar; the result records exactly which pillars failed so the
decision is auditable after the fact.
"""

from __future__ import annotations

from .catalyst import meets_minimum_grade
from .config import CameronConfig
from .models import GapperSnapshot, ScreenResult

PILLAR_PRICE = "price_band"
PILLAR_DAY_CHANGE = "day_change"
PILLAR_RELATIVE_VOLUME = "relative_volume"
PILLAR_FLOAT = "float"
PILLAR_CATALYST = "catalyst"
CHECK_GAP = "gap"
CHECK_DILUTION = "dilution_risk"
CHECK_HALTED = "halted"


def screen_snapshot(snapshot: GapperSnapshot, cfg: CameronConfig) -> ScreenResult:
    """Evaluate one scanner snapshot against the Five Pillars + guardrails."""
    failed: list[str] = []

    if not cfg.min_price <= snapshot.price <= cfg.max_price:
        failed.append(PILLAR_PRICE)
    if snapshot.day_change_pct < cfg.min_day_change_pct:
        failed.append(PILLAR_DAY_CHANGE)
    if snapshot.relative_volume < cfg.min_relative_volume:
        failed.append(PILLAR_RELATIVE_VOLUME)
    if snapshot.float_shares <= 0 or snapshot.float_shares > cfg.max_float_shares:
        failed.append(PILLAR_FLOAT)
    if cfg.require_catalyst:
        # Graded path (catalyst.py) when a grade is present; legacy boolean
        # otherwise. A veto grade ("F") always fails here as well as in the
        # dilution check below.
        if snapshot.catalyst_grade:
            if not meets_minimum_grade(snapshot.catalyst_grade, cfg.min_catalyst_grade):
                failed.append(PILLAR_CATALYST)
        elif not snapshot.has_news_catalyst:
            failed.append(PILLAR_CATALYST)
    if snapshot.gap_pct < cfg.min_gap_pct:
        failed.append(CHECK_GAP)
    # G6: refuse candidates where the issuer is positioned to sell the spike.
    if cfg.block_dilution_flagged and snapshot.dilution_flags:
        failed.append(CHECK_DILUTION)
    if snapshot.halted:
        failed.append(CHECK_HALTED)

    return ScreenResult(snapshot=snapshot, passed=not failed, failed_pillars=tuple(failed))


def build_watchlist(
    snapshots: list[GapperSnapshot], cfg: CameronConfig
) -> tuple[list[ScreenResult], list[ScreenResult]]:
    """Screen all snapshots; return (watchlist, rejected).

    The watchlist is ranked by relative volume (the strongest evidence of
    abnormal demand) and truncated to ``max_watchlist_size`` so the engine
    focuses on A+ candidates only (G3: scarcity over activity).
    """
    results = [screen_snapshot(s, cfg) for s in snapshots]
    accepted = [r for r in results if r.passed]
    rejected = [r for r in results if not r.passed]
    accepted.sort(key=lambda r: r.snapshot.relative_volume, reverse=True)
    return accepted[: cfg.max_watchlist_size], rejected
