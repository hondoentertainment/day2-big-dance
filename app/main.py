"""Serve static site + cached /api/picks with optional secured refresh."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from bigdance.config import (
    bundled_data_dir,
    get_allowed_origins,
    get_odds_min_interval_seconds,
    get_picks_cache_ttl_seconds,
    get_refresh_secret,
    is_vercel,
    runtime_data_dir,
)
from bigdance.pipeline import run_picks_pipeline

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB = PROJECT_ROOT / "web"
PUBLIC = PROJECT_ROOT / "public"
BUNDLED_DATA = bundled_data_dir()
LAST_PICKS = runtime_data_dir() / "last_picks.json"
RUNS = runtime_data_dir() / "runs"
EXAMPLE_PICKS = BUNDLED_DATA / "example_picks.json"

_lock = threading.Lock()
_memory_payload: dict[str, Any] | None = None
_memory_expires_at: float = 0.0
_last_live_monotonic: float = 0.0


def _attach_cache_meta(payload: dict[str, Any], **extra: Any) -> dict[str, Any]:
    out = dict(payload)
    meta = dict(out.get("meta") or {})
    meta.update(extra)
    out["meta"] = meta
    return out


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_last_picks(data: dict[str, Any]) -> None:
    LAST_PICKS.parent.mkdir(parents=True, exist_ok=True)
    LAST_PICKS.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _save_run_snapshot(data: dict[str, Any]) -> str | None:
    meta = data.get("meta") or {}
    gen = meta.get("generated_at")
    if not gen or not isinstance(gen, str):
        return None
    safe = re.sub(r"[^0-9A-Za-z_-]+", "_", gen)[:40]
    RUNS.mkdir(parents=True, exist_ok=True)
    path = RUNS / f"picks_{safe}.json"
    try:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            return str(path.relative_to(PROJECT_ROOT))
        except ValueError:
            return str(path)
    except OSError:
        return None


def _verify_refresh(request: Request, refresh: bool) -> None:
    if not refresh:
        return
    secret = get_refresh_secret()
    if not secret:
        return
    hdr = (request.headers.get("X-Refresh-Secret") or "").strip()
    if hdr != secret:
        raise HTTPException(
            status_code=403,
            detail="Refresh requires valid X-Refresh-Secret header.",
        )


def _rate_limit_live() -> None:
    interval = get_odds_min_interval_seconds()
    if interval <= 0:
        return
    global _last_live_monotonic
    now = time.monotonic()
    with _lock:
        delta = now - _last_live_monotonic
        if _last_live_monotonic > 0 and delta < interval:
            raise HTTPException(
                status_code=429,
                detail=f"Wait {interval - delta:.0f}s before another live Odds API refresh.",
            )


def _mark_live_done() -> None:
    global _last_live_monotonic
    with _lock:
        _last_live_monotonic = time.monotonic()


def _set_memory_cache(data: dict[str, Any]) -> None:
    global _memory_payload, _memory_expires_at
    ttl = get_picks_cache_ttl_seconds()
    with _lock:
        _memory_payload = data
        _memory_expires_at = time.monotonic() + ttl if ttl > 0 else time.monotonic() + 1e9


def _get_memory_cache() -> dict[str, Any] | None:
    with _lock:
        if _memory_payload is None:
            return None
        if time.monotonic() > _memory_expires_at:
            return None
        return dict(_memory_payload)


def _live_pipeline_with_fallback() -> dict[str, Any]:
    data = run_picks_pipeline()
    picks = data.get("picks") or []
    err = (data.get("meta") or {}).get("error")

    if picks:
        _write_last_picks(data)
        snap = _save_run_snapshot(data)
        if snap:
            data = _attach_cache_meta(data, run_saved_as=snap)
        return data

    if err:
        if LAST_PICKS.exists():
            disk = _load_json(LAST_PICKS)
            if disk:
                disk = _attach_cache_meta(
                    disk,
                    served_from="last_picks.json",
                    live_error=err,
                )
                return disk
        if EXAMPLE_PICKS.exists():
            ex = _load_json(EXAMPLE_PICKS)
            if ex:
                ex = _attach_cache_meta(
                    ex,
                    served_from="example_picks.json",
                    live_error=err,
                )
                return ex

    return data


def _serve_payload(data: dict[str, Any], *, from_cache: str | None) -> JSONResponse:
    extra: dict[str, Any] = {"cache_layer": from_cache} if from_cache else {}
    if from_cache:
        ttl = get_picks_cache_ttl_seconds()
        extra["cache_ttl_seconds"] = ttl
    return JSONResponse(_attach_cache_meta(data, **extra))


app = FastAPI(title="Day 2 Big Dance", version="0.2.0")

_origins = get_allowed_origins()
if _origins:
    _cred = _origins != ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=_cred,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

# Vercel serves /assets from public/assets via CDN; avoid duplicate mount.
if WEB.exists() and not is_vercel():
    app.mount("/assets", StaticFiles(directory=str(WEB / "assets")), name="assets")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "day2-bigdance"}


@app.get("/api/picks/meta")
def picks_meta() -> JSONResponse:
    mem = _get_memory_cache()
    disk = _load_json(LAST_PICKS)
    meta = {
        "memory_cache_valid": mem is not None,
        "disk_cache_exists": disk is not None,
        "ttl_seconds": get_picks_cache_ttl_seconds(),
        "refresh_secret_required": get_refresh_secret() is not None,
    }
    if mem and mem.get("meta"):
        meta["last_generated_at"] = mem["meta"].get("generated_at")
        meta["last_pick_count"] = len(mem.get("picks") or [])
        meta["last_remaining_requests"] = mem["meta"].get("remaining_requests")
    elif disk and disk.get("meta"):
        meta["last_generated_at"] = disk["meta"].get("generated_at")
        meta["last_pick_count"] = len(disk.get("picks") or [])
        meta["last_remaining_requests"] = disk["meta"].get("remaining_requests")
    return JSONResponse(meta)


@app.get("/api/picks")
def api_picks_get(
    request: Request,
    refresh: bool = Query(False, description="Live Odds API refresh (may require X-Refresh-Secret)"),
) -> JSONResponse:
    use_cache_only = os.environ.get("SERVE_CACHED_ONLY", "").lower() in ("1", "true", "yes")
    if use_cache_only and LAST_PICKS.exists() and not refresh:
        payload = _load_json(LAST_PICKS) or {}
        payload = _attach_cache_meta(payload, served_from="last_picks.json", cache_layer="serve_cached_only")
        return JSONResponse(payload)

    _verify_refresh(request, refresh)

    if refresh:
        _rate_limit_live()
        data = _live_pipeline_with_fallback()
        _mark_live_done()
        _set_memory_cache(data)
        return _serve_payload(data, from_cache="live")

    cached = _get_memory_cache()
    if cached is not None:
        return _serve_payload(cached, from_cache="memory")

    disk = _load_json(LAST_PICKS)
    if disk is not None:
        _set_memory_cache(disk)
        return _serve_payload(disk, from_cache="disk")

    data = _live_pipeline_with_fallback()
    _set_memory_cache(data)
    return _serve_payload(data, from_cache="live_cold_start")


@app.post("/api/picks/refresh")
def api_picks_refresh(request: Request) -> JSONResponse:
    _verify_refresh(request, True)
    _rate_limit_live()
    data = _live_pipeline_with_fallback()
    _mark_live_done()
    _set_memory_cache(data)
    return _serve_payload(data, from_cache="live")


@app.get("/")
def index() -> FileResponse:
    for candidate in (PUBLIC / "index.html", WEB / "index.html"):
        if candidate.exists():
            return FileResponse(str(candidate))
    return FileResponse(str(PROJECT_ROOT / "README.md"))
