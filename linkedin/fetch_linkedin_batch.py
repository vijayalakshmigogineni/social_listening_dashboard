import os
import sys
import json
import time
import requests
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
if not APIFY_TOKEN:
    raise ValueError("APIFY_TOKEN is missing from .env")

ACTOR_ID = "Wpp1BZ6yGWjySadk3"  # supreme_coder/linkedin-post, same actor as the original pinned run

LIMIT_PER_SOURCE = int(sys.argv[1]) if len(sys.argv) > 1 else 25
OUTPUT_TAG = sys.argv[2] if len(sys.argv) > 2 else f"batch{LIMIT_PER_SOURCE}"

# Broadened multi-payer / multi-procedure query, built from the existing
# PAYERS / PROCEDURES / TOPICS keyword lists already in linkedin/process_linkedin.py.
# NOTE: LinkedIn's search backend rejected a deeply-nested multi-OR-group boolean
# query ("Unknown error when trying to fetch posts") -- confirmed via a failed
# test run. This flatter form (one OR-group + plain keywords) is confirmed working.
QUERY = '(UnitedHealthcare OR Aetna OR Cigna OR Humana OR Medicare) prior authorization denial reimbursement'

search_url = (
    "https://www.linkedin.com/search/results/content/"
    f"?keywords={quote(QUERY)}&origin=FACETED_SEARCH"
)

run_input = {
    "deepScrape": False,   # confirmed: deepScrape=True cost ~$0.50/item (comment/reaction detail);
                            # deepScrape=False cost ~$0.00001/item and still includes text/date/author/likes/comments-count
    "fetchDocumentDetails": False,
    "limitPerSource": LIMIT_PER_SOURCE,
    "numComments": 0,
    "numLikes": 0,
    "rawData": False,
    "urls": [search_url],
}

print("=" * 80)
print(f"Starting Apify run: actor={ACTOR_ID}, limitPerSource={LIMIT_PER_SOURCE}")
print("Search URL:", search_url)
print("=" * 80)

start_resp = requests.post(
    f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs",
    headers={"Authorization": f"Bearer {APIFY_TOKEN}", "Content-Type": "application/json"},
    data=json.dumps(run_input),
    timeout=30,
)
start_resp.raise_for_status()
run = start_resp.json()["data"]
run_id = run["id"]
print("Run started. runId:", run_id, "| initial status:", run["status"])

# Poll until finished
poll_start = time.time()
status = run["status"]
while status not in ("SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"):
    time.sleep(5)
    r = requests.get(
        f"https://api.apify.com/v2/actor-runs/{run_id}",
        headers={"Authorization": f"Bearer {APIFY_TOKEN}"},
        timeout=30,
    )
    r.raise_for_status()
    run = r.json()["data"]
    status = run["status"]
    elapsed = time.time() - poll_start
    print(f"  ...status={status} (elapsed {elapsed:.0f}s)")
    if elapsed > 900:
        print("Polling timeout after 900s, aborting wait loop.")
        break

print("\nFinal status:", status)
print("Real cost fields from Apify run object:")
for key in ("usageTotalUsd", "usageUsd"):
    if key in run:
        print(f"  {key}: {run[key]}")

dataset_id = run.get("defaultDatasetId")
print("defaultDatasetId:", dataset_id)

items_resp = requests.get(
    f"https://api.apify.com/v2/datasets/{dataset_id}/items",
    headers={"Authorization": f"Bearer {APIFY_TOKEN}"},
    params={"format": "json", "clean": "true"},
    timeout=60,
)
items_resp.raise_for_status()
posts = items_resp.json()

output_dir = Path("data/raw")
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / f"linkedin_posts_{OUTPUT_TAG}.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(posts, f, indent=2, ensure_ascii=False)

meta = {
    "actor_id": ACTOR_ID,
    "run_id": run_id,
    "final_status": status,
    "search_url": search_url,
    "run_input": run_input,
    "usageTotalUsd": run.get("usageTotalUsd"),
    "usageUsd": run.get("usageUsd"),
    "startedAt": run.get("startedAt"),
    "finishedAt": run.get("finishedAt"),
    "posts_returned": len(posts),
}
with open(output_dir / f"linkedin_posts_{OUTPUT_TAG}_meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 80)
print("RESULT SUMMARY")
print("=" * 80)
print("Posts returned:", len(posts))
print("Saved to:", output_file)
print("Real Apify cost (usageTotalUsd):", run.get("usageTotalUsd"))
if len(posts) > 0 and run.get("usageTotalUsd") is not None:
    print(f"Cost per item: ${run['usageTotalUsd'] / len(posts):.4f}")
