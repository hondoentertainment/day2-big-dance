"""Load optional team ratings CSV for efficiency-based margin."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from bigdance.config import ratings_csv_path
from bigdance.normalize import load_aliases, normalize_team_name


def load_ratings_table(path: Path | None = None) -> pd.DataFrame:
    p = path or ratings_csv_path()
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    if df.empty:
        return df
    df = df.copy()
    col = None
    for c in df.columns:
        if str(c).strip().lower() in ("team", "team_name", "school"):
            col = c
            break
    if col is None:
        df.columns = [str(x).strip().lower() for x in df.columns]
        col = "team" if "team" in df.columns else df.columns[0]
    net_col = None
    for name in ("net_rating", "net", "adj_net", "barthag"):
        for c in df.columns:
            if str(c).strip().lower() == name:
                net_col = c
                break
        if net_col:
            break
    if net_col is None:
        for c in df.columns:
            if c == col:
                continue
            if pd.api.types.is_numeric_dtype(df[c]):
                net_col = c
                break
    if net_col is None:
        return pd.DataFrame()
    out = df[[col, net_col]].copy()
    out.columns = ["team", "net_rating"]
    out["team_norm"] = out["team"].astype(str).map(normalize_team_name)
    out = out.drop_duplicates(subset=["team_norm"], keep="last")
    return out


def net_for_team(
    ratings: pd.DataFrame,
    team_display: str,
    aliases: dict[str, str],
) -> float | None:
    key = normalize_team_name(team_display)
    if aliases and key in aliases:
        key = aliases[key]
    if ratings.empty or "team_norm" not in ratings.columns:
        return None
    row = ratings.loc[ratings["team_norm"] == key]
    if row.empty:
        return None
    return float(row.iloc[0]["net_rating"])


def expected_margin_home(
    home_team: str,
    away_team: str,
    ratings: pd.DataFrame,
    aliases: dict[str, str],
    home_court: float,
    k_mu: float,
) -> tuple[float | None, bool]:
    """Returns (mu_home, ratings_ok). mu = k * (net_h - net_a) + home_court."""
    nh = net_for_team(ratings, home_team, aliases)
    na = net_for_team(ratings, away_team, aliases)
    if nh is None or na is None:
        return None, False
    mu = k_mu * (nh - na) + home_court
    return mu, True
