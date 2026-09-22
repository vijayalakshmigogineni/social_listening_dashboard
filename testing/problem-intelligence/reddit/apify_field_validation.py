"""
Reddit / Apify FIELD VALIDATION experiment.

Purpose: determine whether the data returned by a current Apify Reddit Actor
contains the fields the PainMed-PA SLD canonical schema needs. This is a
data-validation experiment, NOT a production collector and NOT a statement
about Reddit authorization.

Actor: harshmaur/reddit-scraper-pro  (actor id 3XedXIRBcjfKrnsDJ)

Three bounded runs:
  R1  keyword search, posts only          -> ~36 posts
  R2  comments for 4 posts chosen from R1 -> <=160 comments
  R3  historical date-window search       -> ~15 posts from a 2024 window

Raw actor responses are written untouched to data/raw/validation/.
Nothing is normalised or filtered here; inspection happens separately.

Usage:
    python problem-intelligence/apify_field_validation.py r1
    python problem-intelligence/apify_field_validation.py r2
    python problem-intelligence/apify_field_validation.py r3
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

# Reuse the existing repo credential; never printed, never copied.
load_dotenv(REPO_ROOT / "linkedin" / ".env")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
if not APIFY_TOKEN:
    raise RuntimeError("APIFY_TOKEN not set (expected in linkedin/.env)")

ACTOR_ID = "3XedXIRBcjfKrnsDJ"          # harshmaur/reddit-scraper-pro
ACTOR_SLUG = "harshmaur~reddit-scraper-pro"

OUT_DIR = HERE / "data" / "raw" / "validation"
OUT_DIR.mkdir(parents=True, exist_ok=True)

AUTH = {"Authorization": f"Bearer {APIFY_TOKEN}"}

# --------------------------------------------------------------------------
# Test configuration -- recorded verbatim so the run is reproducible
# --------------------------------------------------------------------------

QUERIES = [
    '"prior authorization" pain management',
    '"pain management" claim denial',
    '"pain clinic" billing',
    '"pain management" reimbursement',
    '"epidural steroid injection" denied',
    '"radiofrequency ablation" prior authorization',
    '"pain management" credentialing',
    '"interventional pain" billing',
    '64483 denial',
    '"pain management" insurance verification',
]

R1_INPUT = {
    "searchTerms": QUERIES,
    "searchPosts": True,
    "searchComments": False,
    "searchSort": "relevance",
    "searchTime": "all",
    "crawlCommentsPerPost": False,
    "maxPostsCount": 36,
    "includeNSFW": False,
    "proxy": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]},
}

R3_INPUT = {
    "searchTerms": [
        '"prior authorization" pain management',
        '"pain management" claim denial',
    ],
    "searchPosts": True,
    "searchComments": False,
    "postedAfter": "2024-01-01",
    "postedBefore": "2024-06-30",
    "crawlCommentsPerPost": False,
    "maxPostsCount": 15,
    "includeNSFW": False,
    "proxy": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]},
}


def r2_input(post_urls):
    return {
        "startUrls": [{"url": u} for u in post_urls],
        "searchTerms": [],
        "crawlCommentsPerPost": True,
        "maxCommentsPerPost": 40,
        "maxPostsCount": len(post_urls),
        "fastMode": False,
        "includeNSFW": False,
        "proxy": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]},
    }


# --------------------------------------------------------------------------
# Apify helpers
# --------------------------------------------------------------------------

def run_actor(payload, label, timeout_s=600):
    """Start the actor, poll to completion, return (items, run_meta)."""
    started = datetime.now(timezone.utc).isoformat()
    r = requests.post(
        f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs",
        headers={**AUTH, "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    run = r.json()["data"]
    run_id = run["id"]
    print(f"[{label}] run {run_id} started")

    deadline = time.time() + timeout_s
    status = run["status"]
    while status in ("READY", "RUNNING") and time.time() < deadline:
        time.sleep(10)
        s = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}", headers=AUTH, timeout=60
        )
        s.raise_for_status()
        run = s.json()["data"]
        status = run["status"]
        print(f"[{label}] status={status}")

    ds = run.get("defaultDatasetId")
    items = []
    if ds:
        d = requests.get(
            f"https://api.apify.com/v2/datasets/{ds}/items",
            headers=AUTH,
            params={"clean": "false", "format": "json"},
            timeout=120,
        )
        d.raise_for_status()
        items = d.json()

    meta = {
        "label": label,
        "actor": ACTOR_SLUG,
        "actor_id": ACTOR_ID,
        "run_id": run_id,
        "status": status,
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "stats": run.get("stats"),
        "usage_total_usd": run.get("usageTotalUsd"),
        "input": payload,
        "returned": len(items),
    }
    print(f"[{label}] status={status} items={len(items)} "
          f"cost=${run.get('usageTotalUsd')}")
    return items, meta


def save(label, items, meta):
    path = OUT_DIR / f"{label}.json"
    if path.exists():
        path = OUT_DIR / f"{label}_{int(time.time())}.json"
    path.write_text(
        json.dumps({"meta": meta, "items": items}, indent=1, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[{label}] wrote {path} ({len(items)} items)")
    return path


# --------------------------------------------------------------------------

def main():
    which = (sys.argv[1] if len(sys.argv) > 1 else "r1").lower()

    if which == "r1":
        items, meta = run_actor(R1_INPUT, "r1_search_posts")
        save("r1_search_posts", items, meta)

    elif which == "r2":
        src = json.loads((OUT_DIR / "r1_search_posts.json").read_text(encoding="utf-8"))
        posts = [i for i in src["items"] if i.get("dataType") == "post"]
        # Prefer PROFESSIONAL communities (practice-side voices) over patient
        # communities, then order by comment count so we get a deep tree to
        # test thread reconstruction against.
        PRO = {
            "medicine", "privatepracticedocs", "anesthesiology", "physicianassistant",
            "healthinsurance", "workerscomp", "painmanagement", "codingandbilling",
            "medicalcoding", "healthit", "familymedicine", "nursing", "crna",
        }
        pro = [p for p in posts if (p.get("parsedCommunityName") or "").lower() in PRO]
        pro.sort(key=lambda p: p.get("commentsCount") or 0, reverse=True)
        rest = sorted(posts, key=lambda p: p.get("commentsCount") or 0, reverse=True)
        picked, seen = [], set()
        for p in pro + rest:
            u = p.get("postUrl")
            if u and u not in seen:
                seen.add(u)
                picked.append(p)
            if len(picked) == 4:
                break
        urls = [p["postUrl"] for p in picked]
        for p in picked:
            print(f"    r/{p['parsedCommunityName']}  comments={p.get('commentsCount')}")
        print("[r2] target posts:")
        for u in urls:
            print("   ", u)
        items, meta = run_actor(r2_input(urls), "r2_comments")
        meta["target_post_urls"] = urls
        save("r2_comments", items, meta)

    elif which == "r3":
        items, meta = run_actor(R3_INPUT, "r3_historical")
        save("r3_historical", items, meta)

    else:
        raise SystemExit("usage: apify_field_validation.py [r1|r2|r3]")


if __name__ == "__main__":
    main()
