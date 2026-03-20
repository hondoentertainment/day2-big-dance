# Day 2 of the Big Dance

NCAA men’s basketball **ATS** model (market de-vig + optional team ratings) and a small **website** to review picks.

## Quick start

```powershell
cd "c:\Users\kyle\OneDrive\Desktop\Day 2 of the Big Dance"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env: set ODDS_API_KEY (https://the-odds-api.com/)
python run_server.py
```

Open **http://127.0.0.1:8000** — the UI loads **`GET /api/picks`** (cached).

- **Caching:** Responses are cached in memory for `PICKS_CACHE_TTL_SECONDS` (default **180**), then fall back to **`data/last_picks.json`** so normal page loads do not hit the Odds API.
- **Live refresh:** The **Refresh live odds** button calls **`POST /api/picks/refresh`** (one Odds API pull). Optional **`REFRESH_SECRET`**: set on the server and paste once in the **Refresh secret** field so the browser sends **`X-Refresh-Secret`**.
- **Rate limit:** Refreshes closer than **`ODDS_MIN_INTERVAL_SECONDS`** (default **45**) return **429**.
- **Run history:** Each successful live run with picks writes **`data/runs/picks_<timestamp>.json`** (gitignored).
- **Meta:** **`GET /api/picks/meta`** — cache status, last `generated_at`, pick count.
- **CORS:** Set **`ALLOWED_ORIGINS`** to your deployed site origins (comma-separated). Use `*` only if you accept open cross-origin access (credentials disabled).
- Without a key (or if the API errors), the API falls back to **`data/last_picks.json`** or **`data/example_picks.json`**.

### UX (site)

- **Last updated** line (from `generated_at` + cache layer).
- **Top 16** as a **card grid** under **720px** width; table on wider screens.
- **Copy top 16** (plain text), **Print** (formatted top 16 only).
- Links to **Odds API** and **status** page.

## CLI: export picks

```powershell
python scripts\run_picks.py
```

Writes `data/last_picks.json` and `data/picks_export.csv`.

## Grade results (optional)

1. Copy `data/results.example.csv` to `data/results.csv`.
2. Add rows: `game_id,home_score,away_score` (game_id must match `last_picks.json`).
3. Run:

```powershell
python scripts\grade_picks.py
```

## Data files

| File | Purpose |
|------|---------|
| [data/team_ratings.csv](data/team_ratings.csv) | `team`, `net_rating` (or `net`, `adj_net`). Expand with your snapshot. |
| [data/team_aliases.yaml](data/team_aliases.yaml) | Optional Odds API ↔ CSV name aliases. |
| [docs/ux-review-information.md](docs/ux-review-information.md) | UX notes for presenting picks. |

## Model weights (defaults)

Defined in `bigdance/config.py` (`ModelWeights`):

- **Blend:** 55% market fair ATS probability, 45% ratings-based P(cover) when both teams match the CSV.
- **Margin noise:** σ = 11.5 points; **home court** +3.0 on top of `net_rating` difference (scale `efficiency_to_margin` = 1.0).
- **Confidence:** grows with \|P(blend) − 0.5\|, discounted by book count, spread IQR, and market-only rows.

## Project layout

- `bigdance/` — fetch, normalize, ratings merge, ATS math, pipeline.
- `app/main.py` — FastAPI + `/api/picks`.
- `web/` — static HTML/CSS/JS.
- `scripts/` — `run_picks.py`, `grade_picks.py`.

## Deploy (GitHub + Vercel)

See **[DEPLOY.md](DEPLOY.md)** for step-by-step: create a GitHub repo, push, import the repo in [Vercel](https://vercel.com/new), set **`ODDS_API_KEY`** (and optional vars) in the Vercel dashboard, then deploy.

- **Build:** `python scripts/sync_public.py` copies [`web/`](web/) → [`public/`](public/) so the UI ships on the CDN; FastAPI serves `/api/*` on the same host.
- **Serverless disk:** writable cache and run snapshots use **`/tmp/day2-bigdance`** on Vercel (override with **`DATA_DIR`**). Bundled CSVs stay in repo **`data/`**.

## Deploy (Docker)

```bash
docker build -t day2-picks .
docker run -e ODDS_API_KEY=your_key -e PORT=8000 -p 8000:8000 day2-picks
```

Mount a volume for persistence: `-v $(pwd)/data:/app/data` so `last_picks.json` and `runs/` survive restarts.

## CI

GitHub Actions (`.github/workflows/ci.yml`) installs dependencies, imports the app, and runs **`pytest tests/`**.

## Security

- **`.env`** holds `ODDS_API_KEY`. It is **gitignored**; copy from [`.env.example`](.env.example) only with empty values in the repo.
- **Windows:** restrict the file to your user (run from the project folder in PowerShell):

  ```powershell
  icacls .env /inheritance:r /grant:r "$($env:USERNAME):(F)"
  ```

  That removes inherited ACLs and grants only your account full control, so other local OS accounts cannot read the key.
- **macOS/Linux:** `chmod 600 .env`
- If a key was pasted into chat, email, or a ticket, **rotate it** in The Odds API account portal and update `.env` only on your machine.

## Legal

For research and pool discussion only. Odds and availability depend on your Odds API plan and region.
