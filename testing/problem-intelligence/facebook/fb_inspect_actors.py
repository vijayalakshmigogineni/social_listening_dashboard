"""
TASK 1 (cont.) -- find the available Facebook actors and read their REAL input
schemas from the latest build. This is how we decide between "type",
"searchType", "searchQueries", etc. without guessing.
"""
import os, json
from pathlib import Path
import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent.parent / "linkedin" / ".env")
AUTH = {"Authorization": f"Bearer {os.getenv('APIFY_TOKEN')}"}
API = "https://api.apify.com/v2"

store = requests.get(f"{API}/store", headers=AUTH,
                     params={"search": "facebook", "limit": 60}, timeout=60).json()["data"]["items"]
print("=" * 90)
print("APIFY STORE -- facebook actors")
print("=" * 90)
cands = []
for a in store:
    full = f"{a.get('username')}/{a.get('name')}"
    print(f"  {full:55s} id={a.get('id')}  title={a.get('title')}")
    cands.append(full)

TARGETS = [c for c in cands if any(k in c for k in
           ("facebook-search", "facebook-posts", "facebook-groups", "facebook-pages"))]
print("\nTARGETS:", TARGETS)

schemas = {}
for full in TARGETS:
    aid = full.replace("/", "~")
    try:
        act = requests.get(f"{API}/acts/{aid}", headers=AUTH, timeout=60).json()["data"]
        bid = (act.get("taggedBuilds") or {}).get("latest", {}).get("buildId")
        build = requests.get(f"{API}/actor-builds/{bid}", headers=AUTH, timeout=60).json()["data"]
        schema = json.loads(build.get("inputSchema") or "{}")
    except Exception as e:  # noqa: BLE001
        print(f"\n{full}: schema unavailable ({e})")
        continue
    props = schema.get("properties", {})
    schemas[full] = {"actor_id": act.get("id"), "title": act.get("title"),
                     "pricing": act.get("currentPricingInfo", {}).get("pricingModel"),
                     "input_schema": schema}
    print("\n" + "=" * 90)
    print(f"{full}   id={act.get('id')}   pricing={act.get('currentPricingInfo',{}).get('pricingModel')}")
    print(f"  price: {act.get('currentPricingInfo',{}).get('pricePerUnitUsd')} per {act.get('currentPricingInfo',{}).get('unitName')}")
    print("=" * 90)
    for k, v in props.items():
        line = f"  {k:28s} {v.get('type','?'):8s}"
        if v.get("enum"):
            line += f" enum={v['enum']}"
        if v.get("default") is not None:
            line += f" default={v['default']!r}"
        print(line)
        d = (v.get("description") or "").replace("\n", " ")
        if d:
            print(f"      {d[:150]}")
    print(f"  REQUIRED: {schema.get('required')}")

Path("fb_actor_schemas.json").write_text(json.dumps(schemas, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nsaved: fb_actor_schemas.json")
