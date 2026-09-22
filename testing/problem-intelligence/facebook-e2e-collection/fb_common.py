"""
Shared Apify plumbing for the Facebook END-TO-END collection test.

Scope: DISCOVERY -> COLLECTION -> COMMENTS -> NORMALIZATION only.
No classification, no intelligence layer, no database.

CREDENTIALS
    The Apify token is read from the environment (or from the repo's existing
    linkedin/.env). It is never printed, copied, or written into any output file.

        APIFY_TOKEN1   default -- account 'bewildered_temperature_xvn'
        APIFY_TOKEN    override with:  set FB_APIFY_TOKEN_VAR=APIFY_TOKEN

BILLING GUARD
    Both known accounts are Apify FREE plan with a $5/cycle ceiling. Every run
    goes out with an explicit maxItems + maxTotalChargeUsd cap, and check_budget()
    refuses to start a run that the remaining allowance cannot absorb.

ACTORS
    The four actors named for this test. Their input schemas are NOT assumed --
    fb_00_inspect_schemas.py reads the live schema from each actor's latest build
    and every later script is written against what that inspection actually found.
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
# quotes. Without this, printing a real post raises UnicodeEncodeError.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

load_dotenv(REPO_ROOT / "linkedin" / ".env")

TOKEN_VAR = os.getenv("FB_APIFY_TOKEN_VAR", "APIFY_TOKEN1")
APIFY_TOKEN = os.getenv(TOKEN_VAR) or os.getenv("APIFY_TOKEN")
if not APIFY_TOKEN:
    raise RuntimeError(
        f"{TOKEN_VAR} is not set. Put it in the environment or in linkedin/.env. "
        "Never hardcode the token in a script."
    )

AUTH = {"Authorization": f"Bearer {APIFY_TOKEN}"}
API = "https://api.apify.com/v2"

# The four actors named for this test, by slug. IDs are resolved at runtime from
# the slug so a renamed/republished actor does not silently break the pipeline.
ACTORS = {
    "search_scrapesmith": {
        "slug": "scrapesmith/facebook-search-scraper",
        "role": "DISCOVERY -- keyword search for posts / pages / groups",
    },
    "search_parseforge": {
        "slug": "parseforge/facebook-search-scraper",
        "role": "DISCOVERY (comparison) -- second keyword search actor",
    },
    "page_thedoor": {
        "slug": "thedoor/facebook-page-scraper",
        "role": "COLLECTION -- posts/details from a Page URL or a post URL",
    },
    "comments_apify": {
        "slug": "apify/facebook-comments-scraper",
        "role": "COMMENTS -- comments from post URLs",
    },
}

SEARCH_QUERIES = [
    "medical claim denial",
    "insurance denial",
    "prior authorization",
    "denied claim",
    "reimbursement problem",
    "medical billing problem",
    "revenue cycle management",
    "payer denial",
    "insurance verification",
    "delayed payment",
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_json(url, params=None, tries=4, timeout=60):
    """
    GET + .json() with retries.

    Apify's API intermittently drops a long poll (observed as a urllib3
    ReadTimeoutError mid-run). Without a retry the script dies AFTER the actor
    run has already been billed, which is the one failure mode worth engineering
    against on a $5/month allowance.
    """
    last = None
    for attempt in range(tries):
        try:
            r = requests.get(url, headers=AUTH, params=params, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:                      # noqa: BLE001 - retry on anything
            last = e
            wait = 3 * (attempt + 1)
            print(f"      [retry {attempt + 1}/{tries}] {type(e).__name__}; "
                  f"waiting {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"GET {url} failed after {tries} tries: {last}")


def actor_id(key):
    """Resolve 'user/name' -> actor id, cached per process."""
    meta = ACTORS[key]
    if "_id" not in meta:
        slug = meta["slug"].replace("/", "~")
        r = requests.get(f"{API}/acts/{slug}", headers=AUTH, timeout=30)
        r.raise_for_status()
        meta["_id"] = r.json()["data"]["id"]
    return meta["_id"]


def budget():
    """(used_usd, cap_usd, remaining_usd) for the current monthly cycle."""
    d = get_json(f"{API}/users/me/limits")["data"]
    used = d["current"]["monthlyUsageUsd"]
    cap = d["limits"]["maxMonthlyUsageUsd"]
    return used, cap, cap - used


def check_budget(need_usd, floor_usd=0.02):
    """Refuse to start a run the remaining allowance cannot absorb."""
    used, cap, remaining = budget()
    print(f"  [budget] used ${used:.4f} / ${cap} -> ${remaining:.4f} remaining")
    if remaining - need_usd < floor_usd:
        raise RuntimeError(
            f"REFUSING TO RUN: estimated ${need_usd:.4f} would leave less than "
            f"${floor_usd:.4f} of the ${cap} monthly allowance "
            f"(${remaining:.4f} remaining). Stop and re-plan."
        )
    return remaining


def run_actor(actor_key, run_input, max_items=None, max_charge_usd=None,
              poll_seconds=5, timeout_seconds=600, label="", resume_run_id=None):
    """
    Start an actor run with hard caps, poll to completion, return (run, items).
    Never raises on a FAILED run -- a failure is itself a finding we must record.

    resume_run_id: attach to an already-started run instead of starting a new
    one. Used when a poll died on a network blip after the run was billed --
    the same query must never be paid for twice on a $5 allowance.
    """
    meta = ACTORS[actor_key]
    aid = actor_id(actor_key)

    if resume_run_id:
        print(f"  [{meta['slug']}] RESUMING run {resume_run_id} (no new charge)")
        run = get_json(f"{API}/actor-runs/{resume_run_id}")["data"]
        items = fetch_dataset(run.get("defaultDatasetId"))
        print(f"    status={run.get('status')} items={len(items)} "
              f"cost=${run.get('usageTotalUsd')}")
        return run, items

    params = {}
    if max_items is not None:
        params["maxItems"] = max_items
    if max_charge_usd is not None:
        params["maxTotalChargeUsd"] = max_charge_usd

    print(f"  [{meta['slug']}] {label}")
    print(f"    input: {json.dumps(run_input)[:400]}")
    print(f"    caps : maxItems={max_items} maxTotalChargeUsd={max_charge_usd}")

    start = requests.post(
        f"{API}/acts/{aid}/runs",
        headers={**AUTH, "Content-Type": "application/json"},
        params=params,
        data=json.dumps(run_input),
        timeout=60,
    )
    if not start.ok:
        print(f"    START FAILED {start.status_code}: {start.text[:500]}")
        return {"status": "START_REJECTED",
                "http_status": start.status_code,
                "error_body": start.text[:1000]}, []

    run = start.json()["data"]
    run_id = run["id"]
    print(f"    run started: {run_id}")

    t0 = time.time()
    status = run["status"]
    while status not in ("SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"):
        time.sleep(poll_seconds)
        run = get_json(f"{API}/actor-runs/{run_id}")["data"]
        status = run["status"]
        elapsed = time.time() - t0
        print(f"      ...{status} ({elapsed:.0f}s)")
        if elapsed > timeout_seconds:
            print("      polling timeout; aborting wait")
            break

    items = fetch_dataset(run.get("defaultDatasetId"))
    print(f"    status={run.get('status')} items={len(items)} cost=${run.get('usageTotalUsd')}")
    return run, items


def fetch_dataset(dataset_id):
    if not dataset_id:
        return []
    return get_json(f"{API}/datasets/{dataset_id}/items",
                    params={"format": "json", "clean": "false"}, timeout=180)


def run_log(run, max_chars=3000):
    """Actor log tail -- this is where free-plan gates and silent caps show up."""
    rid = run.get("id")
    if not rid:
        return None
    r = requests.get(f"{API}/logs/{rid}", headers=AUTH, timeout=30)
    if not r.ok:
        return None
    return r.text[-max_chars:]


def run_meta(run, actor_key, run_input):
    """Provenance block stored alongside every raw result."""
    return {
        "actor_slug": ACTORS[actor_key]["slug"],
        "actor_id": ACTORS[actor_key].get("_id"),
        "run_id": run.get("id"),
        "status": run.get("status"),
        "started_at": run.get("startedAt"),
        "finished_at": run.get("finishedAt"),
        "dataset_id": run.get("defaultDatasetId"),
        "usage_total_usd": run.get("usageTotalUsd"),
        "http_status": run.get("http_status"),
        "error_body": run.get("error_body"),
        "run_input": run_input,
    }


def save(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  saved: {path}")


def load(path):
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
