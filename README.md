# SLD — Source Feasibility Tests

Research code for the **Social Listening Dashboard (SLD)** at PainMed-PA.

This repo answers one question per source: *can we actually get usable data out
of it, and what does that data look like?* It is a feasibility and collection
workbench — exploratory scripts plus the raw and classified output they
produced — not a production pipeline.

> **Private repo.** The collected datasets contain personal data scraped from
> public social media (author names, profile URLs, organization names), and the
> planning documents contain internal PainMed-PA strategy. Do not make this
> repository public and do not redistribute the datasets.

Start with [SLD-ROADMAP.md](SLD-ROADMAP.md) — it defines the scope, the two
deliverables, and why they must be measured separately.

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate     # Windows (Git Bash); use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
playwright install chromium       # only needed for the Aetna browser tests

cp .env.example .env              # then fill in your Apify credentials
```

Python 3.11 is what this was developed and run against.

## Repository layout

### Planning and findings

| File | What it is |
|---|---|
| [SLD-ROADMAP.md](SLD-ROADMAP.md) | Scope, business problem, and phased implementation plan. Read first. |
| [REDDIT-SOURCE-INVESTIGATION.md](REDDIT-SOURCE-INVESTIGATION.md) | Full write-up of the Reddit source evaluation. |
| [REDDIT-APIFY-DATA-VALIDATION.md](REDDIT-APIFY-DATA-VALIDATION.md) | Field-level validation of what the Apify Reddit actor returns. |
| [SLD-Research-Briefing.pdf](SLD-Research-Briefing.pdf) | Briefing deck. |
| [sld_week1_mentor_presentation.html](sld_week1_mentor_presentation.html) | Week 1 mentor presentation. |

### Payer and regulatory sources

One folder per source. These are mostly standalone probe scripts that hit a
payer's policy site or API and report what came back.

| Folder | Source |
|---|---|
| [aetna/](aetna/) | Aetna clinical policy bulletins, precert lists (incl. Playwright network capture) |
| [cigna/](cigna/) | Cigna coverage policies, eviCore MSK, monthly updates |
| [uhc/](uhc/) | UnitedHealthcare commercial and individual policies, ESI policy history |
| [humana/](humana/) | Humana medical/pharmacy coverage policies, injection and epidural policies |
| [cms/](cms/) | CMS coverage database, contractor filtering, Noridian LCD lookups |
| [noridian/](noridian/) | Noridian (MAC) billing codes and ESI policy |
| [novitas/](novitas/) | Novitas (MAC) billing, coding, and claims-denial availability |
| [federal_register/](federal_register/) | Federal Register API search and document detail |
| [beckers/](beckers/) | Becker's ASC/Spine RSS feed |
| [linkedin/](linkedin/) | LinkedIn post collection via Apify, plus relevance classification |

### Problem intelligence sources

[problem-intelligence/](problem-intelligence/) holds the community/forum source
work — the evidence base for Deliverable A. It has its own README; each source
folder can be read on its own.

| Folder | Source |
|---|---|
| [problem-intelligence/reddit/](problem-intelligence/reddit/) | Reddit via Apify — investigation plus a Phase 1 labelled dataset |
| [problem-intelligence/aapc/](problem-intelligence/aapc/) | AAPC discussion forums (RSS + HTML) |
| [problem-intelligence/facebook/](problem-intelligence/facebook/) | Facebook actor evaluation and selection bake-off |
| [problem-intelligence/facebook-e2e-collection/](problem-intelligence/facebook-e2e-collection/) | End-to-end Facebook collection and normalization run |
| [problem-intelligence/medical-billing-live/](problem-intelligence/medical-billing-live/) | Medical Billing Live forum (SMF) — feasibility only |

### Outputs

| Path | What it is |
|---|---|
| [retrieval_output/](retrieval_output/) | Per-source retrieval results, the `classify_*.py` scripts, and `classified_rows_*.json` |
| [signal_distribution_classified.csv](signal_distribution_classified.csv) / [.json](signal_distribution_classified.json) | Consolidated classified signal distribution across sources |
| [results_in_small_mindmaps/](results_in_small_mindmaps/) | Per-source mindmap diagrams of what each source yields |
| [finalized_dashboard_concepts/](finalized_dashboard_concepts/) | Dashboard design concepts |

## Running the scripts

Scripts resolve paths relative to their own file, so **run them from inside
their own folder**:

```bash
cd problem-intelligence/medical-billing-live
python mbl_access_test.py
```

Most payer scripts take no arguments and print what they found. Scripts that
call Apify need `APIFY_TOKEN` (and sometimes `APIFY_RUN_ID`) in `.env`.

## Credentials

All secrets live in `.env`, which is gitignored. `.env.example` lists the keys
you need. Nothing in the tracked source hardcodes a credential.

Note: the Facebook scripts load `linkedin/.env` rather than the repo-root
`.env` (see `problem-intelligence/facebook/fb_common.py`). If you hit a missing
token error there, either copy your `.env` to `linkedin/.env` or export the
variables into your shell.

## Data that is not committed

`retrieval_output/federal_register/federal_register_merged_pool_all_terms.json`
(~28 MB) is excluded as a large intermediate merge pool. Regenerate it with the
`federal_register/` collection scripts.
