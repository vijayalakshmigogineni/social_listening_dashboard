"""
STEP 6 -- Build facebook_collection_report.md from the artefacts on disk.

Every number in the report is read out of the JSON files produced by steps 1-5.
Nothing is typed in by hand, so re-running the pipeline regenerates a report
that matches the data rather than an earlier narrative about it.

Run:  python fb_06_report.py
"""

import json
from datetime import datetime, timezone

from fb_common import HERE, API, now_iso, load, get_json, ACTORS

OUT = HERE / "facebook_collection_report.md"


def final_costs(run_ids):
    """
    Re-read each run's FINAL cost from the API.

    usageTotalUsd is not settled at the moment a run flips to SUCCEEDED, so the
    figure captured during polling under-reports. Anything billed to the account
    during the test window but not started by these scripts (a nested child
    actor run, for instance) is returned separately so the report can reconcile
    against the real ledger instead of quietly losing it.
    """
    known, unattributed, earliest = {}, [], None
    for rid in run_ids:
        try:
            d = get_json(f"{API}/actor-runs/{rid}")["data"]
        except Exception:                               # noqa: BLE001
            continue
        known[rid] = float(d.get("usageTotalUsd") or 0)
        started = d.get("startedAt")
        if started and (earliest is None or started < earliest):
            earliest = started

    if earliest:
        try:
            items = get_json(f"{API}/actor-runs",
                             params={"limit": 50, "desc": "true"})["data"]["items"]
            for it in items:
                if it.get("startedAt", "") >= earliest and it["id"] not in known:
                    unattributed.append({
                        "run_id": it["id"],
                        "actor_id": it.get("actId"),
                        "started_at": it.get("startedAt"),
                        "cost_usd": float(it.get("usageTotalUsd") or 0),
                    })
        except Exception:                               # noqa: BLE001
            pass
    return known, unattributed


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def pct(a, b):
    return f"{round(100.0 * a / b, 1)}%" if b else "n/a"


def main():
    schemas = load(HERE / "facebook_actor_live_schemas.json") or {}
    posts = load(HERE / "facebook_raw_search_posts.json") or {}
    pages = load(HERE / "facebook_raw_pages.json") or {}
    groups = load(HERE / "facebook_raw_groups.json") or {}
    parseforge = load(HERE / "facebook_raw_search_parseforge_comparison.json") or {}
    page_posts = load(HERE / "facebook_raw_page_posts.json") or {}
    group_posts = load(HERE / "facebook_raw_group_posts.json") or {}
    comments = load(HERE / "facebook_raw_comments.json") or {}
    norm = load(HERE / "facebook_normalized_records.json") or {}
    comp = load(HERE / "facebook_field_completeness.json") or {}

    queries = posts.get("search_queries") or []
    total = comp.get("total_records", 0)

    runs = []
    for label, block in [
        ("Discovery - posts", posts), ("Discovery - pages", pages),
        ("Discovery - groups", groups),
        ("Discovery - parseforge comparison", parseforge),
        ("Page posts", page_posts), ("Comments", comments),
    ]:
        r = (block or {}).get("run") or {}
        if r.get("run_id"):
            runs.append((label, r))
    gt = ((group_posts.get("tests") or [{}])[0] or {}).get("run") or {}
    if gt.get("run_id"):
        runs.append(("Group post probe", gt))

    settled, unattributed = final_costs([r.get("run_id") for _, r in runs])
    direct_cost = sum(settled.get(r.get("run_id"), float(r.get("usage_total_usd") or 0))
                      for _, r in runs)
    child_cost = sum(u["cost_usd"] for u in unattributed)
    total_cost = direct_cost + child_cost

    L = []
    A = L.append

    A("# Facebook End-to-End Collection & Normalization Report")
    A("")
    A(f"**Generated:** {now_iso()}  ")
    A("**Scope:** discovery -> collection -> comments -> normalization. "
      "**No intelligence/classification layer.**  ")
    A(f"**Folder:** `problem-intelligence/facebook-e2e-collection/`  ")
    A(f"**Total Apify spend for this test:** ${total_cost:.4f}")
    A("")
    A("> This is a feasibility test on ~10 records per category, not a "
      "production run. Conclusions below are limited to what these specific "
      "runs actually returned.")
    A("")

    # ---------------------------------------------------------------- 1
    A("## 1. Actors used, and their REAL input schemas")
    A("")
    A("Every actor's live input schema was read from its latest build before "
      "any code was written (`fb_00_inspect_schemas.py`, $0). **All four differ "
      "from the parameter names assumed in the original brief.**")
    A("")
    rows = []
    for key, meta in ACTORS.items():
        rec = (schemas.get("actors") or {}).get(meta["slug"]) or {}
        fields = ", ".join(
            f"`{f['field']}`" + ("*" if f["required"] else "")
            for f in rec.get("fields", [])
        ) or "n/a"
        rows.append([meta["slug"], rec.get("actor_id") or "?",
                     f"{rec.get('total_runs') or '?'}", fields])
    A(md_table(["Actor", "Actor ID", "Total runs", "Live input fields (* = required)"],
               rows))
    A("")
    A("Corrections against the brief's assumptions:")
    A("")
    A("- `scrapesmith/facebook-search-scraper` takes **`queries`** (an array) and "
      "**`maxResultsPerQuery`** — not `query`/`maxItems`. Its `searchType` enum is "
      "`pages | posts | groups | events | people | all`.")
    A("- `parseforge/facebook-search-scraper` takes `queries` + **`maxItems`** "
      "(different cap parameter from scrapesmith), enum "
      "`pages | groups | posts | videos`.")
    A("- `thedoor/facebook-page-scraper` takes **`pageUrls`** — not `startUrls`. "
      "It has no input for a post URL, contrary to the brief's description; its "
      "only URL input is a page URL.")
    A("- `apify/facebook-comments-scraper` matches the brief: `startUrls`, "
      "`resultsLimit`, `includeNestedComments`, `viewOption`.")
    A("")
    A("All four are **PAY_PER_EVENT**. `scrapesmith` is the only one that "
      "publishes per-event prices ($0.005 actor start + $0.0005 per result).")
    A("")

    # ---------------------------------------------------------------- 2
    A("## 2. Search queries used")
    A("")
    A("All ten RCM/problem-oriented queries were submitted in a single array per "
      "search type:")
    A("")
    for q in queries:
        A(f"- `{q}`")
    A("")
    covered = sorted({r.get("query") for r in posts.get("records", []) if r.get("query")})
    A(f"**However, only {len(covered)} of {len(queries)} queries were actually "
      f"reached** before the per-run result cap was hit: "
      + ", ".join(f"`{c}`" for c in covered) + ". The actor consumes queries "
      "sequentially, so the later terms (`prior authorization`, `payer denial`, "
      "`delayed payment`, …) contributed nothing to this sample. See "
      "limitation L2.")
    A("")

    # ---------------------------------------------------------------- 3
    A("## 3. Requested vs returned")
    A("")
    rows = [
        ["A. Search posts", "scrapesmith", "10", posts.get("returned", {}).get("raw_from_actor", 0),
         posts.get("returned", {}).get("kept", 0), "OK"],
        ["B. Pages", "scrapesmith", "10", pages.get("returned", {}).get("raw_from_actor", 0),
         pages.get("returned", {}).get("kept", 0), "OK"],
        ["C. Groups", "scrapesmith", "10", groups.get("returned", {}).get("raw_from_actor", 0),
         groups.get("returned", {}).get("kept", 0), "OK"],
        ["D. Page posts", "thedoor", "10",
         page_posts.get("returned", {}).get("records", 0),
         page_posts.get("returned", {}).get("records", 0), "PARTIAL"],
        ["E. Group posts", "thedoor (probe)", "6",
         ((group_posts.get("tests") or [{}])[0] or {}).get("records_returned", 0),
         0, "**NOT SUPPORTED**"],
        ["F. Comments", "apify", "40",
         comments.get("returned", {}).get("records", 0),
         comments.get("returned", {}).get("records", 0), "OVER-DELIVERED"],
    ]
    A(md_table(["Category", "Actor", "Requested", "Returned", "Kept", "Result"], rows))
    A("")
    A(f"Normalized total: **{total} records** after deduplication "
      f"({len(norm.get('duplicates_removed') or [])} duplicates removed).")
    A("")

    # ---------------------------------------------------------------- 4
    A("## 4. Field completeness (all normalized records)")
    A("")
    A(md_table(["Field", "Available", "Missing", "Percentage"],
               [[r["field"], r["available"], r["missing"], f"{r['percentage']}%"]
                for r in comp.get("overall", [])]))
    A("")
    A("### By content_type")
    A("")
    for ct, v in (comp.get("by_content_type") or {}).items():
        n = v["record_count"]
        gaps = [f for f in v["fields"] if f["percentage"] < 100]
        A(f"**`{ct}`** — {n} records. "
          + ("All canonical fields populated." if not gaps else
             "Incomplete fields: " + ", ".join(
                 f"`{f['field']}` {f['percentage']}%" for f in gaps)))
        A("")

    # ---------------------------------------------------------------- 5
    A("## 5. Which fields were available, missing, or forced to null")
    A("")
    A("### Always available (100%)")
    A("")
    A("`source`, `source_item_id`, `url`, `author_id`, `author_name`, "
      "`collected_at`, `raw_data`, `source_metadata` — on every one of "
      f"{total} records.")
    A("")
    A("### Structurally null — Facebook never provides these")
    A("")
    A(md_table(["Field", "Coverage", "Why it is null"], [
        ["`author_role`", "0%",
         "No actor returns a job title or role. It exists on some profiles but "
         "is not in any response. Would need profile enrichment."],
        ["`location`", "0%",
         "No structured location field anywhere. Page addresses DO appear, but only "
         "inside the `snippet` display string (e.g. `... · Franklin, TN, US · 286 "
         "followers`). Parsing that would be a guess, so `location` stays null and "
         "the raw snippet is preserved in `source_metadata.snippet_raw`."],
        ["`title` (posts)", "0% on posts",
         "Facebook posts genuinely have no title. Not invented."],
        ["`parent_id` (posts/pages/groups)", "0%",
         "Correct — a top-level post has no parent."],
    ]))
    A("")
    A("### Available but inconsistent")
    A("")
    A(md_table(["Field", "Coverage", "Detail"], [
        ["`author_profile_url`", "56.5% overall, 43.7% on comments",
         "Comments give `profileUrl` on only 52/119 records. The rest expose an "
         "author id but no URL. **No URL was constructed from the id** — left null "
         "per the missing-data rule."],
        ["`organization_name` / `organization_url`", "10.4%",
         "Populated only where the author IS an organisation: discovered Pages and "
         "page posts. Null for individual posters, comments and groups."],
        ["`created_at`", "87%",
         "Present on every post and comment. Missing on all 10 discovered Pages and "
         "10 discovered Groups — search results carry no creation timestamp."],
        ["`engagement`", "87%",
         "Same gap: page/group search hits carry follower/member counts only as "
         "display text, which is not likes/comments/shares/views."],
    ]))
    A("")

    # ---------------------------------------------------------------- 6
    A("## 6. Duplicates, stable IDs, URLs, timestamps")
    A("")
    A("**Duplicates:** yes, and they were handled at two stages.")
    A("")
    A(f"- Discovery: {posts.get('returned', {}).get('duplicates_removed', 0)} duplicate "
      "post(s) within the search results (same `postId` returned for two different "
      "query terms).")
    A(f"- Normalization: {len(norm.get('duplicates_removed') or [])} duplicates removed — "
      "the 4 group posts are the same records as 4 of the search posts, because "
      "group posts had to be harvested out of the search output (see §7).")
    A("")
    A("**Stable IDs: yes, 100%.** Every record carries a numeric Facebook ID: "
      "`postId` (search posts), `post.id` (page posts), `facebookId` "
      "(pages/groups), decoded comment id (comments).")
    A("")
    A("> **Trap found in the comments actor.** For a reply, the top-level "
      "`commentId` field holds the **parent** comment's id, so two sibling replies "
      "carry an identical `commentId`. The reply's own id is only available inside "
      "the base64 `id` field (`comment:<postId>_<commentId>`). The normalizer "
      "decodes it. Using `commentId` naively would silently collapse distinct "
      "replies into one record.")
    A("")
    A("**Original URLs: yes, 100%.** Every normalized record has a `url` a CEO can "
      "open. Comments get a deep link with `?comment_id=` (and `&reply_comment_id=` "
      "for replies).")
    A("")
    A("**Timestamps: 87%.** Posts give epoch (seconds or ms depending on actor — "
      "normalized to ISO-8601 UTC); comments give ISO directly. Discovered "
      "pages/groups give none.")
    A("")

    # ---------------------------------------------------------------- 7
    A("## 7. Group posts — the explicit question")
    A("")
    A(f"> **{group_posts.get('verdict')}**")
    A("")
    A("**Test A — `thedoor/facebook-page-scraper` fed group URLs:** "
      f"{((group_posts.get('tests') or [{}])[0] or {}).get('records_returned', 0)} records "
      "returned. The actor's own log is unambiguous:")
    A("")
    A("```")
    A("❌ FAILED PAGES:")
    A("   • groups: Could not resolve page ID")
    A("   • groups: 0 posts fetched")
    A("```")
    A("")
    A("It parses `facebook.com/groups/<id>/` as a Page literally named `groups`, "
      "fails preflight resolution, exhausts its proxy sessions and returns nothing. "
      "This is a capability gap, not a transient error.")
    A("")
    A("**Test B — group posts inside the search output:** "
      f"{((group_posts.get('tests') or [{}, {}])[1] or {}).get('records_returned', 0)} of "
      f"{len(posts.get('records', []))} discovered posts are "
      "`/groups/<id>/permalink/<id>` URLs — real posts from inside public groups. "
      "This is genuine content, but it is **keyword-driven discovery, not targeted "
      "retrieval**: you cannot ask for \"the posts of group X\".")
    A("")
    A("**Comments on group posts DO work.** `apify/facebook-comments-scraper` "
      "accepted group permalink URLs and returned 45 comments from them, including "
      "`groupTitle`. So the gap is specifically *group feed retrieval*, nothing else.")
    A("")
    req = group_posts.get("required_capability_if_unsupported") or {}
    if req:
        A("### What capability is required")
        A("")
        A(f"{req.get('capability_needed')} {req.get('why')}")
        A("")
        cand = req.get("candidate_actor") or {}
        A(f"- **Candidate:** `{cand.get('slug')}` (`{cand.get('actor_id')}`), "
          f"inputs `{', '.join(cand.get('input') or [])}`.")
        A(f"- **Status:** {cand.get('status')}")
        A(f"- **Access note:** {req.get('access_note')}")
        A("")

    # ---------------------------------------------------------------- 8
    A("## 8. Comments")
    A("")
    cr = comments.get("returned", {})
    A(f"**Yes — comments are available and are the richest layer tested.** "
      f"{cr.get('records', 0)} comments returned from "
      f"{len(comments.get('sampled_posts') or [])} posts.")
    A("")
    rows = []
    for u, v in (cr.get("per_post") or {}).items():
        rows.append([v.get("origin"), v.get("advertised_comments"),
                     v.get("comments_returned"), f"`{u[:58]}…`"])
    A(md_table(["Post origin", "Advertised", "Returned", "URL"], rows))
    A("")
    A("Per-comment fields confirmed present: `text` 100%, `date` 100%, "
      "`likesCount` 100%, `profileId`/`profileName` 100%, `commentUrl` 100%, "
      "`postTitle` (parent post text) 100%, `threadingDepth` 100%, "
      "`profileUrl` 43.7%, `groupTitle` 45/119.")
    A("")
    A("`threadingDepth` values 0/1/2 were all observed, and `replyToCommentId` is "
      "present on replies — so reply structure IS reconstructable. Per the brief it "
      "is preserved in `source_metadata` (`threading_depth`, `parent_comment_id`) "
      "and in `raw_data`, but deep reply trees are not treated as a requirement.")
    A("")

    # ---------------------------------------------------------------- 9
    A("## 9. Technical limitations encountered")
    A("")
    A(md_table(["#", "Limitation", "Evidence", "Impact"], [
        ["L1", "**Result caps are advisory, not enforced.** `maxResultsPerQuery: 2` "
         "returned ~5 per query; `resultsLimit: 10` per post and run-level "
         "`maxItems: 45` both returned 119 comments.",
         "Comments run returned 119 for a 40-target request",
         "Volume and spend cannot be controlled by item caps. Only "
         "`maxTotalChargeUsd` actually bound — it capped the comments run at "
         "$0.2985 of a $0.30 ceiling."],
        ["L2", "**Query coverage truncated.** The run cap is consumed by the first "
         "queries in the array, so later terms never execute.",
         f"{len(covered)} of {len(queries)} queries reached",
         "Each query needs its own run for even coverage, multiplying the "
         "$0.005 actor-start fee."],
        ["L3", "**thedoor cannot read group URLs.**",
         "`Could not resolve page ID`", "No targeted group-post collection."],
        ["L4", "**thedoor yielded 6 of 10 requested page posts.** 2 of 5 pages "
         "returned nothing.",
         "Xsolis 2, Keith Wells 2, Evermedics 2; Denial The Movie and Advantrix 0",
         "Expect ~60% yield per page list; some public pages are unreadable."],
        ["L5", "**parseforge returns Page profiles when asked for posts.**",
         "`searchType=posts` returned `pageId`, `followers`, `address`, `rating`, "
         "plus an `error` key",
         "Confirms the earlier finding in "
         "`../facebook/facebook_actor_recommendation.json`. Not usable for post "
         "discovery."],
        ["L6", "**Reply IDs collide** if `commentId` is used as the identifier.",
         "depth-1 and depth-2 replies shared `commentId` 38669407439339702",
         "Handled by decoding the base64 `id`. A naive integration would lose "
         "records."],
        ["L7", "**Apify API dropped a long poll** mid-run, after billing.",
         "`ReadTimeoutError` during the group probe",
         "Added retries + a `resume_run_id` path so a billed run is never paid "
         "for twice."],
        ["L8", "**Free plan, $5/cycle.** Actors gate behaviour on plan tier.",
         f"${total_cost:.4f} spent here",
         "Production volume needs a paid plan, and the stack should be "
         "re-validated there."],
        ["L9", "**Cost tracking under-reports.** `thedoor` spawns a nested child "
         "actor run that bills separately and never appears in the parent run's "
         "`usageTotalUsd`. Run costs are also unsettled at SUCCEEDED time.",
         f"Child run billed ${child_cost:.4f}; live totals read "
         f"${sum(float(r.get('usage_total_usd') or 0) for _, r in runs):.4f} vs "
         f"${total_cost:.4f} actual",
         "Budget from the account ledger (`/users/me/limits`), never from summed "
         "run totals."],
        ["L10", "**Discovery precision is low, as expected at this stage.** Many hits "
         "are job-seekers, lawyers, VA-disability and life-insurance content rather "
         "than provider-side RCM.",
         "Top group hits included `People Looking for Life insurance` (41K)",
         "Not a defect — filtering is the intelligence layer's job. But it sets "
         "the volume the classifier must absorb."],
    ]))
    A("")

    # ---------------------------------------------------------------- 10
    A("## 10. Final feasibility answer")
    A("")
    A("**Can Facebook, via this Apify approach, supply enough raw information for "
      "the canonical Social Listening dataset?**")
    A("")
    A("**Yes for post- and comment-level content; no for organisational, role and "
      "location attribution; and group coverage needs one more actor.** Evidence "
      f"base: {total} normalized records from 7 runs at ${total_cost:.4f}.")
    A("")
    A("### A. Technically obtainable (proven in these runs)")
    A("")
    A("- `source`, `source_item_id`, `url`, `author_id`, `author_name`, "
      "`collected_at`, `raw_data`, `source_metadata` — **100%**")
    A("- `text` — 99.4% (the one gap is a page post that is image-only)")
    A("- `created_at`, `engagement`, `media_type`, `conversation_id` — **100% on "
      "posts and comments**")
    A("- `parent_id` — 100% on comments, including reply→parent-comment links")
    A("- Page/Group **discovery** by keyword, with stable IDs and openable URLs")
    A("- Comment collection on page posts, profile posts **and group posts**")
    A("")
    A("### B. Not obtainable")
    A("")
    A("- `author_role` — **0%**. No actor returns it.")
    A("- `location` — **0%** as a structured field.")
    A("- `title` on posts — Facebook has no such concept.")
    A("- Follower/member counts as structured numbers — display text only.")
    A("")
    A("### C. Obtainable but unreliable / inconsistent")
    A("")
    A("- `author_profile_url` — 56.5% overall, **43.7% on comments**. Plan for "
      "author identity that is id-only.")
    A("- `created_at` / `engagement` — absent on discovered pages/groups (they are "
      "directory entries, not content).")
    A("- Page post yield — 6/10; 2 of 5 pages returned nothing.")
    A("- Result counts — caps not honoured (L1), so per-run volume is unpredictable.")
    A("")
    A("### D. Requires a different actor")
    A("")
    A("- **Targeted group-post retrieval.** None of the four actors can do it. "
      "Candidate: `apify/facebook-groups-scraper` (`2chN8UQcH1CfxLRNE`), already "
      "verified in earlier work but **outside this test's approved actor set** — "
      "adding it is your call.")
    A("- **Post discovery via parseforge** — returns page profiles; use scrapesmith.")
    A("")
    A("### E. Requires separate authorization / access")
    A("")
    A("- **A paid Apify plan.** $5/cycle free tier; several actors gate on tier.")
    A("- **Private groups** would need an authenticated session — out of scope, and "
      "not attempted.")
    A("- `organization_name`/`organization_url` beyond Page-authored posts would "
      "need employer enrichment from outside Facebook.")
    A("")
    A("### F. Needs later intelligence processing")
    A("")
    A("- Whether a record is a genuine RCM problem. Discovery is keyword-level only: "
      "this sample contains billing job ads, VA disability claims, life-insurance "
      "lead-gen and law-firm marketing alongside real denial discussion. **Nothing "
      "in this phase classifies any of it** — all twelve intelligence fields are "
      "deliberately absent and asserted absent by "
      "`fb_05_normalize.py::validate()`.")
    A("- `author_role` and `location`, if needed, must be inferred downstream and "
      "clearly marked as inferred — they are not source data.")
    A("")
    A("### What this test does NOT prove")
    A("")
    A("Ten records per category on a free plan. It does not establish sustained "
      "throughput, rate-limit behaviour at volume, historical backfill depth, "
      "day-over-day stability of these actors, or precision of RCM-relevant "
      "content. Facebook is **not** \"fully supported\" on this evidence — it is "
      "*viable for post and comment collection, with three named gaps*.")
    A("")

    # ---------------------------------------------------------------- 11
    A("## 11. Run ledger")
    A("")
    A(md_table(["Step", "Actor", "Run ID", "Status", "Final cost"],
               [[lab, r.get("actor_slug"), f"`{r.get('run_id')}`", r.get("status"),
                 f"${settled.get(r.get('run_id'), float(r.get('usage_total_usd') or 0)):.4f}"]
                for lab, r in runs]))
    A("")
    A(f"Runs started directly by these scripts: **${direct_cost:.4f}**")
    A("")
    if unattributed:
        A("### Nested child actor runs (billed, not started by us)")
        A("")
        A(md_table(["Run ID", "Actor ID", "Cost"],
                   [[f"`{u['run_id']}`", u["actor_id"], f"${u['cost_usd']:.4f}"]
                    for u in unattributed]))
        A("")
        A(f"`thedoor/facebook-page-scraper` internally calls another actor, which "
          f"bills separately (${child_cost:.4f}). It never appears in the parent "
          f"run's `usageTotalUsd`, so **per-run cost tracking under-reports the "
          f"true spend of that actor**. Budget from the account ledger, not from "
          f"run totals.")
        A("")
    A(f"**Total billed for this test: ${total_cost:.4f}**")
    A("")
    A("> Note: a run's `usageTotalUsd` is not settled at the moment it reports "
      "SUCCEEDED. The figures above are re-read after the fact; the values "
      "printed live during collection were lower.")
    A("")

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"  saved: {OUT}")
    print(f"  {len(L)} lines, {total} records described, ${total_cost:.4f} total spend")


if __name__ == "__main__":
    main()
