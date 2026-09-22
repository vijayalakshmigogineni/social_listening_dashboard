import json
from collections import Counter

with open("humana/humana_latest_activities.json", encoding="utf-8") as f:
    records = json.load(f)["records"]

assert len(records) == 93, len(records)

seen_names = Counter()
rows = []
for rec in records:
    name = (rec.get("policy_name") or "").replace("�", "'")
    ptype = rec.get("policy_type")
    status = rec.get("status")
    seen_names[name] += 1
    occurrence = seen_names[name]

    row = {
        "source": "Humana",
        "source_type": "Payer public coverage-policy portal (mcp.humana.com Medical & Pharmacy Coverage Policies tool)",
        "record_id": rec.get("object_id"),
        "record_date": rec.get("reviewed_date"),
        "title": f"{name} ({ptype} coverage policy, {status})",
        "text_or_description": f"Humana {ptype} coverage policy '{name}' -- status: {status}, effective date {rec.get('effective_date')}. "
                                f"(Only listing metadata was captured; full policy PDF text was not fetched, so no PA/documentation "
                                f"criteria beyond the policy subject itself is claimed.)",
        "url": rec.get("document_url"),
        "payer": "Humana",
        "procedure": name,
        "topic": f"{ptype.title()} Coverage Policy" if ptype else None,
        "duplicate_or_repost": "No",
        "underlying_event_id": None,
        "direct_or_supporting": "D",
        "signal_categories": ["Coverage / Policy", "Procedure / Device Access"],
        "signal_types": [
            "Policy revision" if status == "Revised" else "Procedure/device coverage",
            "Procedure coverage",
        ],
        "classification_reason": (
            f"Humana's own coverage-policy portal listing with explicit status '{status}' and a Reviewed Date -- a "
            f"first-party record that this named drug/procedure coverage policy was itself reviewed/changed. This is "
            f"the project's defined Humana activity type ('policy update/review/change' / 'pharmacy policy where "
            f"relevant'). No claim is made about specific PA/documentation criteria inside the policy (full PDF text "
            f"not retrieved)."
        ),
        "evidence_quote_or_field": f"policy_type={ptype}; status={status}; reviewed_date={rec.get('reviewed_date')}; effective_date={rec.get('effective_date')}",
    }

    if occurrence > 1:
        row["duplicate_or_repost"] = f"Yes (occurrence #{occurrence} of policy '{name}' -- same policy, different plan/line-of-business version reviewed in the same cycle, per source agent's verification of distinct object_ids)"
        row["underlying_event_id"] = f"HUMANA-POLICY-{name[:40]}"

    rows.append(row)

with open("classified_rows_humana.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2, ensure_ascii=False)

ds = Counter(r["direct_or_supporting"] for r in rows)
print("D/S/Irrelevant:", dict(ds))
cat_counts = Counter()
for r in rows:
    for c in r["signal_categories"]:
        cat_counts[c] += 1
print("Signal categories:", dict(cat_counts))
print("Flagged duplicates:", sum(1 for r in rows if r["duplicate_or_repost"] != "No"))
