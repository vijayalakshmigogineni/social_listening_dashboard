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

The Step 4 LLM fallback (content stance and seeking level, used only when the
zero-shot model is unsure) is chosen with `LLM_PROVIDER`:

| `LLM_PROVIDER` | What runs | Needs |
|---|---|---|
| `ollama` (default) | Local Ollama, fully offline | `ollama pull llama3.1`; optional `OLLAMA_HOST`, `OLLAMA_MODEL` |
| `bedrock` | Amazon Nova 2 Lite on Bedrock | `AWS_BEARER_TOKEN_BEDROCK`, `AWS_REGION`, `BEDROCK_MODEL_ID` |
| `none` | Fallback off; Step 4 keeps the zero-shot result | — |

Only the selected provider is loaded, so an Ollama run never imports boto3 or
contacts AWS. For Bedrock, use the `us.` model-ID prefix from a US region and
`global.amazon.nova-2-lite-v1:0` from anywhere else; post text is sent to AWS
when that fallback runs.

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
..\.venv\Scripts\python.exe scripts\collect_facebook.py --limit 20

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
| `collect_facebook.py` | `--limit` | 20 | **Total** posts kept, round-robin across groups |
| | `--per-group` | 8 | Posts fetched per group (each ~$0.005, capped at $0.10/run) |
| | `--groups` | all in `DEFAULT_GROUPS` | Subset of group keys in [facebook.py](backend/app/collectors/facebook.py) |
| | `--top-up` | off | Only add new posts until the stored Facebook total reaches `--limit` |

### Evaluation runs

`scripts/run_experiment.py` re-normalizes the 167 gold posts plus the stored
Facebook posts from raw data, runs every stage fresh with `LLM_PROVIDER=ollama`,
stores rows under `exp187-20260924-v1/-v2` (production rows untouched), and
writes `backend/data/experiments/<id>/report.md`. Add `--report-only` to
rebuild the report without re-running.

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
From Backend

DATABASE CLEAR :
python -c "from app.db.base import engine; from sqlalchemy import text; conn = engine.connect(); conn.execute(text('DELETE FROM analysis_results')); conn.execute(text('DELETE FROM normalized_items')); conn.commit(); conn.close()"

 From scripts

Collecting Posts :
python collect_reddit.py --max-items 30
python collect_linkedin.py --limit 5
python collect_aapc.py --max-threads 15



Run pipeline :
python run_pipeline.py

When you want fresh data: collect → `run_pipeline.py` → refresh the browser,
or use the **Data Collection** tab (below). The `/api/pipeline/{source}/{id}` endpoint is debug-only — it re-runs
the stage-by-stage explanation for one existing post to power the
Pipeline/Debug tab.

### Data Collection tab

http://localhost:5173/collect does collect → review → analyze without a
terminal. It calls the same collector and pipeline code as the scripts, in a
background job inside the API process (one job at a time; a second request
gets HTTP 409). Credentials stay in the backend `.env`.

| Mode | What it fetches |
|---|---|
| Since last sweep | Per source, posts made after its checkpoint, up to now |
| Custom date range | Posts made between two dates, max N **per source** |
| Latest posts | The newest N posts **per source** |

- **Checkpoints** (`collection_checkpoints`): per source, the end of the window
  of its last *fully successful* Since Last Sweep. A source with any error keeps
  its old checkpoint, so the next sweep covers the same window again. Latest and
  Custom Range never move it. Before the first sweep, the window starts at the
  newest stored post for that source.
- The collectors fetch newest-first to a per-unit depth (a subreddit, forum,
  group, ...); the date window is applied afterwards. If a unit hits its depth
  before reaching the window start, the job shows a "may be missing" note.
- Duplicates are counted through the existing `(source, source_item_id)`
  upsert. Failed sources show their error and can be retried on their own.
- **Run SLD Analysis** scores every post not yet analyzed (same selection as
  `run_pipeline.py`), commits post by post, and records failed posts instead of
  stopping. Failed posts are retried on the next run.
- API: `GET /api/collection/sources`, `POST|GET /api/collection/jobs`,
  `GET /api/collection/jobs/{id}`, `POST /api/collection/jobs/{id}/retry`,
  `GET /api/analysis/pending`, `POST|GET /api/analysis/jobs`,
  `GET /api/analysis/jobs/{id}`.
- Job history lives in `collection_jobs` / `analysis_jobs`. These tables are
  created automatically at API startup (existing tables are not touched). A
  job still running when the server restarts, including `--reload`, is marked
  *interrupted*.

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
