"""Setup detectors: the strategy's entry patterns as exact bar logic.

Each detector inspects a chronological list of 1-minute bars and either
arms a :class:`Signal` (a stop-buy trigger with a structure stop) or
returns ``None``. The detectors deliberately replace the discretionary
parts of the taught strategy (tape reading, "does it look clean?") with
mechanical definitions — an autonomous system must not pretend to have
judgment it doesn't have. The exact definitions are documented in
docs/strategy/cameron-autonomous-execution-spec.md and are the single
source of truth for these functions.

Shared invariants enforced here:
- entry trigger is strictly above the stop (long-only, defined risk),
- stop distance is capped at ``max_stop_distance_pct`` of the entry
  (a wide stop cannot be "made up for" with a distant target — G2),
- prices are rounded to cents.
"""

from __future__ import annotations

from .config import CameronConfig
from .models import Bar, SetupType, Signal

TICK = 0.01


def _round(price: float) -> float:
    return round(price + 1e-9, 2)


def _finalize(
    symbol: str,
    setup: SetupType,
    entry: float,
    stop: float,
    bars: list[Bar],
    cfg: CameronConfig,
) -> Signal | None:
    entry, stop = _round(entry), _round(stop)
    risk = entry - stop
    if risk <= 0:
        return None
    if risk / entry * 100.0 > cfg.max_stop_distance_pct:
        return None
    return Signal(symbol=symbol, setup=setup, entry=entry, stop=stop, armed_at=bars[-1].ts)


def detect_opening_range_breakout(
    symbol: str, bars: list[Bar], cfg: CameronConfig, premarket_high: float | None = None
) -> Signal | None:
    """Gap-and-Go: buy the break of the first 1-minute candle's high.

    Armed off the completed first bar of the session; the trigger is that
    bar's high (or the pre-market high when it sits above it), the stop is
    the first bar's low.
    """
    if not bars:
        return None
    first = bars[0]
    entry = first.high + TICK
    if premarket_high is not None and premarket_high > first.high:
        entry = premarket_high + TICK
    return _finalize(symbol, SetupType.OPENING_RANGE_BREAKOUT, entry, first.low, bars, cfg)


def _trailing_run(bars: list[Bar], predicate) -> int:
    """Length of the run of bars satisfying ``predicate`` at the end of the list."""
    n = 0
    for bar in reversed(bars):
        if predicate(bar):
            n += 1
        else:
            break
    return n


def detect_bull_flag(symbol: str, bars: list[Bar], cfg: CameronConfig) -> Signal | None:
    """Bull flag: pole of >=2 green bars, pullback of 2-3 red bars.

    Entry is the first candle to make a new high after the pullback —
    armed as a stop-buy one tick above the last pullback bar's high, with
    the stop at the low of the pullback. The pullback must retrace less
    than ``flag_max_retrace`` of the pole and must not undercut the pole
    low (a pullback that gives the whole pole back is a failed move, not
    a flag).
    """
    pull_len = _trailing_run(bars, lambda b: b.close < b.open)
    if not cfg.flag_min_pullback_bars <= pull_len <= cfg.flag_max_pullback_bars:
        return None
    body = bars[: len(bars) - pull_len]
    pole_len = _trailing_run(body, lambda b: b.close > b.open)
    if pole_len < 2:
        return None

    pole = body[len(body) - pole_len :]
    pullback = bars[len(bars) - pull_len :]
    pole_low = min(b.low for b in pole)
    pole_high = max(b.high for b in pole)
    pole_height = pole_high - pole_low
    if pole_height <= 0:
        return None
    pullback_low = min(b.low for b in pullback)
    retrace = pole_high - pullback_low
    if retrace <= 0 or retrace > cfg.flag_max_retrace * pole_height:
        return None
    if pullback_low <= pole_low:
        return None

    entry = pullback[-1].high + TICK
    return _finalize(symbol, SetupType.BULL_FLAG, entry, pullback_low, bars, cfg)


def detect_micro_pullback(symbol: str, bars: list[Bar], cfg: CameronConfig) -> Signal | None:
    """Micro pullback: a 1-3 bar pause immediately after an impulse bar.

    Requirements: the impulse bar is green and makes the local high of the
    lookback window; the pause bars stop making new highs but hold above
    the impulse bar's midpoint (tight, early-stage — not a deep flag).
    Entry is one tick above the pause high; stop is the pause low.
    """
    min_bars = cfg.micro_min_pause_bars + 2
    if len(bars) < min_bars:
        return None

    for pause_len in range(cfg.micro_min_pause_bars, cfg.micro_max_pause_bars + 1):
        if len(bars) < pause_len + 1:
            break
        impulse = bars[len(bars) - pause_len - 1]
        pause = bars[len(bars) - pause_len :]
        if impulse.close <= impulse.open:
            continue
        lookback = bars[max(0, len(bars) - pause_len - 10) : len(bars) - pause_len]
        if impulse.high < max(b.high for b in lookback):
            continue
        if any(b.high > impulse.high for b in pause):
            continue
        midpoint = (impulse.high + impulse.low) / 2
        pause_low = min(b.low for b in pause)
        if pause_low < midpoint:
            continue
        entry = max(b.high for b in pause) + TICK
        return _finalize(symbol, SetupType.MICRO_PULLBACK, entry, pause_low, bars, cfg)
    return None


def detect_flat_top(symbol: str, bars: list[Bar], cfg: CameronConfig) -> Signal | None:
    """Flat-top breakout: repeated tests of one resistance with rising lows.

    Looks at the trailing 6-bar window: at least ``flat_top_min_touches``
    bars whose highs sit within ``flat_top_tolerance_pct`` of the window
    high, and the low of the window's second half above the low of its
    first half. Entry is one tick above the resistance; stop is the
    window low.
    """
    window = bars[-6:]
    if len(window) < cfg.flat_top_min_touches + 1:
        return None
    resistance = max(b.high for b in window)
    tolerance = resistance * cfg.flat_top_tolerance_pct / 100.0
    touches = sum(1 for b in window if resistance - b.high <= tolerance)
    if touches < cfg.flat_top_min_touches:
        return None
    half = len(window) // 2
    first_low = min(b.low for b in window[:half])
    second_low = min(b.low for b in window[half:])
    if second_low <= first_low:
        return None
    return _finalize(
        symbol, SetupType.FLAT_TOP_BREAKOUT, resistance + TICK, min(b.low for b in window), bars, cfg
    )


# Detector priority: at the open the ORB is armed once; afterwards the
# tighter/earlier-stage patterns take precedence over the broader ones.
INTRADAY_DETECTORS = (
    detect_micro_pullback,
    detect_bull_flag,
    detect_flat_top,
)


def detect_intraday(symbol: str, bars: list[Bar], cfg: CameronConfig) -> Signal | None:
    """Run intraday detectors in priority order; first match wins."""
    for detector in INTRADAY_DETECTORS:
        signal = detector(symbol, bars, cfg)
        if signal is not None:
            return signal
    return None
