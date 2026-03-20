"""Grade picks against data/results.csv (game_id, home_score, away_score)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bigdance.config import runtime_data_dir
from bigdance.metrics import GradeSummary, summarize_grades
from bigdance.metrics import grade_ats_row as grade_fn


def main() -> int:
    picks_path = runtime_data_dir() / "last_picks.json"
    results_path = ROOT / "data" / "results.csv"
    if not picks_path.exists():
        print("Missing", picks_path, file=sys.stderr)
        return 1
    if not results_path.exists():
        print("Missing", results_path, file=sys.stderr)
        return 1

    payload = json.loads(picks_path.read_text(encoding="utf-8"))
    picks = payload.get("picks") or []
    res = pd.read_csv(results_path)
    by_id = res.set_index("game_id").to_dict("index")

    rows: list[dict] = []
    for p in picks:
        gid = p.get("game_id")
        if gid not in by_id:
            rows.append({**p, "result": None, "margin_home": None})
            continue
        r = by_id[gid]
        hs = r.get("home_score")
        aw = r.get("away_score")
        if hs is None or aw is None or pd.isna(hs) or pd.isna(aw):
            rows.append({**p, "result": None, "margin_home": None})
            continue
        mh = float(hs) - float(aw)
        spread = p.get("consensus_home_spread")
        role = p.get("pick_role")
        if spread is None or role is None:
            rows.append({**p, "result": None, "margin_home": mh})
            continue
        result = grade_fn(mh, float(spread), str(role))
        rows.append({**p, "result": result, "margin_home": mh})

    graded = [dict(x) for x in rows if x.get("result") in ("win", "loss", "push")]
    summary: GradeSummary = summarize_grades(graded)

    out = {
        "summary": {
            "n": summary.n,
            "wins": summary.wins,
            "losses": summary.losses,
            "pushes": summary.pushes,
            "hit_rate": summary.hit_rate,
            "brier": summary.brier,
            "units_profit_flat_1u": summary.units_profit_flat_1u,
        },
        "rows": rows,
    }
    out_path = ROOT / "data" / "graded_picks.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out["summary"], indent=2))
    print("Wrote", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
