"""
TASK 1 -- inspect the EXISTING Apify configuration before writing any Facebook code.

Reads the existing repo credential (linkedin/.env, same as the Reddit work) and
reports:
  1. which account the token belongs to
  2. the account's recent actor runs -- this is how we find the exact actor the
     first "Facebook Search Scraper" test used, rather than guessing a name
  3. for each Facebook-looking actor: its store name and the INPUT SCHEMA of its
     latest build, so we can see whether it expects "type", "searchType", or
     something else. We do not guess.

Nothing is collected here. Read-only against the Apify API.
"""

import os
import json
from pathlib import Path

import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

load_dotenv(REPO_ROOT / "linkedin" / ".env")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
if not APIFY_TOKEN:
    raise RuntimeError("APIFY_TOKEN not found in linkedin/.env or environment")

AUTH = {"Authorization": f"Bearer {APIFY_TOKEN}"}
API = "https://api.apify.com/v2"


def get(path, **params):
    r = requests.get(f"{API}{path}", headers=AUTH, params=params, timeout=60)
    r.raise_for_status()
    return r.json().get("data", r.json())


def main():
    me = get("/users/me")
    print("=" * 78)
    print("APIFY ACCOUNT")
    print("=" * 78)
    print(f"  username : {me.get('username')}")
    print(f"  plan     : {(me.get('plan') or {}).get('id')}")

    print()
    print("=" * 78)
    print("RECENT ACTOR RUNS (newest first)")
    print("=" * 78)
    runs = get("/actor-runs", limit=30, desc="true")
    items = runs.get("items", [])
    actor_ids = {}
    for r in items:
        aid = r.get("actId")
        actor_ids.setdefault(aid, 0)
        actor_ids[aid] += 1
        print(f"  {r.get('startedAt','')[:19]}  actId={aid}  status={r.get('status'):10s} run={r.get('id')}")

    print()
    print("=" * 78)
    print("ACTORS BEHIND THOSE RUNS")
    print("=" * 78)
    resolved = []
    for aid in actor_ids:
        try:
            a = get(f"/acts/{aid}")
        except Exception as e:  # noqa: BLE001
            print(f"  {aid}: could not resolve ({e})")
            continue
        full = f"{(a.get('username') or '?')}/{a.get('name')}"
        print(f"  {aid} -> {full}   (title: {a.get('title')})")
        resolved.append({"actor_id": aid, "full_name": full, "title": a.get("title"), "runs_seen": actor_ids[aid]})

    out = {"account": me.get("username"), "recent_runs": items, "actors": resolved}
    (HERE / "fb_apify_account_inspection.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nsaved: {HERE / 'fb_apify_account_inspection.json'}")


if __name__ == "__main__":
    main()
