"""End-to-end: fetch odds, filter date, merge ratings, rank picks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bigdance.config import (
    WEIGHTS,
    get_target_date,
    get_timezone,
    ratings_csv_path,
)
from bigdance.fetch_odds import FetchResult, fetch_ncaab_odds, filter_events_by_date
from bigdance.model_ats import (
    build_game_pick,
    game_pick_to_dict,
    spread_market_devig_home_covers,
)
from bigdance.normalize import load_aliases
from bigdance.ratings import expected_margin_home, load_ratings_table


def run_picks_pipeline(
    date_str: str | None = None,
    tz: str | None = None,
) -> dict[str, Any]:
    date_str = date_str or get_target_date()
    tz = tz or get_timezone()

    fr: FetchResult = fetch_ncaab_odds()
    now = datetime.now(timezone.utc)
    generated = now.isoformat().replace("+00:00", "Z")

    meta: dict[str, Any] = {
        "generated_at": generated,
        "target_date": date_str,
        "timezone": tz,
        "weights": {
            "w_market": WEIGHTS.w_market,
            "w_ratings": WEIGHTS.w_ratings,
            "sigma_game": WEIGHTS.sigma_game,
            "home_court_points": WEIGHTS.home_court_points,
            "efficiency_to_margin": WEIGHTS.efficiency_to_margin,
        },
        "remaining_requests": fr.remaining_requests,
        "error": fr.error,
        "source": "the-odds-api",
    }

    if fr.error and not fr.events:
        return {"meta": meta, "picks": [], "events_considered": 0}

    events = filter_events_by_date(fr.events, date_str, tz)
    meta["events_on_date"] = len(events)

    ratings = load_ratings_table()
    meta["ratings_file"] = str(ratings_csv_path())
    meta["ratings_loaded"] = not ratings.empty

    aliases = load_aliases()
    picks_raw: list[Any] = []

    for event in events:
        p_market, _ = spread_market_devig_home_covers(event)
        home = event.get("home_team") or ""
        away = event.get("away_team") or ""
        mu, ratings_ok = expected_margin_home(
            home,
            away,
            ratings,
            aliases,
            WEIGHTS.home_court_points,
            WEIGHTS.efficiency_to_margin,
        )
        gp = build_game_pick(event, p_market, mu, ratings_ok)
        if gp.pick_team and gp.confidence is not None:
            picks_raw.append(gp)

    picks_raw.sort(
        key=lambda g: (g.confidence if g.confidence is not None else -1.0),
        reverse=True,
    )

    picks = [game_pick_to_dict(g, rank=i + 1) for i, g in enumerate(picks_raw)]

    return {
        "meta": meta,
        "picks": picks,
        "events_considered": len(events),
    }
