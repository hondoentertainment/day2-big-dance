"""Fetch NCAAB odds from The Odds API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

from bigdance.config import get_odds_api_key, get_target_date, get_timezone

ODDS_BASE = "https://api.the-odds-api.com/v4"
SPORT_KEY = "basketball_ncaab"


@dataclass
class FetchResult:
    events: list[dict[str, Any]]
    remaining_requests: int | None
    error: str | None


def fetch_ncaab_odds() -> FetchResult:
    key = get_odds_api_key()
    if not key:
        return FetchResult(
            events=[],
            remaining_requests=None,
            error="Missing ODDS_API_KEY. Set it in .env or the environment.",
        )
    url = f"{ODDS_BASE}/sports/{SPORT_KEY}/odds"
    params = {
        "apiKey": key,
        "regions": "us",
        "markets": "spreads",
        "oddsFormat": "american",
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        return FetchResult(
            events=[],
            remaining_requests=None,
            error=f"Odds API request failed: {e}",
        )
    remaining = r.headers.get("x-requests-remaining")
    rem = int(remaining) if remaining and remaining.isdigit() else None
    try:
        data = r.json()
    except ValueError:
        return FetchResult(events=[], remaining_requests=rem, error="Invalid JSON from Odds API")
    if not isinstance(data, list):
        return FetchResult(events=[], remaining_requests=rem, error="Unexpected Odds API payload")
    return FetchResult(events=data, remaining_requests=rem, error=None)


def event_on_local_date(event: dict[str, Any], date_str: str, tz_name: str) -> bool:
    """True if commence_time falls on date_str in tz_name (YYYY-MM-DD)."""
    raw = event.get("commence_time")
    if not raw:
        return False
    try:
        # API uses ISO Z
        if raw.endswith("Z"):
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(raw)
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    local = dt.astimezone(ZoneInfo(tz_name))
    return local.strftime("%Y-%m-%d") == date_str


def filter_events_by_date(
    events: list[dict[str, Any]],
    date_str: str | None = None,
    tz_name: str | None = None,
) -> list[dict[str, Any]]:
    d = date_str or get_target_date()
    tz = tz_name or get_timezone()
    return [e for e in events if event_on_local_date(e, d, tz)]
