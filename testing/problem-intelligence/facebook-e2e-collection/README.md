# Facebook End-to-End Collection Test

First end-to-end Facebook test for the PainMed-PA Social Listening Dashboard.

**Scope:** discovery → collection → comments → normalization → completeness report.
**Out of scope:** no AI, no classification, no database, no embeddings, no dashboard.
All twelve intelligence fields are deliberately absent and are asserted absent by
`fb_05_normalize.py::validate()`.

Read **`facebook_collection_report.md`** first — it is the deliverable.

## Setup

The Apify token is read from the environment or from the repo's existing
`linkedin/.env`. **It is never hardcoded, printed, or written to any output file.**

```powershell
# already present in linkedin/.env as APIFY_TOKEN1 (the default)
$env:APIFY_TOKEN1 = "<your-apify-token>"

# to use the other account instead:
$env:FB_APIFY_TOKEN_VAR = "APIFY_TOKEN"

pip install requests python-dotenv
```

## Run order

Each script is standalone and re-runnable. Steps 1–4 start billed Apify runs;
step 0, 5 and 6 are free.

```powershell
cd problem-intelligence\facebook-e2e-collection

python fb_00_inspect_schemas.py   # $0  live actor input schemas
python fb_01_discovery.py         # ~$0.07  posts + pages + groups + comparison
python fb_02_page_posts.py        # ~$0.02  posts from discovered Pages
python fb_03_group_posts.py       # ~$0.02  group-post capability probe
python fb_04_comments.py          # ~$0.30  comments from sampled posts
python fb_05_normalize.py         # $0  canonical schema + completeness
python fb_06_report.py            # $0  builds the markdown report
```

Total observed spend for a full pass: **$0.4115** (includes a $0.0201 nested
child actor run that `thedoor` starts internally and that never shows up in the
parent run's reported cost).

### Billing guards

Both known Apify accounts are **FREE plan, $5/cycle**. Every run is sent with an
explicit `maxItems` **and** `maxTotalChargeUsd`, and `check_budget()` refuses to
start a run the remaining allowance cannot absorb.

Item caps turned out to be **advisory** — the comments actor returned 119 records
against a `maxItems` of 45. Only `maxTotalChargeUsd` actually bound the spend.
Do not remove it.

### Resuming a billed run

If a poll dies on a network blip after the run was charged, re-read it instead of
paying twice:

```powershell
$env:FB_RESUME_GROUP_RUN    = "<runId>"   # fb_03
$env:FB_RESUME_COMMENTS_RUN = "<runId>"   # fb_04
```

## Files

| File | What it is |
|---|---|
| `fb_common.py` | Shared Apify plumbing: auth, budget guard, run+poll with retries, resume |
| `fb_00_inspect_schemas.py` | Reads each actor's **live** input schema before any code assumes one |
| `fb_01_discovery.py` | Keyword search → posts / pages / groups |
| `fb_02_page_posts.py` | Posts from discovered Pages |
| `fb_03_group_posts.py` | Group-post capability probe (the explicit open question) |
| `fb_04_comments.py` | Comments from sampled post URLs |
| `fb_05_normalize.py` | **One pipeline**, all record shapes → canonical schema |
| `fb_06_report.py` | Generates the report from the JSON on disk |

### Generated output

| File | Contents |
|---|---|
| `facebook_actor_live_schemas.json` | Live input schemas + pricing for all four actors |
| `facebook_raw_search_posts.json` | Raw discovered posts |
| `facebook_raw_pages.json` | Raw discovered pages |
| `facebook_raw_groups.json` | Raw discovered groups |
| `facebook_raw_search_parseforge_comparison.json` | Second search actor, for comparison |
| `facebook_raw_page_posts.json` | Raw page posts |
| `facebook_raw_group_posts.json` | Group probe result + verdict |
| `facebook_raw_comments.json` | Raw comments |
| `facebook_normalized_records.json` | **154 records in the canonical schema** |
| `facebook_field_completeness.json` | Field coverage, overall and per content_type |
| `facebook_collection_report.md` | **The report** |

## Headline results

154 normalized records, 0 schema violations, $0.4115.

- **100%** — `source`, `source_item_id`, `url`, `author_id`, `author_name`,
  `collected_at`, `raw_data`, `source_metadata`
- **99.4%** `text` · **87%** `created_at` / `engagement` (100% on posts and comments)
- **56.5%** `author_profile_url` (43.7% on comments) — no URL was ever constructed
- **0%** `author_role`, `location` — Facebook does not provide them

**Group posts: discovery works, targeted group-post collection does not.**
`thedoor/facebook-page-scraper` logs `Could not resolve page ID` on a group URL.
Group posts reached this dataset only indirectly, via keyword search. Comments on
group posts *do* work. See §7 of the report.

## Gotchas worth knowing

- **Reply IDs collide.** In the comments actor a reply's `commentId` field holds its
  **parent's** id. The reply's own id is inside the base64 `id`
  (`comment:<postId>_<commentId>`). `fb_05_normalize.py` decodes it. Using
  `commentId` directly silently merges sibling replies.
- **Query coverage truncates.** Only 2 of 10 queries were reached before the run cap;
  the actor consumes the array in order. Even coverage needs one run per query.
- **`parseforge/facebook-search-scraper` returns Page profiles for `searchType=posts`.**
  Confirmed again here. Use `scrapesmith` for post discovery.
