"""Polygon.io historical data adapter for the replay harness.

Provides exactly the five queries the replay needs — grouped daily bars
(gapper discovery), 1-minute bars (pre-market snapshot + session replay),
daily bars (30-day average volume), ticker overview (shares outstanding
as a float proxy), and ticker news (catalyst flag).

Design notes:
- Responses are cached as JSON under the cache dir (default
  ``~/.tradingagents/cache/polygon``) keyed by endpoint+params, so a
  replay re-run costs zero API calls. Historical data is immutable, so
  the cache never expires.
- The free Polygon tier allows 5 requests/minute; pass
  ``throttle_seconds=12.5`` to stay under it. Paid tiers can leave the
  default of 0.
- All timestamps are converted from Polygon's UTC epoch-milliseconds to
  naive US/Eastern datetimes, which is what the engine expects.
- Float caveat: Polygon exposes shares outstanding, not free float. The
  proxy overstates float, which biases the Five Pillars screen toward
  *rejecting* candidates — the conservative direction — but real float
  data (and dilution flags) remain an open item in the execution spec.
"""

from __future__ import annotations

import hashlib
import json
import os
import time as time_module
from datetime import date as date_type
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import Bar

_BASE_URL = "https://api.polygon.io"
_EASTERN = ZoneInfo("America/New_York")


class PolygonError(RuntimeError):
    """Raised when Polygon returns an error or the API key is missing."""


def _to_eastern(epoch_ms: int) -> datetime:
    utc = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
    return utc.astimezone(_EASTERN).replace(tzinfo=None)


class PolygonClient:
    """Thin, cached REST client for the endpoints the replay uses."""

    def __init__(
        self,
        api_key: str | None = None,
        cache_dir: str | Path | None = None,
        session=None,
        max_retries: int = 3,
        throttle_seconds: float = 0.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("POLYGON_API_KEY", "")
        if not self.api_key:
            raise PolygonError(
                "POLYGON_API_KEY is not set (pass api_key= or export the env var)"
            )
        default_cache = Path.home() / ".tradingagents" / "cache" / "polygon"
        self.cache_dir = Path(cache_dir) if cache_dir else default_cache
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if session is None:
            import requests  # deferred so tests can inject a fake session

            session = requests.Session()
        self._session = session
        self.max_retries = max_retries
        self.throttle_seconds = throttle_seconds

    # ------------------------------------------------------------------
    # Transport with cache + retry
    # ------------------------------------------------------------------
    def _cache_path(self, path: str, params: dict) -> Path:
        key_material = path + "?" + json.dumps(params, sort_keys=True)
        digest = hashlib.sha256(key_material.encode()).hexdigest()[:32]
        return self.cache_dir / f"{digest}.json"

    def _get(self, path: str, params: dict | None = None) -> dict:
        params = dict(params or {})
        cache_file = self._cache_path(path, params)
        if cache_file.exists():
            return json.loads(cache_file.read_text())

        params["apiKey"] = self.api_key
        delay = 2.0
        for attempt in range(self.max_retries + 1):
            if self.throttle_seconds:
                time_module.sleep(self.throttle_seconds)
            response = self._session.get(_BASE_URL + path, params=params, timeout=30)
            if response.status_code == 200:
                payload = response.json()
                cache_file.write_text(json.dumps(payload))
                return payload
            if response.status_code in (429, 500, 502, 503) and attempt < self.max_retries:
                time_module.sleep(delay)
                delay *= 2
                continue
            raise PolygonError(f"GET {path} failed: HTTP {response.status_code}")
        raise PolygonError(f"GET {path} failed after {self.max_retries} retries")

    # ------------------------------------------------------------------
    # Endpoints
    # ------------------------------------------------------------------
    def grouped_daily(self, day: date_type) -> dict[str, dict]:
        """All US stocks' daily OHLCV for one date. Empty dict on closed days."""
        payload = self._get(
            f"/v2/aggs/grouped/locale/us/market/stocks/{day.isoformat()}",
            {"adjusted": "true"},
        )
        return {
            row["T"]: {
                "open": row.get("o"),
                "high": row.get("h"),
                "low": row.get("l"),
                "close": row.get("c"),
                "volume": row.get("v", 0),
            }
            for row in payload.get("results") or []
            if row.get("T")
        }

    def minute_bars(self, symbol: str, day: date_type) -> list[Bar]:
        """1-minute bars for one symbol/date, extended hours included."""
        payload = self._get(
            f"/v2/aggs/ticker/{symbol}/range/1/minute/{day.isoformat()}/{day.isoformat()}",
            {"adjusted": "true", "sort": "asc", "limit": 50_000},
        )
        return [
            Bar(
                ts=_to_eastern(row["t"]),
                open=row["o"],
                high=row["h"],
                low=row["l"],
                close=row["c"],
                volume=int(row.get("v", 0)),
            )
            for row in payload.get("results") or []
        ]

    def daily_bars(self, symbol: str, start: date_type, end: date_type) -> list[dict]:
        payload = self._get(
            f"/v2/aggs/ticker/{symbol}/range/1/day/{start.isoformat()}/{end.isoformat()}",
            {"adjusted": "true", "sort": "asc", "limit": 500},
        )
        return [
            {"ts": _to_eastern(row["t"]), "volume": int(row.get("v", 0)), "close": row["c"]}
            for row in payload.get("results") or []
        ]

    def shares_outstanding(self, symbol: str) -> int:
        """Shares outstanding as a float proxy (see module docstring caveat)."""
        payload = self._get(f"/v3/reference/tickers/{symbol}", {})
        results = payload.get("results") or {}
        shares = (
            results.get("weighted_shares_outstanding")
            or results.get("share_class_shares_outstanding")
            or 0
        )
        return int(shares)

    def news_headlines(
        self, symbol: str, published_gte: datetime, published_lte: datetime
    ) -> list[str]:
        """Headlines for the catalyst window, oldest first."""
        payload = self._get(
            "/v2/reference/news",
            {
                "ticker": symbol,
                "published_utc.gte": published_gte.astimezone(timezone.utc).isoformat(),
                "published_utc.lte": published_lte.astimezone(timezone.utc).isoformat(),
                "order": "asc",
                "limit": 20,
            },
        )
        return [row.get("title", "") for row in payload.get("results") or [] if row.get("title")]


def premarket_window(day: date_type) -> tuple[datetime, datetime]:
    """Catalyst lookback: prior day 16:00 ET through scan time 09:25 ET."""
    from datetime import timedelta

    end = datetime.combine(day, time(9, 25), tzinfo=_EASTERN)
    start = datetime.combine(day - timedelta(days=1), time(16, 0), tzinfo=_EASTERN)
    return start, end
