"""Tests for the Ross Cameron momentum strategy module.

Covers the Five Pillars screener, the setup detectors, the risk governor's
guardrails (sizing caps, daily circuit breaker, rehab size-down, stop
monotonicity), and the session engine end-to-end on synthetic bars.
"""

import dataclasses
from datetime import datetime, time

import pytest

from tradingagents.strategies.ross_cameron import (
    Bar,
    CameronConfig,
    CameronEngine,
    ExitReason,
    GapperSnapshot,
    RiskGovernor,
    SetupType,
    Signal,
    build_watchlist,
    detect_bull_flag,
    detect_flat_top,
    detect_micro_pullback,
    detect_opening_range_breakout,
    screen_snapshot,
)

CFG = CameronConfig()


def ts(hour, minute):
    return datetime(2026, 7, 9, hour, minute)


def bar(hour, minute, o, h, l, c, v=50_000):
    return Bar(ts=ts(hour, minute), open=o, high=h, low=l, close=c, volume=v)


def good_snapshot(**overrides):
    base = dict(
        symbol="TEST",
        price=5.0,
        prev_close=4.0,
        day_change_pct=25.0,
        gap_pct=25.0,
        premarket_high=5.20,
        avg_daily_volume_30d=1_000_000,
        day_volume=6_000_000,
        float_shares=15_000_000,
        has_news_catalyst=True,
    )
    base.update(overrides)
    return GapperSnapshot(**base)


# ---------------------------------------------------------------------------
# Screener: the Five Pillars
# ---------------------------------------------------------------------------
class TestScreener:
    def test_passes_all_pillars(self):
        result = screen_snapshot(good_snapshot(), CFG)
        assert result.passed
        assert result.failed_pillars == ()

    @pytest.mark.parametrize(
        "overrides,expected",
        [
            ({"price": 25.0}, "price_band"),
            ({"price": 0.80}, "price_band"),
            ({"day_change_pct": 5.0}, "day_change"),
            ({"day_volume": 2_000_000}, "relative_volume"),
            ({"float_shares": 100_000_000}, "float"),
            ({"has_news_catalyst": False}, "catalyst"),
            ({"gap_pct": 2.0}, "gap"),
            ({"dilution_flags": ("S-3 shelf",)}, "dilution_risk"),
            ({"halted": True}, "halted"),
        ],
    )
    def test_each_pillar_fails_individually(self, overrides, expected):
        result = screen_snapshot(good_snapshot(**overrides), CFG)
        assert not result.passed
        assert expected in result.failed_pillars

    def test_dilution_block_can_be_disabled(self):
        cfg = dataclasses.replace(CFG, block_dilution_flagged=False)
        result = screen_snapshot(good_snapshot(dilution_flags=("active ATM",)), cfg)
        assert result.passed

    def test_watchlist_ranked_by_relative_volume_and_truncated(self):
        snaps = [
            good_snapshot(symbol=f"S{i}", day_volume=(i + 6) * 1_000_000)
            for i in range(7)
        ]
        snaps.append(good_snapshot(symbol="BAD", has_news_catalyst=False))
        watchlist, rejected = build_watchlist(snaps, CFG)
        assert len(watchlist) == CFG.max_watchlist_size
        assert [r.symbol for r in watchlist] == ["S6", "S5", "S4", "S3", "S2"]
        assert any(r.symbol == "BAD" for r in rejected)


# ---------------------------------------------------------------------------
# Setup detectors
# ---------------------------------------------------------------------------
class TestSetups:
    def test_opening_range_breakout_uses_first_bar(self):
        bars = [bar(9, 30, 5.00, 5.10, 4.95, 5.05)]
        signal = detect_opening_range_breakout("TEST", bars, CFG)
        assert signal is not None
        assert signal.setup is SetupType.OPENING_RANGE_BREAKOUT
        assert signal.entry == pytest.approx(5.11)
        assert signal.stop == pytest.approx(4.95)

    def test_opening_range_breakout_prefers_higher_premarket_high(self):
        bars = [bar(9, 30, 5.00, 5.10, 4.95, 5.05)]
        signal = detect_opening_range_breakout("TEST", bars, CFG, premarket_high=5.20)
        assert signal.entry == pytest.approx(5.21)

    def test_bull_flag_detected(self):
        bars = [
            bar(9, 31, 1.00, 1.05, 0.99, 1.05),
            bar(9, 32, 1.05, 1.12, 1.04, 1.12),
            bar(9, 33, 1.12, 1.20, 1.11, 1.20),
            bar(9, 34, 1.20, 1.21, 1.15, 1.16),
            bar(9, 35, 1.16, 1.17, 1.13, 1.14),
        ]
        signal = detect_bull_flag("TEST", bars, CFG)
        assert signal is not None
        assert signal.setup is SetupType.BULL_FLAG
        assert signal.entry == pytest.approx(1.18)
        assert signal.stop == pytest.approx(1.13)

    def test_bull_flag_rejects_deep_retrace(self):
        bars = [
            bar(9, 31, 1.00, 1.05, 0.99, 1.05),
            bar(9, 32, 1.05, 1.12, 1.04, 1.12),
            bar(9, 33, 1.12, 1.20, 1.11, 1.20),
            bar(9, 34, 1.20, 1.21, 1.08, 1.09),   # gives back most of the pole
            bar(9, 35, 1.09, 1.10, 1.05, 1.06),
        ]
        assert detect_bull_flag("TEST", bars, CFG) is None

    def test_micro_pullback_detected(self):
        bars = [
            bar(9, 31, 1.00, 1.02, 0.99, 1.01),
            bar(9, 32, 1.01, 1.10, 1.00, 1.09),   # impulse: green, local high
            bar(9, 33, 1.09, 1.09, 1.06, 1.07),   # tight 1-bar pause
        ]
        signal = detect_micro_pullback("TEST", bars, CFG)
        assert signal is not None
        assert signal.setup is SetupType.MICRO_PULLBACK
        assert signal.entry == pytest.approx(1.10)
        assert signal.stop == pytest.approx(1.06)

    def test_micro_pullback_rejects_deep_pause(self):
        bars = [
            bar(9, 31, 1.00, 1.02, 0.99, 1.01),
            bar(9, 32, 1.01, 1.10, 1.00, 1.09),
            bar(9, 33, 1.09, 1.09, 1.02, 1.03),   # pause below impulse midpoint
        ]
        assert detect_micro_pullback("TEST", bars, CFG) is None

    def test_flat_top_detected(self):
        bars = [
            bar(9, 31, 1.96, 2.000, 1.95, 1.98),
            bar(9, 32, 1.98, 1.999, 1.96, 1.99),
            bar(9, 33, 1.99, 2.000, 1.96, 1.98),
            bar(9, 34, 1.98, 1.998, 1.97, 1.98),
            bar(9, 35, 1.98, 2.000, 1.97, 1.99),
            bar(9, 36, 1.99, 1.999, 1.97, 1.98),
        ]
        signal = detect_flat_top("TEST", bars, CFG)
        assert signal is not None
        assert signal.setup is SetupType.FLAT_TOP_BREAKOUT
        assert signal.entry == pytest.approx(2.01)
        assert signal.stop == pytest.approx(1.95)

    def test_wide_stop_rejected_everywhere(self):
        # First bar with a 10% range: ORB stop would exceed max_stop_distance_pct.
        bars = [bar(9, 30, 5.00, 5.20, 4.70, 5.10)]
        assert detect_opening_range_breakout("TEST", bars, CFG) is None


# ---------------------------------------------------------------------------
# Risk governor
# ---------------------------------------------------------------------------
def make_signal(entry=5.00, stop=4.85):
    return Signal(
        symbol="TEST", setup=SetupType.BULL_FLAG, entry=entry, stop=stop, armed_at=ts(9, 35)
    )


def losing_record(pnl_per_share=-0.20, shares=500):
    from tradingagents.strategies.ross_cameron import Fill, TradeRecord

    record = TradeRecord(
        symbol="TEST",
        setup=SetupType.BULL_FLAG,
        shares=shares,
        entry_price=5.00,
        opened_at=ts(9, 40),
    )
    record.fills.append(
        Fill(shares=shares, price=5.00 + pnl_per_share, reason=ExitReason.STOP, ts=ts(9, 45))
    )
    return record


class TestRiskGovernor:
    def test_sizing_fixed_dollar_risk(self):
        gov = RiskGovernor(CFG, equity=30_000)
        # 0.5% of 30k = $150 risk; $0.15/share risk → 1000 shares.
        shares = gov.size(make_signal(), recent_bars=[], float_shares=15_000_000)
        assert shares == 1000

    def test_sizing_participation_cap(self):
        gov = RiskGovernor(CFG, equity=30_000)
        thin = [bar(9, 40 + i, 5, 5.1, 4.9, 5, v=1_000) for i in range(5)]
        shares = gov.size(make_signal(), recent_bars=thin, float_shares=15_000_000)
        assert shares == 200  # 20% of 1k average 1-min volume

    def test_daily_max_loss_halts_session(self):
        gov = RiskGovernor(CFG, equity=30_000)  # breaker at -$450
        gov.on_trade_closed(losing_record(pnl_per_share=-1.00, shares=500))  # -$500
        assert gov.state.halted
        ok, reason = gov.can_enter(ts(9, 50), open_positions=0)
        assert not ok and "halted" in reason
        assert gov.next_session_multiplier() == CFG.next_day_after_max_loss_multiplier

    def test_rehab_size_down_after_consecutive_losses(self):
        gov = RiskGovernor(CFG, equity=100_000)
        assert gov.risk_multiplier() == 1.0
        for _ in range(3):
            gov.on_trade_closed(losing_record(shares=100))
        assert gov.risk_multiplier() == CFG.rehab_risk_multiplier

    def test_entry_window_enforced(self):
        gov = RiskGovernor(CFG, equity=30_000)
        ok, reason = gov.can_enter(ts(12, 0), open_positions=0)
        assert not ok and "G7" in reason
        ok, _ = gov.can_enter(ts(9, 45), open_positions=0)
        assert ok

    def test_stop_moves_are_monotonic(self):
        assert RiskGovernor.validate_stop_move(5.00, 5.10)
        assert RiskGovernor.validate_stop_move(5.00, 5.00)
        assert not RiskGovernor.validate_stop_move(5.00, 4.90)

    def test_invalid_config_fails_loudly(self):
        with pytest.raises(ValueError, match="G2"):
            RiskGovernor(dataclasses.replace(CFG, min_reward_risk=0.5), equity=30_000)
        with pytest.raises(ValueError, match="G1"):
            RiskGovernor(dataclasses.replace(CFG, risk_per_trade_pct=5.0), equity=30_000)


# ---------------------------------------------------------------------------
# Engine end-to-end (synthetic sessions)
# ---------------------------------------------------------------------------
def run_engine(bars, snapshot=None, cfg=CFG, equity=30_000.0):
    snapshot = snapshot or good_snapshot()
    watchlist, _ = build_watchlist([snapshot], cfg)
    engine = CameronEngine(cfg=cfg, equity=equity)
    report = engine.run_session(watchlist, {snapshot.symbol: bars})
    return report


HAPPY_PATH_BARS = [
    bar(9, 30, 5.00, 5.10, 4.95, 5.05),   # ORB armed: entry 5.21 (PM high), stop 4.95
    bar(9, 31, 5.10, 5.25, 5.08, 5.22),   # triggers → fill 5.22 (+1 tick slippage)
    bar(9, 32, 5.30, 5.80, 5.28, 5.75),   # first target 5.76 hit → scale half, BE stop
    bar(9, 33, 5.70, 5.85, 5.50, 5.60),   # trail ratchets to 5.50
    bar(9, 34, 5.55, 5.60, 5.45, 5.50),   # trail stop 5.50 hit → exit rest at 5.49
]


class TestEngine:
    def test_happy_path_scale_and_trail(self):
        report = run_engine(HAPPY_PATH_BARS)
        assert len(report.trades) == 1
        trade = report.trades[0]
        assert trade.setup is SetupType.OPENING_RANGE_BREAKOUT
        assert trade.entry_price == pytest.approx(5.22)
        reasons = [f.reason for f in trade.fills]
        assert reasons == [ExitReason.FIRST_TARGET_SCALE, ExitReason.TRAIL]
        # Sized off the armed signal risk (5.21-4.95=0.26): $150 → 576 shares.
        # Half scaled at 5.76 (+0.54 vs 5.22 fill), rest trailed out at 5.49 (+0.27).
        assert trade.shares == 576
        assert trade.pnl == pytest.approx(288 * 0.54 + 288 * 0.27, abs=0.01)
        assert report.metrics()["win_rate"] == 1.0

    def test_stop_loss_exit(self):
        bars = [
            bar(9, 30, 5.00, 5.10, 4.95, 5.05),
            bar(9, 31, 5.10, 5.25, 5.08, 5.22),   # entry 5.22
            bar(9, 32, 4.93, 4.94, 4.80, 4.82),   # opens through stop 4.95
        ]
        report = run_engine(bars)
        assert len(report.trades) == 1
        trade = report.trades[0]
        assert trade.fills[0].reason is ExitReason.STOP
        assert trade.fills[0].price == pytest.approx(4.92)  # open - slippage
        assert trade.pnl < 0

    def test_chase_guard_skips_gapped_trigger(self):
        bars = [
            bar(9, 30, 5.00, 5.10, 4.95, 5.05),
            bar(9, 31, 5.40, 5.60, 5.35, 5.55),   # opens 3.6% past 5.21 trigger
        ]
        report = run_engine(bars)
        assert report.trades == []
        assert any(s["stage"] == "chase_guard" for s in report.skips)

    def test_stall_exit_frees_dead_capital(self):
        cfg = dataclasses.replace(CFG, stall_exit_bars=3)
        bars = [
            bar(9, 30, 5.00, 5.10, 4.95, 5.05),
            bar(9, 31, 5.10, 5.25, 5.08, 5.22),           # entry 5.22
            bar(9, 32, 5.20, 5.30, 5.15, 5.20),           # held 1
            bar(9, 33, 5.20, 5.28, 5.12, 5.18),           # held 2
            bar(9, 34, 5.18, 5.25, 5.10, 5.15),           # held 3 → stall exit
        ]
        report = run_engine(bars, cfg=cfg)
        assert len(report.trades) == 1
        assert report.trades[0].fills[-1].reason is ExitReason.STALL

    def test_flatten_by_close(self):
        cfg = dataclasses.replace(
            CFG, no_entries_after=time(15, 54), flatten_by=time(15, 55)
        )
        bars = [
            bar(15, 50, 5.00, 5.10, 4.95, 5.05),
            bar(15, 51, 5.10, 5.25, 5.08, 5.22),   # entry
            bar(15, 52, 5.22, 5.30, 5.18, 5.25),
            bar(15, 55, 5.25, 5.30, 5.20, 5.28),   # flatten at open
        ]
        report = run_engine(bars, cfg=cfg)
        assert len(report.trades) == 1
        assert report.trades[0].fills[-1].reason is ExitReason.TIME_FLATTEN

    def test_no_entries_without_qualifying_watchlist(self):
        report = run_engine(HAPPY_PATH_BARS, snapshot=good_snapshot(has_news_catalyst=False))
        assert report.trades == []

    def test_deterministic_replay(self):
        first = run_engine(HAPPY_PATH_BARS).metrics()
        second = run_engine(HAPPY_PATH_BARS).metrics()
        assert first == second
