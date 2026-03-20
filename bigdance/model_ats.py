"""Consensus spread, de-vig, P(cover), blend, confidence."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any

from bigdance.config import WEIGHTS


def american_to_implied_prob(american: int | float) -> float:
    o = float(american)
    if o > 0:
        return 100.0 / (o + 100.0)
    return abs(o) / (abs(o) + 100.0)


def devig_two_way(p_a_raw: float, p_b_raw: float) -> tuple[float, float]:
    s = p_a_raw + p_b_raw
    if s <= 0:
        return 0.5, 0.5
    return p_a_raw / s, p_b_raw / s


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def median_spread_from_books(
    event: dict[str, Any],
) -> tuple[list[float], list[tuple[str, int, int | float]]]:
    """
    Collect home spread points from each book's spreads market.
    Returns (list of home spread points, list of (book_key, home_price, home_point)).
    """
    home = event.get("home_team")
    away = event.get("away_team")
    if not home or not away:
        return [], []
    points: list[float] = []
    detail: list[tuple[str, int, int | float]] = []
    for bm in event.get("bookmakers") or []:
        key = bm.get("key", "")
        for m in bm.get("markets") or []:
            if m.get("key") != "spreads":
                continue
            home_pt = None
            home_px = None
            away_pt = None
            away_px = None
            for o in m.get("outcomes") or []:
                name = o.get("name")
                pt = o.get("point")
                px = o.get("price")
                if pt is None or px is None:
                    continue
                if name == home:
                    home_pt = float(pt)
                    home_px = int(px)
                elif name == away:
                    away_pt = float(pt)
                    away_px = int(px)
            if home_pt is not None and home_px is not None:
                points.append(home_pt)
                detail.append((key, home_px, home_pt))
            break
    return points, detail


def spread_market_devig_home_covers(
    event: dict[str, Any],
) -> tuple[float | None, int]:
    """
    Average fair P(home covers) across books that have both sides priced.
    """
    home = event.get("home_team")
    away = event.get("away_team")
    if not home or not away:
        return None, 0
    probs: list[float] = []
    for bm in event.get("bookmakers") or []:
        for m in bm.get("markets") or []:
            if m.get("key") != "spreads":
                continue
            h_raw = a_raw = None
            for o in m.get("outcomes") or []:
                name = o.get("name")
                px = o.get("price")
                if px is None:
                    continue
                ip = american_to_implied_prob(int(px))
                if name == home:
                    h_raw = ip
                elif name == away:
                    a_raw = ip
            if h_raw is not None and a_raw is not None:
                fh, _ = devig_two_way(h_raw, a_raw)
                probs.append(fh)
            break
    if not probs:
        return None, 0
    return sum(probs) / len(probs), len(probs)


def iqr(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    xs = sorted(values)
    n = len(xs)
    def q(p: float) -> float:
        idx = p * (n - 1)
        lo = int(math.floor(idx))
        hi = int(math.ceil(idx))
        if lo == hi:
            return xs[lo]
        return xs[lo] + (xs[hi] - xs[lo]) * (idx - lo)
    return q(0.75) - q(0.25)


@dataclass
class GamePick:
    game_id: str
    commence_time: str | None
    home_team: str
    away_team: str
    consensus_home_spread: float | None
    n_books_spread: int
    spread_iqr: float
    p_market: float | None
    p_model: float | None
    p_blend: float | None
    pick_team: str | None
    pick_role: str | None
    line_display: str | None
    confidence: float | None
    ratings_ok: bool
    edge_vs_even: float | None
    notes: str


def build_game_pick(
    event: dict[str, Any],
    p_market: float | None,
    mu_home: float | None,
    ratings_ok: bool,
    w: Any = WEIGHTS,
) -> GamePick:
    gid = str(event.get("id", ""))
    home = event.get("home_team") or ""
    away = event.get("away_team") or ""
    commence = event.get("commence_time")

    pts, _ = median_spread_from_books(event)
    s_h: float | None
    if pts:
        s_h = float(statistics.median(pts))
    else:
        s_h = None
    n_books = len(pts)
    spread_iqr = iqr(pts) if pts else 0.0

    p_model_val: float | None = None
    if mu_home is not None and s_h is not None and w.sigma_game > 0:
        z = (mu_home + s_h) / w.sigma_game
        p_model_val = norm_cdf(z)

    wm, wr = w.w_market, w.w_ratings
    if not ratings_ok or p_model_val is None:
        wm, wr = 1.0, 0.0

    ratings_used = bool(ratings_ok and p_model_val is not None)

    p_blend: float | None = None
    if p_market is not None and s_h is not None:
        if wr > 0 and p_model_val is not None:
            raw = wm * p_market + wr * p_model_val
        else:
            raw = p_market
        p_blend = max(w.p_blend_floor, min(w.p_blend_ceiling, raw))
    elif p_model_val is not None:
        p_blend = max(w.p_blend_floor, min(w.p_blend_ceiling, p_model_val))

    pick_team = pick_role = line_display = None
    confidence = None
    edge_vs_even = None

    if p_blend is not None and s_h is not None:
        take_home = p_blend >= 0.5
        pick_team = home if take_home else away
        pick_role = "home" if take_home else "away"
        pt = s_h if take_home else -s_h
        sign = "+" if pt > 0 else ""
        line_display = f"{pick_team} {sign}{pt:g}"
        base = abs(p_blend - 0.5)
        m_n = min(1.0, n_books / w.books_full_weight_at) if w.books_full_weight_at else 1.0
        m_disp = 1.0 / (1.0 + w.dispersion_coef * spread_iqr) if spread_iqr >= 0 else 1.0
        m_r = 1.0 if ratings_used else w.missing_ratings_multiplier
        confidence = base * m_n * m_disp * m_r
        edge_vs_even = p_blend - 0.5 if take_home else 0.5 - p_blend

    notes_parts: list[str] = []
    if n_books:
        notes_parts.append(f"{n_books} books")
    if spread_iqr >= 1.5:
        notes_parts.append("wide line dispersion")
    if not ratings_used:
        notes_parts.append("market-only (no ratings merge)")

    return GamePick(
        game_id=gid,
        commence_time=commence if isinstance(commence, str) else None,
        home_team=home,
        away_team=away,
        consensus_home_spread=s_h,
        n_books_spread=n_books,
        spread_iqr=spread_iqr,
        p_market=p_market,
        p_model=p_model_val,
        p_blend=p_blend,
        pick_team=pick_team,
        pick_role=pick_role,
        line_display=line_display,
        confidence=confidence,
        ratings_ok=ratings_used,
        edge_vs_even=edge_vs_even,
        notes=", ".join(notes_parts),
    )


def game_pick_to_dict(g: GamePick, rank: int | None = None) -> dict[str, Any]:
    d: dict[str, Any] = {
        "game_id": g.game_id,
        "commence_time": g.commence_time,
        "home_team": g.home_team,
        "away_team": g.away_team,
        "consensus_home_spread": g.consensus_home_spread,
        "n_books_spread": g.n_books_spread,
        "spread_iqr": round(g.spread_iqr, 3),
        "p_market": round(g.p_market, 4) if g.p_market is not None else None,
        "p_model": round(g.p_model, 4) if g.p_model is not None else None,
        "p_blend": round(g.p_blend, 4) if g.p_blend is not None else None,
        "pick_team": g.pick_team,
        "pick_role": g.pick_role,
        "line_display": g.line_display,
        "confidence": round(g.confidence, 4) if g.confidence is not None else None,
        "confidence_pct": round(g.confidence * 200, 1) if g.confidence is not None else None,
        "ratings_ok": g.ratings_ok,
        "edge_vs_even": round(g.edge_vs_even, 4) if g.edge_vs_even is not None else None,
        "notes": g.notes,
    }
    if rank is not None:
        d["rank"] = rank
    return d
