"""
Shared Apify plumbing for the Facebook feasibility tests.

Mirrors the existing Reddit pattern (problem-intelligence/reddit/fetch_reddit_60.py):
the credential is read from the repo's existing linkedin/.env and is never copied,
printed, or written to disk.

Actors used (verified against their live input schemas, not guessed -- see
fb_actor_schemas.json):

  danek/facebook-search-ppr   "Facebook Search Scraper"
      query        : str   (required)
      search_type  : str   (required) enum: pages | places | posts | global
      max_posts    : int   (required)
      recent_posts : bool
      location     : str
      start_date   : str
      end_date     : str
      NOTE: the parameter is `search_type` -- NOT `type` and NOT `searchType`.
            The result cap is `max_posts` -- NOT `maxItems`.
            There is no `groups` value in the enum.

  apify/facebook-groups-scraper
      startUrls, resultsLimit, viewOption, searchGroupKeyword,
      searchGroupYear, onlyPostsNewerThan

  apify/facebook-posts-scraper
      startUrls, resultsLimit, captionText, onlyPostsNewerThan, onlyPostsOlderThan

  apify/facebook-comments-scraper
      startUrls, resultsLimit, includeNestedComments, viewOption, onlyCommentsNewerThan

BILLING GUARD: the account is on the FREE plan ($5/cycle). Every run is started
with an explicit maxItems + maxTotalChargeUsd cap, and check_budget() refuses to
start a run when the remaining allowance is below a floor.
"""

import os
import io
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

# Windows consoles default to cp1252; Facebook text is full of emoji and smart
# quotes. Without this every print of a real post raises UnicodeEncodeError.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

load_dotenv(REPO_ROOT / "linkedin" / ".env")

# Two Apify credentials already exist in linkedin/.env. Both are FREE-plan
# accounts with a $5 monthly allowance:
#   APIFY_TOKEN  -> rapturous_juncus         (near its cap; used by the Reddit work)
#   APIFY_TOKEN1 -> bewildered_temperature_xvn (headroom; used for this Facebook work)
# APIFY_TOKEN1 is preferred here purely for the remaining allowance. Override
# with FB_APIFY_TOKEN_VAR if you want the other account.
TOKEN_VAR = os.getenv("FB_APIFY_TOKEN_VAR", "APIFY_TOKEN1")
APIFY_TOKEN = os.getenv(TOKEN_VAR) or os.getenv("APIFY_TOKEN")
if not APIFY_TOKEN:
    raise RuntimeError(
        f"{TOKEN_VAR} is not set. Expected it in linkedin/.env (the existing repo "
        "credentials) or in the environment."
    )

AUTH = {"Authorization": f"Bearer {APIFY_TOKEN}"}
API = "https://api.apify.com/v2"

ACTORS = {
    # PRIMARY search actor. Chosen after danek/facebook-search-ppr refused to run
    # on this plan ("This actor is for paid users only" -- see the run log quoted
    # in facebook_post_search_smoke_test.json). Its search_type enum is the only
    # one that covers posts, groups AND pages, which is what Tasks 3-5 need.
    #   query, search_type, max_results, start_date, end_date, recent_posts, location_uid
    #   search_type enum: posts | pages | groups | people | videos | events
    #   $0.00259 per result + $0.00005 actor start
    "search":    {"id": "F60Kx7YJNOmKmqQm3", "name": "scrapeforge/facebook-search-posts"},
    # Blocked on FREE plans -- kept here so the finding is reproducible.
    "search_danek": {"id": "l6CUZt8H0214D3I0N", "name": "danek/facebook-search-ppr"},
    "groups":   {"id": "2chN8UQcH1CfxLRNE", "name": "apify/facebook-groups-scraper"},
    "posts":    {"id": "KoJrdxJCTtpon81KY", "name": "apify/facebook-posts-scraper"},
    "pages":    {"id": "4Hv5RhChiaDk6iwad", "name": "apify/facebook-pages-scraper"},
    "comments": {"id": "us5srxAYnsrkgUv2v", "name": "apify/facebook-comments-scraper"},
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def budget():
    """(used_usd, cap_usd, remaining_usd) for the current monthly cycle."""
    d = requests.get(f"{API}/users/me/limits", headers=AUTH, timeout=30).json()["data"]
    used = d["current"]["monthlyUsageUsd"]
    cap = d["limits"]["maxMonthlyUsageUsd"]
    return used, cap, cap - used


def check_budget(need_usd, floor_usd=0.02):
    """Refuse to start a run that the remaining allowance cannot absorb."""
    used, cap, remaining = budget()
    print(f"  [budget] used ${used:.3f} / ${cap} -> ${remaining:.3f} remaining")
    if remaining - need_usd < floor_usd:
        raise RuntimeError(
            f"REFUSING TO RUN: estimated ${need_usd:.3f} would leave less than "
            f"${floor_usd:.3f} of the ${cap} monthly allowance "
            f"(${remaining:.3f} remaining). Stop and re-plan."
        )
    return remaining


def run_actor(actor_key, run_input, max_items=None, max_charge_usd=None,
              poll_seconds=5, timeout_seconds=600, label=""):
    """Start an actor run with hard caps, poll to completion, return (run, items)."""
    actor = ACTORS[actor_key]
    params = {}
    if max_items is not None:
        params["maxItems"] = max_items
    if max_charge_usd is not None:
        params["maxTotalChargeUsd"] = max_charge_usd

    print(f"  [{actor['name']}] {label}")
    print(f"    input: {json.dumps(run_input)[:300]}")
    print(f"    caps : maxItems={max_items} maxTotalChargeUsd={max_charge_usd}")

    start = requests.post(
        f"{API}/acts/{actor['id']}/runs",
        headers={**AUTH, "Content-Type": "application/json"},
        params=params,
        data=json.dumps(run_input),
        timeout=60,
    )
    if not start.ok:
        print(f"    START FAILED {start.status_code}: {start.text[:400]}")
        start.raise_for_status()
    run = start.json()["data"]
    run_id = run["id"]
    print(f"    run started: {run_id}")

    t0 = time.time()
    status = run["status"]
    while status not in ("SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"):
        time.sleep(poll_seconds)
        run = requests.get(f"{API}/actor-runs/{run_id}", headers=AUTH, timeout=30).json()["data"]
        status = run["status"]
        elapsed = time.time() - t0
        print(f"      ...{status} ({elapsed:.0f}s)")
        if elapsed > timeout_seconds:
            print("      polling timeout; aborting wait")
            break

    items = []
    ds = run.get("defaultDatasetId")
    if ds:
        r = requests.get(f"{API}/datasets/{ds}/items", headers=AUTH,
                         params={"format": "json", "clean": "false"}, timeout=180)
        r.raise_for_status()
        items = r.json()

    print(f"    status={run.get('status')} items={len(items)} cost=${run.get('usageTotalUsd')}")
    return run, items


def fetch_run(run_id):
    """Re-read an already-completed run and its dataset. Costs nothing -- used to
    re-analyse a run we already paid for rather than billing the same query twice."""
    run = requests.get(f"{API}/actor-runs/{run_id}", headers=AUTH, timeout=30).json()["data"]
    items = []
    ds = run.get("defaultDatasetId")
    if ds:
        r = requests.get(f"{API}/datasets/{ds}/items", headers=AUTH,
                         params={"format": "json", "clean": "false"}, timeout=180)
        r.raise_for_status()
        items = r.json()
    print(f"  [reused run {run_id}] status={run.get('status')} items={len(items)} "
          f"cost=${run.get('usageTotalUsd')} (no new charge)")
    return run, items


def run_meta(run, actor_key, run_input):
    """Provenance block stored alongside every raw result."""
    return {
        "actor_id": ACTORS[actor_key]["id"],
        "actor_name": ACTORS[actor_key]["name"],
        "run_id": run.get("id"),
        "status": run.get("status"),
        "started_at": run.get("startedAt"),
        "finished_at": run.get("finishedAt"),
        "dataset_id": run.get("defaultDatasetId"),
        "usage_total_usd": run.get("usageTotalUsd"),
        "run_input": run_input,
    }


def classify_record(rec):
    """
    Bucket a returned record by its SHAPE only. No relevance judgement, no
    topic classification -- this only answers "is this a post, a group, a page,
    or an error record?", which is the whole question in Task 2.
    """
    if not isinstance(rec, dict):
        return "unknown"
    if rec.get("error") or rec.get("errorDescription"):
        return "error"
    url = str(rec.get("url") or rec.get("facebookUrl") or rec.get("pageUrl") or "")
    has_text = bool(rec.get("text") or rec.get("message") or rec.get("post_text"))
    if "/permalink/" in url or "/posts/" in url or "story_fbid" in url or "/videos/" in url:
        return "post"
    if rec.get("postId") or rec.get("post_id") or rec.get("feedbackId"):
        return "post"
    if "/groups/" in url:
        return "post" if has_text else "group"
    if rec.get("groupId") or rec.get("group_id"):
        return "group"
    if rec.get("likes") or rec.get("followers") or rec.get("categories") or rec.get("pageId"):
        return "page"
    if has_text:
        return "post"
    return "unknown"


def save(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  saved: {path}")
