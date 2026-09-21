"""
TASK 1 (cont.) -- read the EXACT input and output of the two Facebook runs that
already exist on this Apify account, so the re-test is based on what was really
sent, not on a recollection of it.
"""
import os, json
from pathlib import Path
import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent.parent / "linkedin" / ".env")
AUTH = {"Authorization": f"Bearer {os.getenv('APIFY_TOKEN')}"}
API = "https://api.apify.com/v2"

RUNS = ["1RKFVu7v0UleuM3vI", "lwd1sFYEcsEnAx10X"]

out = []
for rid in RUNS:
    run = requests.get(f"{API}/actor-runs/{rid}", headers=AUTH, timeout=60).json()["data"]
    kvs = run.get("defaultKeyValueStoreId")
    inp = requests.get(f"{API}/key-value-stores/{kvs}/records/INPUT", headers=AUTH, timeout=60)
    run_input = inp.json() if inp.ok else {"_error": inp.status_code}
    ds = run.get("defaultDatasetId")
    items = requests.get(f"{API}/datasets/{ds}/items", headers=AUTH,
                         params={"format": "json", "clean": "false"}, timeout=120).json()
    print("=" * 78)
    print(f"RUN {rid}  actor={run.get('actId')}  status={run.get('status')}  cost={run.get('usageTotalUsd')}")
    print("-- INPUT --")
    print(json.dumps(run_input, indent=2)[:2000])
    print(f"-- OUTPUT: {len(items)} items --")
    for i, it in enumerate(items[:6]):
        print(f"  [{i}] keys={sorted(it.keys())}")
        for k in ("id", "facebookId", "name", "title", "url", "facebookUrl", "text", "error", "errorDescription"):
            if k in it:
                v = str(it[k])
                print(f"       {k}: {v[:140]}")
    out.append({"run_id": rid, "actor_id": run.get("actId"), "status": run.get("status"),
                "input": run_input, "item_count": len(items), "items": items})

Path("fb_prior_runs_inspection.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nsaved: fb_prior_runs_inspection.json")
