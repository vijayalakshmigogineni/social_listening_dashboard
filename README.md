# SLD — Social Listening Dashboard

Prototype dashboard for the **Social Listening Dashboard (SLD)** at PainMed-PA.

Collects posts from Reddit, LinkedIn and the AAPC forums, scores each one
through a six-stage analysis pipeline, and serves the results to a React
dashboard. The feasibility research this grew out of lives in
[testing/](testing/) — start with [testing/SLD-ROADMAP.md](testing/SLD-ROADMAP.md)
for scope and background.

> **Private repo.** Collected data contains personal information scraped from
> public social media (author names, profile URLs, organization names). Do not
> make this repository public and do not redistribute the datasets.

## Stack

| Part | What it is | Location |
|---|---|---|
| Backend | FastAPI + SQLAlchemy, SQLite store | [backend/](backend/) |
| Frontend | React 19 + TypeScript + Vite | [frontend/](frontend/) |
| Analysis | Rules-first pipeline, zero-shot model for ambiguous cases | [backend/app/analysis/](backend/app/analysis/) |

Requires Python 3.11 and Node 20+ (developed against Python 3.11.9 / Node 24).

## One-time setup

Run from the repo root.

```powershell
# Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt

# Frontend
npm install --prefix frontend

# Database (creates backend/data/sld.db)
cd backend
python scripts\init_db.py
cd ..
```

In Git Bash, activate with `source .venv/Scripts/activate` instead.

Credentials are read from the repo-root `.env` (see
[backend/app/config.py](backend/app/config.py)), which needs an `APIFY_TOKEN`.
The collectors share the same token as the existing `testing/` scripts.

## Starting the application

Two terminals, both with the venv active where noted.

**Terminal 1 — API** (must run from `backend/`, since `main.py` imports `app.*`):

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — dashboard:**

```powershell
npm run dev --prefix frontend
```

Then open **http://localhost:5173**.

| URL | What |
|---|---|
| http://localhost:5173 | Dashboard |
| http://127.0.0.1:8000/api/health | API health check |
| http://127.0.0.1:8000/docs | Interactive API docs |

Vite proxies `/api` to `127.0.0.1:8000`
([frontend/vite.config.ts](frontend/vite.config.ts)), so the frontend needs no
API URL configured — but the backend must be running or every request 404s.

## Fetching data

The dashboard renders empty until data is collected and analyzed. Collected
data persists in `backend/data/sld.db`, so this is **not** part of routine
startup — run it only when you want fresh posts.

All commands from `backend/`:

```powershell
# Collect (each call costs Apify credits)
..\.venv\Scripts\python.exe scripts\collect_reddit.py --max-items 30
..\.venv\Scripts\python.exe scripts\collect_linkedin.py --limit 10
..\.venv\Scripts\python.exe scripts\collect_aapc.py --max-threads 5

# Score the new posts
..\.venv\Scripts\python.exe scripts\run_pipeline.py
```

Collectors only store raw normalized posts — nothing is scored until
`run_pipeline.py` runs.

### Collector options

| Script | Flag | Default | Note |
|---|---|---|---|
| `collect_reddit.py` | `--max-items` | 30 | **Per subreddit**, not total |
| | `--subreddits` | `CodingandBilling`, `MedicalCoding`, `Medicalbillingandcoding` | Space-separated list |
| `collect_linkedin.py` | `--limit` | 10 | |
| | `--query` | Payer/denial query | See `DEFAULT_QUERY` in [linkedin.py](backend/app/collectors/linkedin.py) |
| `collect_aapc.py` | `--max-threads` | 5 | **Per forum**, not total |

The per-unit flags are not total caps — they scale Apify spend faster than they
look. Start small.

Re-running a collector is safe: rows are upserted on
`(source, source_item_id)`, so existing posts are updated in place and only new
ones inserted. Each run prints an
`{'inserted': N, 'updated': N, 'skipped': N}` summary.

`run_pipeline.py` skips items already scored under the current
`ANALYSIS_VERSION`, so re-running is cheap. Useful flags:

- `--source reddit` — analyze one source only
- `--force` — re-score everything, for when analysis logic has changed

## Everyday loop

Already set up, just want it running:

```powershell
# Terminal 1
cd backend; ..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# Terminal 2
npm run dev --prefix frontend
```

When you want fresh data: collect → `run_pipeline.py` → refresh the browser.
There is no button in the UI to trigger collection; it is script-only by
design. The `/api/pipeline/{source}/{id}` endpoint is debug-only — it re-runs
the stage-by-stage explanation for one existing post to power the
Pipeline/Debug tab.

## Notes

**First pipeline run is slow.** The zero-shot model
(`MoritzLaurer/deberta-v3-base-zeroshot-v2.0`) downloads on first use and is
loaded lazily ([model_registry.py](backend/app/analysis/model_registry.py)), so
the first run that hits an ambiguous post stalls before producing output.
Later runs use the cached weights.

**Port 5173 may already be taken.** Vite falls back to the next free port
(5174, ...) and prints the real URL on startup — use whatever it prints. The
`/api` proxy still works, because it is server-side. The CORS allowlist in
[backend/app/main.py](backend/app/main.py) is pinned to port 5173, but that
only matters if you bypass the proxy and call the API directly from the browser.

**Run uvicorn from `backend/`.** Starting it from the repo root fails with
`ModuleNotFoundError: No module named 'app'`.

**Schema changes** need `python scripts\init_db.py` re-run; it only creates
missing tables, so drop `backend/data/sld.db` for a clean rebuild.
