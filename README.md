# SLD — Social Listening Dashboard

Prototype dashboard for the **Social Listening Dashboard (SLD)** at PainMed-PA.

Collects posts from Reddit, LinkedIn, the AAPC forums, Facebook groups, X and
YouTube comments, scores each one for **ProbePS opportunity value**
through a five-stage analysis pipeline, and serves the results to a React
dashboard. The feasibility research this grew out of lives in
[testing/](testing/) — start with [testing/SLD-ROADMAP.md](testing/SLD-ROADMAP.md)
for scope and background.

> **Private repo.** Collected data contains personal information scraped from
> public social media (author names, profile URLs, organization names). Do not
> make this repository public and do not redistribute the datasets.

## Stack

| Part | What it is | Location |
|---|---|---|
| Backend | FastAPI + SQLAlchemy, PostgreSQL (Neon) via `DATABASE_URL`; local SQLite when unset | [backend/](backend/) |
| Frontend | React 19 + TypeScript + Vite | [frontend/](frontend/) |
| Analysis | Rule gate + one LLM assessment per relevant post, 65/20/15 opportunity score | [backend/app/analysis/](backend/app/analysis/) |

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

# Database (creates backend/data/sld 1.db)
cd backend
python scripts\init_db.py
cd ..
```

In Git Bash, activate with `source .venv/Scripts/activate` instead.

Credentials are read from the repo-root `.env` (see
[backend/app/config.py](backend/app/config.py)), which needs an `APIFY_TOKEN`.
Copy [.env.example](.env.example) to `.env` to start from a list of every
supported variable.
The collectors share the same token as the existing `testing/` scripts.

`DATABASE_URL` selects the database (production: the Neon PostgreSQL URL).
Leave it unset to work offline against the local SQLite file; tests always use
their own in-memory SQLite. `REPORT_TZ` (IANA name, default `UTC`) sets where
"today" starts for the Overview's New Today KPI.

The LLM (Step 1 for ambiguous relevance, Step 2 for the semantic problem and
ProbePS opportunity assessment) is chosen with `LLM_PROVIDER`:

| `LLM_PROVIDER` | What runs | Needs |
|---|---|---|
| `ollama` (default) | Local Ollama, fully offline | `ollama pull llama3.1`; optional `OLLAMA_HOST`, `OLLAMA_MODEL` |
| `bedrock` | Amazon Nova 2 Lite on Bedrock | `AWS_BEARER_TOKEN_BEDROCK`, `AWS_REGION`, `BEDROCK_MODEL_ID` |
| `none` | LLM off; the rule + zero-shot fallback classifies (opportunity fields score 0) | — |

Only the selected provider is loaded, so an Ollama run never imports boto3 or
contacts AWS. For Bedrock, use the `us.` model-ID prefix from a US region and
`global.amazon.nova-2-lite-v1:0` from anywhere else; post text is sent to AWS
for every RCM-relevant post.

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
data persists in `backend/data/sld 1.db`, so this is **not** part of routine
startup — run it only when you want fresh posts.

All commands from `backend/`:

```powershell
# Collect (each call costs Apify credits)
..\.venv\Scripts\python.exe scripts\collect_reddit.py --max-items 30
..\.venv\Scripts\python.exe scripts\collect_linkedin.py --limit 10
..\.venv\Scripts\python.exe scripts\collect_aapc.py --max-threads 5
..\.venv\Scripts\python.exe scripts\collect_facebook.py --limit 20
..\.venv\Scripts\python.exe scripts\collect_x.py --store
..\.venv\Scripts\python.exe scripts\collect_youtube.py --max-videos-total 10

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
| `collect_x.py` | `--limit` | 20 | **Total** posts kept, round-robin across accounts |
| | `--per-account` | 15 | Posts fetched per account |
| | `--store` | off | Without it, posts are only printed — nothing is written to the DB |
| | `--from-raw` | off | Reuse saved raw output instead of calling Apify again |
| `collect_youtube.py` | `--max-videos-total` | 60 | Cap on videos across all queries |
| | `--max-videos-per-query` | 5 | |
| | `--max-comments-per-video` | 50 | Worst case ≈ videos × comments (~$0.002/comment) |
| | `--families` | all | Subset of `QUERY_FAMILIES` in [youtube.py](backend/app/collectors/youtube.py) |

The per-unit flags are not total caps — they scale Apify spend faster than they
look. Start small.

Re-running a collector is safe: rows are upserted on
`(source, source_item_id)`, so existing posts are updated in place and only new
ones inserted. Each run prints an
`{'inserted': N, 'updated': N, 'skipped': N}` summary.

`run_pipeline.py` skips items already scored under the current
`ANALYSIS_VERSION`, so re-running is cheap. It commits post by post and skips
(and lists) posts that fail. Useful flags:

- `--source reddit` — analyze one source only
- `--force` — re-analyze everything, for when the prompt or stages changed
- `--item-id reddit:abc123` — (re-)analyze one post; repeatable
- `--limit 30` — pilot batch before a full run

## Scoring: ProbePS opportunity score

Every RCM-relevant post gets one LLM assessment (problem evidence, first
person, seeking level, business impact, recurrence, ProbePS fit, opportunity
type, a short reasoning line). The score is three 0–100 components with fixed
weights ([scoring_opportunity.py](backend/app/analysis/scoring_opportunity.py)):

| Component | Weight | From |
|---|---|---|
| LLM opportunity assessment | 65% | Step 2 LLM fields × their confidences |
| RCM relevance | 20% | Step 1 confidence + primary problem-category severity |
| Step 3 payer / procedure | 15% | Deterministic taxonomy specificity |

No multipliers or bonuses; two caps only (LLM score ≤ 30 for
`informational_only` / `not_an_opportunity`; final ≤ 30 without problem
evidence). An **opportunity** is a post with problem evidence and a score ≥
`OPPORTUNITY_THRESHOLD` (40, provisional). The Overview KPIs and the All
Signals `opportunity` filter share that one definition
([backend/app/api/opportunity.py](backend/app/api/opportunity.py)).

The LLM output is stored in `score_breakdown.llm_assessment`, so weight or
point changes never need the LLM again:

```powershell
..\.venv\Scripts\python.exe scripts\rescore.py --dry-run                           # distribution + top list
..\.venv\Scripts\python.exe scripts\rescore.py --dry-run --compare sld-analysis-v3 # movers vs old scores
..\.venv\Scripts\python.exe scripts\rescore.py                                     # write
```

Bump `SCORING_VERSION` in [schemas/analysis.py](backend/app/schemas/analysis.py)
when weights change, and `ANALYSIS_VERSION` when the prompt or stages change
(the latter needs a full `run_pipeline.py` run).

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
or use the **Data Collection** tab (below). The `/api/pipeline/{source}/{id}` endpoint is debug-only — it returns
the stored scoring breakdown for one post (`?live=true` re-runs every stage,
calling the LLM) to power the Pipeline/Debug tab.

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
missing tables (there is no Alembic yet), so changing an existing column needs
a manual migration on PostgreSQL.
