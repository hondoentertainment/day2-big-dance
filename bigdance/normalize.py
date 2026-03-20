"""Team name normalization for merging odds with ratings CSV."""

from __future__ import annotations

import re
import unicodedata


def normalize_team_name(name: str) -> str:
    if not name or not isinstance(name, str):
        return ""
    s = unicodedata.normalize("NFKD", name)
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(
        r"\b(the|university|college|state|st|u|of|a&m|am)\b",
        " ",
        s,
        flags=re.I,
    )
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_aliases(path: str | None = None) -> dict[str, str]:
    """Map normalized odds name -> normalized ratings CSV name (optional YAML)."""
    import yaml

    from bigdance.config import PROJECT_ROOT

    p = path or (PROJECT_ROOT / "data" / "team_aliases.yaml")
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out: dict[str, str] = {}
    for k, v in data.items():
        if k and v:
            out[normalize_team_name(str(k))] = normalize_team_name(str(v))
    return out
