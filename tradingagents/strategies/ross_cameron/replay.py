"""Historical replay harness: run the engine over real gapper days.

This is the sim gate from the execution spec (§10): replay sessions over
historical 1-minute data with the pessimistic fill model and aggregate
net-of-cost results. The harness is point-in-time honest — the 09:25
snapshot is built only from pre-market bars and information available
before the open (no lookahead into the session being traded).

The ``client`` is duck-typed (see ``polygon_data.PolygonClient`` for the
reference implementation) so tests can inject fixtures and other vendors
can be adapted later. Run from the CLI:

    python -m tradingagents.strategies.ross_cameron.replay --date 2026-07-08
    python -m tradingagents.strategies.ross_cameron.replay \
        --start 2026-06-01 --end 2026-06-30 --equity 30000 --json out.json

Requires POLYGON_API_KEY. On the free tier pass --throttle 12.5 (5
requests/minute); results are cached so re-runs are free.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import datetime, time, timedelta

from .config import CameronConfig, DEFAULT_CONFIG
from .engine import CameronEngine, SessionReport
from .models import Bar, GapperSnapshot
from .screener import build_watchlist

SCAN_TIME = time(9, 25)
RTH_START = time(9, 30)
RTH_END = time(16, 0)


# ---------------------------------------------------------------------------
# Candidate discovery (which symbols would the gap scanner have shown?)
# ---------------------------------------------------------------------------
def previous_trading_day(client, day: date_type, max_lookback: int = 7) -> date_type | None:
    """Walk back until grouped daily data exists (skips weekends/holidays)."""
    probe = day - timedelta(days=1)
    for _ in range(max_lookback):
        if client.grouped_daily(probe):
            return probe
        probe -= timedelta(days=1)
    return None


def discover_candidates(
    client, day: date_type, cfg: CameronConfig, max_candidates: int = 30
) -> list[tuple[str, float]]:
    """Symbols that gapped up on ``day``, with their prior closes.

    Uses grouped daily bars for the date and its previous trading day.
    The gap filter here is deliberately looser than the Five Pillars
    (price band widened, no float/news yet) — it reproduces the raw
    scanner output; the real screen happens in ``build_watchlist``.
    """
    today = client.grouped_daily(day)
    if not today:
        return []  # market closed
    prev_day = previous_trading_day(client, day)
    if prev_day is None:
        return []
    prev = client.grouped_daily(prev_day)

    candidates: list[tuple[str, float, float]] = []
    for symbol, row in today.items():
        prior = prev.get(symbol)
        if not prior or not prior.get("close") or not row.get("open"):
            continue
        prev_close = prior["close"]
        gap_pct = (row["open"] / prev_close - 1.0) * 100.0
        if gap_pct < cfg.min_gap_pct:
            continue
        if not cfg.min_price <= row["open"] <= cfg.max_price * 1.5:
            continue
        if row.get("volume", 0) < 500_000:
            continue  # untradeable junk regardless of gap
        candidates.append((symbol, prev_close, gap_pct))

    candidates.sort(key=lambda c: c[2], reverse=True)
    return [(symbol, prev_close) for symbol, prev_close, _ in candidates[:max_candidates]]


# ---------------------------------------------------------------------------
# Point-in-time snapshot (what the 09:25 scanner would have shown)
# ---------------------------------------------------------------------------
def build_snapshot(
    client,
    symbol: str,
    day: date_type,
    prev_close: float,
    cfg: CameronConfig,
    grader=None,
) -> GapperSnapshot | None:
    """Point-in-time 09:25 snapshot. ``grader`` defaults to the deterministic
    catalyst grader; pass ``catalyst.make_llm_grader(model)`` to upgrade."""
    bars = client.minute_bars(symbol, day)
    scan_bars = [b for b in bars if b.ts.time() < SCAN_TIME]
    if not scan_bars or prev_close <= 0:
        return None  # no pre-market tape → the scanner would not have shown it

    last = scan_bars[-1].close
    pm_high = max(b.high for b in scan_bars)
    pm_volume = sum(b.volume for b in scan_bars)
    change_pct = (last / prev_close - 1.0) * 100.0

    lookback = client.daily_bars(symbol, day - timedelta(days=45), day - timedelta(days=1))
    recent = lookback[-30:]
    avg_volume = int(sum(d["volume"] for d in recent) / len(recent)) if recent else 0

    from .catalyst import VETO_CATEGORIES, grade_catalyst
    from .polygon_data import premarket_window

    news_start, news_end = premarket_window(day)
    headlines = client.news_headlines(symbol, news_start, news_end)
    scan_dt = datetime.combine(day, SCAN_TIME)
    grade = (grader or grade_catalyst)(headlines, scan_dt)

    # A news veto (offering/reverse split/going concern) doubles as a
    # dilution flag — partial G6 coverage until an EDGAR feed exists.
    dilution_flags = (f"news:{grade.category}",) if grade.category in VETO_CATEGORIES else ()

    return GapperSnapshot(
        symbol=symbol,
        price=last,
        prev_close=prev_close,
        day_change_pct=change_pct,
        gap_pct=change_pct,           # point-in-time: pre-market price vs prior close
        premarket_high=pm_high,
        avg_daily_volume_30d=avg_volume,
        day_volume=pm_volume,         # pre-market cumulative volume only (honest)
        float_shares=client.shares_outstanding(symbol),
        has_news_catalyst=bool(headlines),
        catalyst_headline=grade.headline or (headlines[0][0] if headlines else ""),
        catalyst_grade=grade.grade,
        dilution_flags=dilution_flags,
    )


def rth_bars(bars: list[Bar]) -> list[Bar]:
    return [b for b in bars if RTH_START <= b.ts.time() < RTH_END]


# ---------------------------------------------------------------------------
# Session and range replay
# ---------------------------------------------------------------------------
def replay_session(
    client,
    day: date_type,
    cfg: CameronConfig = DEFAULT_CONFIG,
    equity: float = 30_000.0,
    carryover_multiplier: float = 1.0,
    symbols: list[tuple[str, float]] | None = None,
    grader=None,
) -> tuple[SessionReport, list[str]]:
    """Replay one session; returns the report and the watchlist symbols."""
    pairs = symbols if symbols is not None else discover_candidates(client, day, cfg)
    snapshots = []
    for symbol, prev_close in pairs:
        snapshot = build_snapshot(client, symbol, day, prev_close, cfg, grader=grader)
        if snapshot is not None:
            snapshots.append(snapshot)

    watchlist, _ = build_watchlist(snapshots, cfg)
    bars_by_symbol = {
        r.symbol: rth_bars(client.minute_bars(r.symbol, day)) for r in watchlist
    }
    bars_by_symbol = {s: b for s, b in bars_by_symbol.items() if b}
    watchlist = [r for r in watchlist if r.symbol in bars_by_symbol]

    engine = CameronEngine(cfg=cfg, equity=equity, carryover_multiplier=carryover_multiplier)
    report = engine.run_session(watchlist, bars_by_symbol)
    return report, [r.symbol for r in watchlist]


@dataclass
class RangeResult:
    """Aggregate of a multi-day replay — the sim-gate scoreboard."""

    equity_start: float
    sessions: list[dict] = field(default_factory=list)   # per-day summaries
    equity_curve: list[float] = field(default_factory=list)

    @property
    def equity_end(self) -> float:
        return self.equity_curve[-1] if self.equity_curve else self.equity_start

    def max_drawdown_pct(self) -> float:
        peak, worst = self.equity_start, 0.0
        for value in self.equity_curve:
            peak = max(peak, value)
            worst = max(worst, (peak - value) / peak * 100.0)
        return round(worst, 2)

    def metrics(self) -> dict:
        trades = [t for s in self.sessions for t in s["trades"]]
        wins = [t["pnl"] for t in trades if t["pnl"] > 0]
        losses = [t["pnl"] for t in trades if t["pnl"] < 0]
        gross_win, gross_loss = sum(wins), -sum(losses)
        return {
            "sessions": len(self.sessions),
            "sessions_traded": sum(1 for s in self.sessions if s["trades"]),
            "trades": len(trades),
            "net_pnl": round(self.equity_end - self.equity_start, 2),
            "return_pct": round((self.equity_end / self.equity_start - 1) * 100.0, 2),
            "win_rate": round(len(wins) / len(trades), 4) if trades else 0.0,
            "profit_factor": round(gross_win / gross_loss, 3) if gross_loss else None,
            "max_drawdown_pct": self.max_drawdown_pct(),
            "max_loss_days": sum(1 for s in self.sessions if s["halted"]),
        }


def _session_summary(day: date_type, report: SessionReport, watchlist: list[str], carryover: float) -> dict:
    return {
        "date": day.isoformat(),
        "watchlist": watchlist,
        "carryover_multiplier": carryover,
        "trades": [
            {
                "symbol": t.symbol,
                "setup": t.setup.value,
                "shares": t.shares,
                "entry": t.entry_price,
                "pnl": round(t.pnl, 2),
                "exits": [f.reason.value for f in t.fills],
            }
            for t in report.trades
        ],
        "net_pnl": round(report.realized_pnl, 2),
        "halted": report.halted_reason,
        "skips": report.skips,
    }


def replay_range(
    client,
    start: date_type,
    end: date_type,
    cfg: CameronConfig = DEFAULT_CONFIG,
    equity: float = 30_000.0,
    grader=None,
) -> RangeResult:
    """Replay every trading day in [start, end], compounding equity and
    chaining the G1 size-down carryover across sessions."""
    result = RangeResult(equity_start=equity)
    carryover = 1.0
    day = start
    while day <= end:
        if day.weekday() < 5:
            report, watchlist = replay_session(
                client, day, cfg, equity=equity, carryover_multiplier=carryover,
                grader=grader,
            )
            # Distinguish "market closed" (no candidates, no bars) from a
            # traded-but-flat day: only record days the market was open.
            if watchlist or client.grouped_daily(day):
                result.sessions.append(_session_summary(day, report, watchlist, carryover))
                equity += report.realized_pnl
                result.equity_curve.append(equity)
                carryover = report.next_session_multiplier
        day += timedelta(days=1)
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay the Cameron momentum engine over Polygon data")
    parser.add_argument("--date", help="single session date (YYYY-MM-DD)")
    parser.add_argument("--start", help="range start (YYYY-MM-DD)")
    parser.add_argument("--end", help="range end (YYYY-MM-DD)")
    parser.add_argument("--equity", type=float, default=30_000.0)
    parser.add_argument("--symbols", help="comma-separated symbols to force (skips discovery)")
    parser.add_argument("--throttle", type=float, default=0.0, help="seconds between API calls (free tier: 12.5)")
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--json", dest="json_out", default=None, help="write full results to this path")
    args = parser.parse_args(argv)

    if not args.date and not (args.start and args.end):
        parser.error("provide --date, or --start and --end")

    try:
        from .polygon_data import PolygonClient, PolygonError
    except ImportError as exc:
        print(f"error: missing dependency ({exc}); run: pip install requests")
        return 1

    try:
        client = PolygonClient(cache_dir=args.cache_dir, throttle_seconds=args.throttle)
    except PolygonError as exc:
        print(f"error: {exc}")
        print("get a key at https://polygon.io, then: export POLYGON_API_KEY=<your key>")
        return 1
    cfg = DEFAULT_CONFIG

    try:
        if args.date:
            day = date_type.fromisoformat(args.date)
            symbols = None
            if args.symbols:
                prev_day = previous_trading_day(client, day)
                prev = client.grouped_daily(prev_day) if prev_day else {}
                symbols = [
                    (s, prev[s]["close"]) for s in args.symbols.split(",") if s in prev
                ]
            report, watchlist = replay_session(client, day, cfg, equity=args.equity, symbols=symbols)
            payload = _session_summary(day, report, watchlist, 1.0) | {"metrics": report.metrics()}
        else:
            result = replay_range(
                client, date_type.fromisoformat(args.start), date_type.fromisoformat(args.end),
                cfg, equity=args.equity,
            )
            payload = {"metrics": result.metrics(), "sessions": result.sessions}
            for session in result.sessions:
                print(
                    f"{session['date']}  watchlist={len(session['watchlist']):>2}  "
                    f"trades={len(session['trades']):>2}  pnl={session['net_pnl']:>+10.2f}"
                    f"{'  [MAX LOSS]' if session['halted'] else ''}"
                )
    except PolygonError as exc:
        print(f"error: {exc}")
        print("(HTTP 401/403 usually means a wrong key or a plan without this data; "
              "429 means rate limit — add --throttle 12.5 on the free tier)")
        return 1

    print(json.dumps(payload.get("metrics", {}), indent=2))
    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(payload, fh, indent=2, default=str)
        print(f"full results written to {args.json_out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
