"""Tests for the historical replay harness (fixture-driven, no network).

Covers gapper discovery from grouped daily data, point-in-time snapshot
construction (pre-market only, no lookahead), single-session replay, and
multi-day replay with equity compounding and the G1 size-down carryover
chained across sessions.
"""

import dataclasses

import pytest
from datetime import date, datetime, timedelta

from tradingagents.strategies.ross_cameron import Bar, CameronConfig
from tradingagents.strategies.ross_cameron.replay import (
    build_snapshot,
    discover_candidates,
    previous_trading_day,
    replay_range,
    replay_session,
)

CFG = CameronConfig()

DAY1 = date(2026, 7, 8)   # stop-out session
DAY2 = date(2026, 7, 9)   # winning session
DAY0 = date(2026, 7, 7)   # prior close reference


def bar_on(day, hour, minute, o, h, l, c, v=50_000):
    return Bar(
        ts=datetime(day.year, day.month, day.day, hour, minute),
        open=o, high=h, low=l, close=c, volume=v,
    )


def premarket_bars(day):
    return [
        bar_on(day, 9, 0, 4.60, 4.80, 4.55, 4.75, v=2_000_000),
        bar_on(day, 9, 10, 4.75, 5.20, 4.70, 4.95, v=2_500_000),
        bar_on(day, 9, 20, 4.95, 5.05, 4.90, 5.00, v=1_500_000),
    ]


WINNING_RTH = [
    (9, 30, 5.00, 5.10, 4.95, 5.05),
    (9, 31, 5.10, 5.25, 5.08, 5.22),   # entry fills 5.22
    (9, 32, 5.30, 5.80, 5.28, 5.75),   # scale half at 5.76
    (9, 33, 5.70, 5.85, 5.50, 5.60),
    (9, 34, 5.55, 5.60, 5.45, 5.50),   # trail out 5.49
]

LOSING_RTH = [
    (9, 30, 5.00, 5.10, 4.95, 5.05),
    (9, 31, 5.10, 5.25, 5.08, 5.22),   # entry fills 5.22
    (9, 32, 4.93, 4.94, 4.80, 4.82),   # opens through stop → out 4.92
]


class FakeClient:
    """Duck-typed stand-in for PolygonClient, fed from dict fixtures."""

    def __init__(self):
        self.grouped = {}   # date -> {symbol: {open, close, volume}}
        self.minutes = {}   # (symbol, date) -> [Bar]
        self.dailies = {}   # symbol -> [ {volume, ...} ]
        self.shares = {}    # symbol -> int
        self.news = {}      # symbol -> [headline]

    def grouped_daily(self, day):
        return self.grouped.get(day, {})

    def minute_bars(self, symbol, day):
        return self.minutes.get((symbol, day), [])

    def daily_bars(self, symbol, start, end):
        return self.dailies.get(symbol, [])

    def shares_outstanding(self, symbol):
        return self.shares.get(symbol, 0)

    def news_headlines(self, symbol, published_gte, published_lte):
        # Published two hours before the window end (i.e. fresh at scan time).
        published = published_lte.replace(tzinfo=None) - timedelta(hours=2)
        return [(title, published) for title in self.news.get(symbol, [])]


def grouped_row(open_, close, volume=6_000_000):
    return {"open": open_, "high": open_, "low": open_, "close": close, "volume": volume}


def make_client():
    client = FakeClient()
    client.grouped[DAY0] = {"TEST": grouped_row(4.00, 4.00)}
    client.grouped[DAY1] = {"TEST": grouped_row(5.00, 4.00)}
    client.grouped[DAY2] = {"TEST": grouped_row(5.00, 5.49)}
    for day, rth in ((DAY1, LOSING_RTH), (DAY2, WINNING_RTH)):
        client.minutes[("TEST", day)] = premarket_bars(day) + [
            bar_on(day, *spec) for spec in rth
        ]
    client.dailies["TEST"] = [{"volume": 1_000_000} for _ in range(30)]
    client.shares["TEST"] = 15_000_000
    client.news["TEST"] = ["FDA grants approval for lead candidate"]
    return client


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
class TestDiscovery:
    def test_previous_trading_day_skips_closed_days(self):
        client = make_client()   # DAY1 (7/8) present, 7/7 present
        assert previous_trading_day(client, DAY2) == DAY1
        del client.grouped[DAY1]
        assert previous_trading_day(client, DAY2) == DAY0

    def test_discover_filters_and_ranks(self):
        client = make_client()
        client.grouped[DAY0].update(
            {
                "BIGGAP": grouped_row(6.00, 4.00),
                "LOWV": grouped_row(6.00, 4.00),
                "SMALLGAP": grouped_row(4.08, 4.00),
                "PRICEY": grouped_row(40.0, 30.0),
            }
        )
        client.grouped[DAY1].update(
            {
                "BIGGAP": grouped_row(6.00, 6.10),                  # +50% gap
                "LOWV": grouped_row(6.00, 6.10, volume=100_000),    # too thin
                "SMALLGAP": grouped_row(4.08, 4.10),                # +2% gap
                "PRICEY": grouped_row(40.0, 41.0),                  # out of band
            }
        )
        pairs = discover_candidates(client, DAY1, CFG)
        symbols = [s for s, _ in pairs]
        assert symbols == ["BIGGAP", "TEST"]  # ranked by gap %, junk filtered
        assert dict(pairs)["TEST"] == 4.00

    def test_closed_market_returns_no_candidates(self):
        assert discover_candidates(make_client(), date(2026, 7, 11), CFG) == []


# ---------------------------------------------------------------------------
# Snapshot construction (point-in-time)
# ---------------------------------------------------------------------------
class TestSnapshot:
    def test_snapshot_from_premarket_only(self):
        client = make_client()
        snap = build_snapshot(client, "TEST", DAY2, prev_close=4.00, cfg=CFG)
        assert snap is not None
        assert snap.price == 5.00                      # last pre-market print
        assert snap.premarket_high == 5.20
        assert snap.day_volume == 6_000_000            # pre-market cumulative
        assert snap.avg_daily_volume_30d == 1_000_000
        assert snap.relative_volume == 6.0
        assert snap.day_change_pct == 25.0
        assert snap.has_news_catalyst
        assert snap.catalyst_grade == "A"              # fresh FDA approval
        assert snap.float_shares == 15_000_000

    def test_offering_news_vetoes_and_flags_dilution(self):
        client = make_client()
        client.news["TEST"] = ["Company prices $10 million public offering"]
        snap = build_snapshot(client, "TEST", DAY2, prev_close=4.00, cfg=CFG)
        assert snap.catalyst_grade == "F"
        assert snap.dilution_flags == ("news:dilution_offering",)

    def test_no_premarket_tape_means_no_snapshot(self):
        client = make_client()
        client.minutes[("TEST", DAY2)] = [bar_on(DAY2, *spec) for spec in WINNING_RTH]
        assert build_snapshot(client, "TEST", DAY2, 4.00, CFG) is None


# ---------------------------------------------------------------------------
# Session and range replay
# ---------------------------------------------------------------------------
class TestReplay:
    def test_single_session_trades_the_gapper(self):
        client = make_client()
        report, watchlist = replay_session(client, DAY2, CFG, equity=30_000)
        assert watchlist == ["TEST"]
        assert len(report.trades) == 1
        assert report.trades[0].pnl > 0
        assert report.metrics()["win_rate"] == 1.0

    def test_range_chains_carryover_and_compounds_equity(self):
        # Breaker at $90 (0.3%), matching per-trade risk so one full-risk
        # stop-out trips it (config requires max loss >= one full-risk trade).
        cfg = dataclasses.replace(CFG, daily_max_loss_pct=0.3, risk_per_trade_pct=0.3)
        client = make_client()
        result = replay_range(client, DAY1, DAY2, cfg, equity=30_000)

        assert [s["date"] for s in result.sessions] == ["2026-07-08", "2026-07-09"]
        day1, day2 = result.sessions
        # Day 1: $90 risk / $0.26 signal risk → 346 shares; -$0.30/share
        # (slippage both sides) = -$103.80 trips the breaker.
        assert day1["trades"][0]["shares"] == 346
        assert day1["halted"]
        # Day 2 runs at half risk on the *compounded* equity of $29,896.20
        # (carryover 0.5 → $44.84 risk → 172 shares, not 346).
        assert day2["carryover_multiplier"] == 0.5
        assert day2["trades"][0]["shares"] == 172

        metrics = result.metrics()
        assert metrics["sessions"] == 2
        assert metrics["trades"] == 2
        assert metrics["max_loss_days"] == 1
        assert metrics["win_rate"] == 0.5
        expected_net = round(-103.80 + (86 * 0.54 + 86 * 0.27), 2)
        assert metrics["net_pnl"] == pytest.approx(expected_net, abs=0.01)
        assert result.equity_curve == pytest.approx(
            [30_000 - 103.80, 30_000 + expected_net], abs=0.01
        )

    def test_weekend_days_are_skipped(self):
        client = make_client()
        result = replay_range(client, date(2026, 7, 11), date(2026, 7, 12), CFG, 30_000)
        assert result.sessions == []
