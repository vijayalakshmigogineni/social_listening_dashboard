"""
STEP 0 -- Inspect the CURRENT Apify input schemas for the four named actors.

Nothing here starts an actor run, so this script costs $0.
It answers one question only: what inputs do these actors ACTUALLY accept today?

Run:  python fb_00_inspect_schemas.py
"""
import json
from fb_common import (API, AUTH, ACTORS, save, now_iso, budget, requests, HERE)

OUT = HERE / "facebook_actor_live_schemas.json"


def get_actor(slug):
    """Resolve an actor by 'user/name' slug -> full store record incl. input schema."""
    r = requests.get(f"{API}/acts/{slug.replace('/', '~')}", headers=AUTH, timeout=30)
    if not r.ok:
        return {"slug": slug, "error": f"HTTP {r.status_code}", "body": r.text[:400]}
    d = r.json()["data"]

    # The input schema lives on the actor's default (tagged 'latest') build.
    schema = None
    schema_err = None
    tagged = (d.get("taggedBuilds") or {}).get("latest") or {}
    build_id = tagged.get("buildId")
    if build_id:
        b = requests.get(f"{API}/actor-builds/{build_id}", headers=AUTH, timeout=30)
        if b.ok:
            raw = (b.json()["data"].get("inputSchema"))
            if raw:
                try:
                    schema = json.loads(raw) if isinstance(raw, str) else raw
                except Exception as e:
                    schema_err = f"unparseable inputSchema: {e}"
        else:
            schema_err = f"build HTTP {b.status_code}"
    else:
        schema_err = "no taggedBuilds.latest"

    pricing = d.get("pricingInfos") or []
    current_price = pricing[-1] if pricing else {}

    return {
        "slug": slug,
        "actor_id": d.get("id"),
        "title": d.get("title"),
        "username": d.get("username"),
        "name": d.get("name"),
        "is_public": d.get("isPublic"),
        "total_runs": (d.get("stats") or {}).get("totalRuns"),
        "total_users": (d.get("stats") or {}).get("totalUsers"),
        "last_run_started_at": (d.get("stats") or {}).get("lastRunStartedAt"),
        "pricing_model": current_price.get("pricingModel"),
        "price_per_unit_usd": (current_price.get("pricePerUnitUsd")
                               or current_price.get("unitPriceUsd")),
        "price_detail": current_price,
        "input_schema": schema,
        "input_schema_error": schema_err,
        "example_input": d.get("exampleRunInput"),
    }


def summarize(rec):
    """Flatten the input schema into a readable field list."""
    s = rec.get("input_schema") or {}
    props = s.get("properties") or {}
    required = set(s.get("required") or [])
    out = []
    for k, v in props.items():
        out.append({
            "field": k,
            "type": v.get("type"),
            "editor": v.get("editor"),
            "required": k in required,
            "default": v.get("prefill", v.get("default")),
            "enum": v.get("enum"),
            "enum_titles": v.get("enumTitles"),
            "description": (v.get("description") or "")[:300],
        })
    return out


def main():
    print(f"=== STEP 0: live actor schema inspection ({now_iso()}) ===")
    used, cap, remaining = budget()
    print(f"Apify budget: used ${used:.4f} / ${cap} -> ${remaining:.4f} remaining\n")

    report = {
        "step": "0 - live actor input schema inspection",
        "produced_at": now_iso(),
        "cost_usd": 0.0,
        "note": "Metadata reads only. No actor was started by this script.",
        "budget": {"used_usd": used, "cap_usd": cap, "remaining_usd": remaining},
        "actors": {},
    }

    for key, meta in ACTORS.items():
        slug = meta["slug"]
        print(f"--- {key}: {slug}")
        rec = get_actor(slug)
        rec["fields"] = summarize(rec)
        report["actors"][slug] = rec
        if rec.get("error"):
            print(f"    ERROR {rec['error']}")
            continue
        print(f"    id={rec['actor_id']}  runs={rec['total_runs']}  "
              f"price={rec['pricing_model']} ${rec['price_per_unit_usd']}")
        if rec.get("input_schema_error"):
            print(f"    schema problem: {rec['input_schema_error']}")
        for f in rec["fields"]:
            req = "REQUIRED" if f["required"] else "optional"
            en = f"  enum={f['enum']}" if f["enum"] else ""
            df = f"  default={f['default']!r}" if f["default"] is not None else ""
            print(f"      {f['field']:<28} {str(f['type']):<8} {req}{df}{en}")
        print()

    save(OUT, report)
    print("\nNo runs started. Cost: $0.00")


if __name__ == "__main__":
    main()
