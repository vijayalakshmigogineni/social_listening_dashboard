import json, re
from collections import Counter

with open("cigna/cigna_policy_updates_latest100.json", encoding="utf-8") as f:
    records = json.load(f)

assert len(records) == 100, len(records)

rows = []
for rec in records:
    section = rec.get("section") or ""
    name = rec.get("policy_name") or ""
    status = rec.get("status") or ""
    comment = rec.get("comment_summary") or ""
    text_l = (name + " " + comment).lower()

    row = {
        "source": "Cigna",
        "source_type": "Payer monthly policy-update bulletin (static.cigna.com PDF, September 2026)",
        "record_id": rec.get("record_id") or f"{rec.get('policy_code')}-{rec.get('effective_date')}",
        "record_date": rec.get("effective_date") or rec.get("posted_date"),
        "title": f"{name} ({status})",
        "text_or_description": comment or "(bulletin table row -- no free-text comment beyond status/date)",
        "url": rec.get("source_url"),
        "payer": "Cigna",
        "procedure": name,
        "topic": section,
        "duplicate_or_repost": "No",
        "direct_or_supporting": "D",
        "signal_categories": ["Coverage / Policy"],
        "signal_types": ["Policy revision"],
        "classification_reason": [f"Official Cigna monthly policy-update bulletin row with explicit status '{status}' "
                                   f"-- a first-party record that this policy was changed."],
        "evidence_quote_or_field": comment[:300] if comment else f"status={status}; section={section}",
    }

    if status == "Retired":
        row["signal_types"].append("Coverage change")
        row["classification_reason"].append("Status 'Retired' -- coverage under this policy is being withdrawn/discontinued.")
    if status == "New":
        row["signal_types"].append("Procedure/device coverage")
        row["classification_reason"].append("Status 'New' -- establishes coverage criteria for a previously ungoverned drug/service.")

    if section == "Cigna Healthcare Drug Coverage Policy":
        if "Procedure/device coverage" not in row["signal_types"]:
            row["signal_types"].append("Procedure/device coverage")
        row["classification_reason"].append("Pharmacy/drug coverage-policy bulletin row -- defines drug coverage criteria.")

    if section in ("eviCore Guidelines", "ASH Guidelines"):
        row["signal_categories"].append("Authorization / Utilization Management")
        row["signal_types"].append("PA requirement")
        row["classification_reason"].append(f"{section} entries govern the clinical criteria used by Cigna's delegated "
            f"utilization-management vendor ({'eviCore' if 'evi' in section else 'American Specialty Health'}) for "
            f"precertification/utilization review of MSK, spine, or chiropractic/PT services.")

    if any(p in text_l for p in ["medically necessary", "coverage criteria", "clinical criteria", "policy statements were revised",
                                   "revised policy statements", "criteria changes"]) and "no criteria changes" not in text_l:
        row["signal_categories"].append("Documentation / Medical Necessity")
        row["signal_types"].append("Clinical criteria")
        row["classification_reason"].append("Comment text explicitly states clinical/coverage criteria were revised.")

    if "reimburse" in text_l:
        row["signal_categories"].append("Reimbursement / Payment")
        row["signal_types"].append("Payment rule")
        row["classification_reason"].append("Comment text explicitly states a reimbursement rule (e.g. 'will not reimburse ... codes').")

    if "quantity management" in text_l or "drug quantity" in text_l:
        row["signal_categories"].append("Authorization / Utilization Management")
        row["signal_types"].append("Frequency restriction")
        row["classification_reason"].append("Drug Quantity Management policy -- a utilization-management frequency/quantity limit.")

    if re.search(r"\bstep\s*1\b|\bstep therapy\b|added to step", text_l):
        row["signal_categories"].append("Authorization / Utilization Management")
        row["signal_types"].append("Step therapy")
        row["classification_reason"].append("Formulary 'Step' tier placement -- a step-therapy utilization requirement.")

    if re.search(r"\bcpt code[s]?\b|\bhcpcs\b|\bcodes? \d{4,5}[a-z]?\b", text_l):
        row["signal_categories"].append("Procedure / Device Access")
        if "Procedure coverage" not in row["signal_types"]:
            row["signal_types"].append("Procedure coverage")
        row["classification_reason"].append("Comment text names specific CPT/HCPCS codes affected by this policy change.")

    row["signal_categories"] = list(dict.fromkeys(row["signal_categories"]))
    row["signal_types"] = list(dict.fromkeys(row["signal_types"]))
    row["classification_reason"] = " ".join(row["classification_reason"])
    rows.append(row)

with open("classified_rows_cigna.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2, ensure_ascii=False)

ds = Counter(r["direct_or_supporting"] for r in rows)
print("D/S/Irrelevant:", dict(ds))
cat_counts = Counter()
for r in rows:
    for c in r["signal_categories"]:
        cat_counts[c] += 1
print("Signal categories (multi-label):", dict(cat_counts))
