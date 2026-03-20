# Deploy to GitHub + Vercel

## 1. GitHub repository

From the project root (first time only):

```powershell
git init
git add .
git commit -m "chore: initial Day 2 Big Dance app"
```

Create a **new empty** repo on GitHub (no README), then:

```powershell
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git branch -M main
git push -u origin main
```

Use SSH remote if you prefer: `git@github.com:YOUR_USER/YOUR_REPO.git`.

## 2. Vercel project

1. Sign in at [vercel.com](https://vercel.com) → **Add New…** → **Project**.
2. **Import** your GitHub repository.
3. Vercel should detect **FastAPI** (via `pyproject.toml` + `requirements.txt`).
4. **Root directory:** leave default (repo root).
5. **Build Command:** `python scripts/sync_public.py` (already in [`vercel.json`](vercel.json)).
6. **Install Command:** `pip install -r requirements.txt` (default in `vercel.json`).

### Environment variables (Vercel → Project → Settings → Environment Variables)

| Name | Value | Notes |
|------|--------|--------|
| `ODDS_API_KEY` | your key | Required for live odds. |
| `TARGET_DATE` | e.g. `2026-03-20` | Slate filter (local TZ below). |
| `TIMEZONE` | `America/New_York` | |
| `REFRESH_SECRET` | random string | Optional; if set, paste in site “Refresh secret” field. |
| `PICKS_CACHE_TTL_SECONDS` | `180` | Optional. |
| `DATA_DIR` | `/tmp/day2-bigdance` | Optional override for writable cache on serverless. |

Do **not** commit secrets. Production + Preview should both get `ODDS_API_KEY` if you want previews to work.

6. **Deploy.** Production URL will look like `https://your-project.vercel.app`.

Static UI is served from `public/` (synced from `web/` at build time). API routes stay on the same host (`/api/picks`, etc.), so you do not need CORS for the default setup.

## 3. CLI alternative

```powershell
npm i -g vercel
vercel login
vercel link
vercel env pull
vercel --prod
```

## 4. After changing the UI

Run locally, then commit:

```powershell
python scripts/sync_public.py
git add public
git commit -m "chore: sync public assets"
```

Or rely on Vercel’s build step to run `sync_public.py` on every deploy.

## 5. Limits

Vercel Functions have [size and duration limits](https://vercel.com/docs/functions/limitations). This app is small; `pandas` adds weight—if the bundle is too large, trim deps or add `excludeFiles` in `vercel.json`.
