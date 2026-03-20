"""Copy web/ → public/ for Vercel CDN static assets."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
PUBLIC = ROOT / "public"


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WEB / "index.html", PUBLIC / "index.html")
    assets_dst = PUBLIC / "assets"
    if assets_dst.exists():
        shutil.rmtree(assets_dst)
    shutil.copytree(WEB / "assets", assets_dst)
    print(f"Synced {WEB} to {PUBLIC}")


if __name__ == "__main__":
    main()
