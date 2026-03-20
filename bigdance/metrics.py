"""Postgame grading: ATS hit rate, Brier, ROI at -110."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


def american_payout_profit(american: int = -110) -> float:
    """Profit per 1u risked on a win (not including stake return)."""
    if american < 0:
        return 100.0 / abs(american)
    return american / 100.0


@dataclass
class GradeSummary:
    n: int
    wins: int
    losses: int
    pushes: int
    hit_rate: float | None
    brier: float | None
    units_profit_flat_1u: float | None


def grade_ats_row(
    margin_home: float,
    consensus_home_spread: float,
    pick_role: str,
) -> str:
    """
    margin_home = home_score - away_score.
    consensus_home_spread: home line (negative = favorite).
    """
    adj = margin_home + consensus_home_spread
    if abs(adj) < 1e-9:
        return "push"
    home_covers = adj > 0
    if pick_role == "home":
        return "win" if home_covers else "loss"
    if pick_role == "away":
        return "win" if not home_covers else "loss"
    return "unknown"


def summarize_grades(rows: list[dict[str, Any]], american: int = -110) -> GradeSummary:
    wins = losses = pushes = 0
    brier_sum = 0.0
    brier_n = 0
    units = 0.0
    for r in rows:
        res = r.get("result")
        if res == "win":
            wins += 1
            units += american_payout_profit(american)
        elif res == "loss":
            losses += 1
            units -= 1.0
        elif res == "push":
            pushes += 1
        pb = r.get("p_blend")
        if pb is not None and res in ("win", "loss"):
            y = 1.0 if res == "win" else 0.0
            brier_sum += (pb - y) ** 2
            brier_n += 1
    n = wins + losses + pushes
    hit = wins / (wins + losses) if (wins + losses) else None
    brier = brier_sum / brier_n if brier_n else None
    return GradeSummary(
        n=n,
        wins=wins,
        losses=losses,
        pushes=pushes,
        hit_rate=hit,
        brier=brier,
        units_profit_flat_1u=units if n else None,
    )


def load_results_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def apply_results_to_picks(
    picks_df: pd.DataFrame,
    results_df: pd.DataFrame,
) -> pd.DataFrame:
    """Join on game_id; results need home_score, away_score or margin_home."""
    out = picks_df.merge(results_df, on="game_id", how="left", suffixes=("", "_res"))
    margins = []
    results = []
    for _, row in out.iterrows():
        if pd.notna(row.get("margin_home")):
            mh = float(row["margin_home"])
        elif pd.notna(row.get("home_score")) and pd.notna(row.get("away_score")):
            mh = float(row["home_score"]) - float(row["away_score"])
        else:
            margins.append(None)
            results.append(None)
            continue
        margins.append(mh)
        spread = row.get("consensus_home_spread")
        role = row.get("pick_role")
        if spread is None or role is None:
            results.append(None)
            continue
        results.append(
            grade_ats_row(mh, float(spread), str(role)),
        )
    out["margin_home"] = margins
    out["result"] = results
    return out
