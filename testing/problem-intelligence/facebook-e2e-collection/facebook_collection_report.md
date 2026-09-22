# Facebook End-to-End Collection & Normalization Report

**Generated:** 2026-09-21T12:44:29.593354+00:00  
**Scope:** discovery -> collection -> comments -> normalization. **No intelligence/classification layer.**  
**Folder:** `problem-intelligence/facebook-e2e-collection/`  
**Total Apify spend for this test:** $0.4115

> This is a feasibility test on ~10 records per category, not a production run. Conclusions below are limited to what these specific runs actually returned.

## 1. Actors used, and their REAL input schemas

Every actor's live input schema was read from its latest build before any code was written (`fb_00_inspect_schemas.py`, $0). **All four differ from the parameter names assumed in the original brief.**

| Actor | Actor ID | Total runs | Live input fields (* = required) |
|---|---|---|---|
| scrapesmith/facebook-search-scraper | 2BZSEQfgrOqtoCTib | 4027 | `queries`*, `searchType`, `maxResultsPerQuery` |
| parseforge/facebook-search-scraper | m5GRLRRCpHItqIz19 | 1096 | `queries`*, `searchType`, `maxItems` |
| thedoor/facebook-page-scraper | QAhtRJ73BUzzsWfJ5 | 10119 | `pageUrls`*, `postsToScrape`, `includeTranscript`, `postsNewerThan` |
| apify/facebook-comments-scraper | us5srxAYnsrkgUv2v | 11124392 | `startUrls`*, `resultsLimit`, `includeNestedComments`, `viewOption`, `onlyCommentsNewerThan` |

Corrections against the brief's assumptions:

- `scrapesmith/facebook-search-scraper` takes **`queries`** (an array) and **`maxResultsPerQuery`** — not `query`/`maxItems`. Its `searchType` enum is `pages | posts | groups | events | people | all`.
- `parseforge/facebook-search-scraper` takes `queries` + **`maxItems`** (different cap parameter from scrapesmith), enum `pages | groups | posts | videos`.
- `thedoor/facebook-page-scraper` takes **`pageUrls`** — not `startUrls`. It has no input for a post URL, contrary to the brief's description; its only URL input is a page URL.
- `apify/facebook-comments-scraper` matches the brief: `startUrls`, `resultsLimit`, `includeNestedComments`, `viewOption`.

All four are **PAY_PER_EVENT**. `scrapesmith` is the only one that publishes per-event prices ($0.005 actor start + $0.0005 per result).

## 2. Search queries used

All ten RCM/problem-oriented queries were submitted in a single array per search type:

- `medical claim denial`
- `insurance denial`
- `prior authorization`
- `denied claim`
- `reimbursement problem`
- `medical billing problem`
- `revenue cycle management`
- `payer denial`
- `insurance verification`
- `delayed payment`

**However, only 2 of 10 queries were actually reached** before the per-run result cap was hit: `insurance denial`, `medical claim denial`. The actor consumes queries sequentially, so the later terms (`prior authorization`, `payer denial`, `delayed payment`, …) contributed nothing to this sample. See limitation L2.

## 3. Requested vs returned

| Category | Actor | Requested | Returned | Kept | Result |
|---|---|---|---|---|---|
| A. Search posts | scrapesmith | 10 | 10 | 9 | OK |
| B. Pages | scrapesmith | 10 | 10 | 10 | OK |
| C. Groups | scrapesmith | 10 | 10 | 10 | OK |
| D. Page posts | thedoor | 10 | 6 | 6 | PARTIAL |
| E. Group posts | thedoor (probe) | 6 | 0 | 0 | **NOT SUPPORTED** |
| F. Comments | apify | 40 | 119 | 119 | OVER-DELIVERED |

Normalized total: **154 records** after deduplication (4 duplicates removed).

## 4. Field completeness (all normalized records)

| Field | Available | Missing | Percentage |
|---|---|---|---|
| source | 154 | 0 | 100.0% |
| source_item_id | 154 | 0 | 100.0% |
| url | 154 | 0 | 100.0% |
| title | 139 | 15 | 90.3% |
| text | 153 | 1 | 99.4% |
| author_id | 154 | 0 | 100.0% |
| author_name | 154 | 0 | 100.0% |
| author_profile_url | 87 | 67 | 56.5% |
| author_role | 0 | 154 | 0.0% |
| organization_name | 16 | 138 | 10.4% |
| organization_url | 16 | 138 | 10.4% |
| location | 0 | 154 | 0.0% |
| created_at | 134 | 20 | 87.0% |
| collected_at | 154 | 0 | 100.0% |
| engagement | 134 | 20 | 87.0% |
| parent_id | 119 | 35 | 77.3% |
| conversation_id | 134 | 20 | 87.0% |
| media_type | 134 | 20 | 87.0% |
| raw_data | 154 | 0 | 100.0% |
| source_metadata | 154 | 0 | 100.0% |

### By content_type

**`comment`** — 119 records. Incomplete fields: `author_profile_url` 43.7%, `author_role` 0.0%, `organization_name` 0.0%, `organization_url` 0.0%, `location` 0.0%

**`group`** — 14 records. Incomplete fields: `title` 71.4%, `author_role` 0.0%, `organization_name` 0.0%, `organization_url` 0.0%, `location` 0.0%, `created_at` 28.6%, `engagement` 28.6%, `parent_id` 0.0%, `conversation_id` 28.6%, `media_type` 28.6%

**`page`** — 10 records. Incomplete fields: `author_role` 0.0%, `location` 0.0%, `created_at` 0.0%, `engagement` 0.0%, `parent_id` 0.0%, `conversation_id` 0.0%, `media_type` 0.0%

**`post`** — 11 records. Incomplete fields: `title` 0.0%, `text` 90.9%, `author_role` 0.0%, `organization_name` 54.5%, `organization_url` 54.5%, `location` 0.0%, `parent_id` 0.0%

## 5. Which fields were available, missing, or forced to null

### Always available (100%)

`source`, `source_item_id`, `url`, `author_id`, `author_name`, `collected_at`, `raw_data`, `source_metadata` — on every one of 154 records.

### Structurally null — Facebook never provides these

| Field | Coverage | Why it is null |
|---|---|---|
| `author_role` | 0% | No actor returns a job title or role. It exists on some profiles but is not in any response. Would need profile enrichment. |
| `location` | 0% | No structured location field anywhere. Page addresses DO appear, but only inside the `snippet` display string (e.g. `... · Franklin, TN, US · 286 followers`). Parsing that would be a guess, so `location` stays null and the raw snippet is preserved in `source_metadata.snippet_raw`. |
| `title` (posts) | 0% on posts | Facebook posts genuinely have no title. Not invented. |
| `parent_id` (posts/pages/groups) | 0% | Correct — a top-level post has no parent. |

### Available but inconsistent

| Field | Coverage | Detail |
|---|---|---|
| `author_profile_url` | 56.5% overall, 43.7% on comments | Comments give `profileUrl` on only 52/119 records. The rest expose an author id but no URL. **No URL was constructed from the id** — left null per the missing-data rule. |
| `organization_name` / `organization_url` | 10.4% | Populated only where the author IS an organisation: discovered Pages and page posts. Null for individual posters, comments and groups. |
| `created_at` | 87% | Present on every post and comment. Missing on all 10 discovered Pages and 10 discovered Groups — search results carry no creation timestamp. |
| `engagement` | 87% | Same gap: page/group search hits carry follower/member counts only as display text, which is not likes/comments/shares/views. |

## 6. Duplicates, stable IDs, URLs, timestamps

**Duplicates:** yes, and they were handled at two stages.

- Discovery: 1 duplicate post(s) within the search results (same `postId` returned for two different query terms).
- Normalization: 4 duplicates removed — the 4 group posts are the same records as 4 of the search posts, because group posts had to be harvested out of the search output (see §7).

**Stable IDs: yes, 100%.** Every record carries a numeric Facebook ID: `postId` (search posts), `post.id` (page posts), `facebookId` (pages/groups), decoded comment id (comments).

> **Trap found in the comments actor.** For a reply, the top-level `commentId` field holds the **parent** comment's id, so two sibling replies carry an identical `commentId`. The reply's own id is only available inside the base64 `id` field (`comment:<postId>_<commentId>`). The normalizer decodes it. Using `commentId` naively would silently collapse distinct replies into one record.

**Original URLs: yes, 100%.** Every normalized record has a `url` a CEO can open. Comments get a deep link with `?comment_id=` (and `&reply_comment_id=` for replies).

**Timestamps: 87%.** Posts give epoch (seconds or ms depending on actor — normalized to ISO-8601 UTC); comments give ISO directly. Discovered pages/groups give none.

## 7. Group posts — the explicit question

> **Group discovery works, but Group-post collection is not supported by the tested actors.**

**Test A — `thedoor/facebook-page-scraper` fed group URLs:** 0 records returned. The actor's own log is unambiguous:

```
❌ FAILED PAGES:
   • groups: Could not resolve page ID
   • groups: 0 posts fetched
```

It parses `facebook.com/groups/<id>/` as a Page literally named `groups`, fails preflight resolution, exhausts its proxy sessions and returns nothing. This is a capability gap, not a transient error.

**Test B — group posts inside the search output:** 4 of 9 discovered posts are `/groups/<id>/permalink/<id>` URLs — real posts from inside public groups. This is genuine content, but it is **keyword-driven discovery, not targeted retrieval**: you cannot ask for "the posts of group X".

**Comments on group posts DO work.** `apify/facebook-comments-scraper` accepted group permalink URLs and returned 45 comments from them, including `groupTitle`. So the gap is specifically *group feed retrieval*, nothing else.

### What capability is required

A dedicated Facebook GROUP feed scraper. The four actors under test cover keyword search (scrapesmith, parseforge), page-feed retrieval (thedoor) and post comments (apify). None of them takes a group URL and returns that group's post feed.

- **Candidate:** `apify/facebook-groups-scraper` (`2chN8UQcH1CfxLRNE`), inputs `startUrls, resultsLimit, viewOption, onlyPostsNewerThan`.
- **Status:** NOT part of this test's actor set. Earlier work in ../facebook/facebook_actor_recommendation.json records a verified pass on group 290657479460430 (run lwd1sFYEcsEnAx10X, 10 posts with text/author/time/engagement). Adding it would require approval since it is outside the four actors named for this test.
- **Access note:** Only PUBLIC groups are in scope. Private-group content would require an authenticated session, which is out of scope for public-content collection.

## 8. Comments

**Yes — comments are available and are the richest layer tested.** 119 comments returned from 4 posts.

| Post origin | Advertised | Returned | URL |
|---|---|---|---|
| search_post | 1850 | 64 | `https://www.facebook.com/joshrinconofficial/posts/pfbid032…` |
| search_post | 634 | 10 | `https://www.facebook.com/joshrinconofficial/posts/pfbid02z…` |
| group_post_via_search | 92 | 35 | `https://www.facebook.com/groups/4425387990835085/permalink…` |
| group_post_via_search | 17 | 10 | `https://www.facebook.com/groups/3805049843060582/permalink…` |

Per-comment fields confirmed present: `text` 100%, `date` 100%, `likesCount` 100%, `profileId`/`profileName` 100%, `commentUrl` 100%, `postTitle` (parent post text) 100%, `threadingDepth` 100%, `profileUrl` 43.7%, `groupTitle` 45/119.

`threadingDepth` values 0/1/2 were all observed, and `replyToCommentId` is present on replies — so reply structure IS reconstructable. Per the brief it is preserved in `source_metadata` (`threading_depth`, `parent_comment_id`) and in `raw_data`, but deep reply trees are not treated as a requirement.

## 9. Technical limitations encountered

| # | Limitation | Evidence | Impact |
|---|---|---|---|
| L1 | **Result caps are advisory, not enforced.** `maxResultsPerQuery: 2` returned ~5 per query; `resultsLimit: 10` per post and run-level `maxItems: 45` both returned 119 comments. | Comments run returned 119 for a 40-target request | Volume and spend cannot be controlled by item caps. Only `maxTotalChargeUsd` actually bound — it capped the comments run at $0.2985 of a $0.30 ceiling. |
| L2 | **Query coverage truncated.** The run cap is consumed by the first queries in the array, so later terms never execute. | 2 of 10 queries reached | Each query needs its own run for even coverage, multiplying the $0.005 actor-start fee. |
| L3 | **thedoor cannot read group URLs.** | `Could not resolve page ID` | No targeted group-post collection. |
| L4 | **thedoor yielded 6 of 10 requested page posts.** 2 of 5 pages returned nothing. | Xsolis 2, Keith Wells 2, Evermedics 2; Denial The Movie and Advantrix 0 | Expect ~60% yield per page list; some public pages are unreadable. |
| L5 | **parseforge returns Page profiles when asked for posts.** | `searchType=posts` returned `pageId`, `followers`, `address`, `rating`, plus an `error` key | Confirms the earlier finding in `../facebook/facebook_actor_recommendation.json`. Not usable for post discovery. |
| L6 | **Reply IDs collide** if `commentId` is used as the identifier. | depth-1 and depth-2 replies shared `commentId` 38669407439339702 | Handled by decoding the base64 `id`. A naive integration would lose records. |
| L7 | **Apify API dropped a long poll** mid-run, after billing. | `ReadTimeoutError` during the group probe | Added retries + a `resume_run_id` path so a billed run is never paid for twice. |
| L8 | **Free plan, $5/cycle.** Actors gate behaviour on plan tier. | $0.4115 spent here | Production volume needs a paid plan, and the stack should be re-validated there. |
| L9 | **Cost tracking under-reports.** `thedoor` spawns a nested child actor run that bills separately and never appears in the parent run's `usageTotalUsd`. Run costs are also unsettled at SUCCEEDED time. | Child run billed $0.0201; live totals read $0.3185 vs $0.4115 actual | Budget from the account ledger (`/users/me/limits`), never from summed run totals. |
| L10 | **Discovery precision is low, as expected at this stage.** Many hits are job-seekers, lawyers, VA-disability and life-insurance content rather than provider-side RCM. | Top group hits included `People Looking for Life insurance` (41K) | Not a defect — filtering is the intelligence layer's job. But it sets the volume the classifier must absorb. |

## 10. Final feasibility answer

**Can Facebook, via this Apify approach, supply enough raw information for the canonical Social Listening dataset?**

**Yes for post- and comment-level content; no for organisational, role and location attribution; and group coverage needs one more actor.** Evidence base: 154 normalized records from 7 runs at $0.4115.

### A. Technically obtainable (proven in these runs)

- `source`, `source_item_id`, `url`, `author_id`, `author_name`, `collected_at`, `raw_data`, `source_metadata` — **100%**
- `text` — 99.4% (the one gap is a page post that is image-only)
- `created_at`, `engagement`, `media_type`, `conversation_id` — **100% on posts and comments**
- `parent_id` — 100% on comments, including reply→parent-comment links
- Page/Group **discovery** by keyword, with stable IDs and openable URLs
- Comment collection on page posts, profile posts **and group posts**

### B. Not obtainable

- `author_role` — **0%**. No actor returns it.
- `location` — **0%** as a structured field.
- `title` on posts — Facebook has no such concept.
- Follower/member counts as structured numbers — display text only.

### C. Obtainable but unreliable / inconsistent

- `author_profile_url` — 56.5% overall, **43.7% on comments**. Plan for author identity that is id-only.
- `created_at` / `engagement` — absent on discovered pages/groups (they are directory entries, not content).
- Page post yield — 6/10; 2 of 5 pages returned nothing.
- Result counts — caps not honoured (L1), so per-run volume is unpredictable.

### D. Requires a different actor

- **Targeted group-post retrieval.** None of the four actors can do it. Candidate: `apify/facebook-groups-scraper` (`2chN8UQcH1CfxLRNE`), already verified in earlier work but **outside this test's approved actor set** — adding it is your call.
- **Post discovery via parseforge** — returns page profiles; use scrapesmith.

### E. Requires separate authorization / access

- **A paid Apify plan.** $5/cycle free tier; several actors gate on tier.
- **Private groups** would need an authenticated session — out of scope, and not attempted.
- `organization_name`/`organization_url` beyond Page-authored posts would need employer enrichment from outside Facebook.

### F. Needs later intelligence processing

- Whether a record is a genuine RCM problem. Discovery is keyword-level only: this sample contains billing job ads, VA disability claims, life-insurance lead-gen and law-firm marketing alongside real denial discussion. **Nothing in this phase classifies any of it** — all twelve intelligence fields are deliberately absent and asserted absent by `fb_05_normalize.py::validate()`.
- `author_role` and `location`, if needed, must be inferred downstream and clearly marked as inferred — they are not source data.

### What this test does NOT prove

Ten records per category on a free plan. It does not establish sustained throughput, rate-limit behaviour at volume, historical backfill depth, day-over-day stability of these actors, or precision of RCM-relevant content. Facebook is **not** "fully supported" on this evidence — it is *viable for post and comment collection, with three named gaps*.

## 11. Run ledger

| Step | Actor | Run ID | Status | Final cost |
|---|---|---|---|---|
| Discovery - posts | scrapesmith/facebook-search-scraper | `PioaGZZlLAfbMdi7V` | SUCCEEDED | $0.0100 |
| Discovery - pages | scrapesmith/facebook-search-scraper | `3aQbMAUdeL5NLB8xr` | SUCCEEDED | $0.0100 |
| Discovery - groups | scrapesmith/facebook-search-scraper | `X8PYgtAEe4peNjNO8` | SUCCEEDED | $0.0100 |
| Discovery - parseforge comparison | parseforge/facebook-search-scraper | `XmDW7lWo0CpUxSNt8` | SUCCEEDED | $0.0480 |
| Page posts | thedoor/facebook-page-scraper | `9SSoHRHVYoxkdTKUe` | SUCCEEDED | $0.0150 |
| Comments | apify/facebook-comments-scraper | `t2MUVkA4knTbZhEON` | SUCCEEDED | $0.2985 |
| Group post probe | thedoor/facebook-page-scraper | `Wb4bwzTCOjhyd4bxH` | SUCCEEDED | $0.0000 |

Runs started directly by these scripts: **$0.3915**

### Nested child actor runs (billed, not started by us)

| Run ID | Actor ID | Cost |
|---|---|---|
| `LWmitvsmMvOSHJ3VT` | Wpp1BZ6yGWjySadk3 | $0.0201 |

`thedoor/facebook-page-scraper` internally calls another actor, which bills separately ($0.0201). It never appears in the parent run's `usageTotalUsd`, so **per-run cost tracking under-reports the true spend of that actor**. Budget from the account ledger, not from run totals.

**Total billed for this test: $0.4115**

> Note: a run's `usageTotalUsd` is not settled at the moment it reports SUCCEEDED. The figures above are re-read after the fact; the values printed live during collection were lower.
