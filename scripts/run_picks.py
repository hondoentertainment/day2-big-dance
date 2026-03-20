"""Fetch odds, build picks, write data/last_picks.json + CSV."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bigdance.config import runtime_data_dir
from bigdance.pipeline import run_picks_pipeline


def main() -> int:
    data = run_picks_pipeline()
    data_dir = runtime_data_dir()
    out_json = data_dir / "last_picks.json"
    out_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {out_json}")

    picks = data.get("picks") or []
    if picks:
        csv_path = data_dir / "picks_export.csv"
        keys = list(picks[0].keys())
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(picks)
        print(f"Wrote {csv_path} ({len(picks)} rows)")

    meta = data.get("meta") or {}
    if meta.get("error"):
        print("Warning:", meta["error"], file=sys.stderr)
    print("Events on date:", meta.get("events_on_date", 0))
    print("Picks:", len(picks))
    return 0 if picks or not meta.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())
