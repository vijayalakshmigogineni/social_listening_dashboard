import json

with open("uhc/uhc_activities_top100.json", encoding="utf-8") as f:
    records = json.load(f)

assert len(records) == 100, len(records)

PAIN_PROC_MAP = [
    ("Epidural Steroid Injections", "ESI"),
    ("Facet Joint", "Facet Joint Injection"),
    ("Sacroiliac Joint", "SI Joint"),
    ("Sympathetic Blockade", "Sympathetic Blockade"),
    ("Occipital Nerve", "Occipital Nerve Block/Ablation"),
    ("Percutaneous Neuroablation", "Neuroablation"),
    ("Spinal Fusion", "Spinal Fusion/Decompression"),
    ("Total Artificial Disc Replacement", "Disc Replacement"),
    ("Spinal Cord Stimulators", "SCS"),
    ("Electrical Stimulators", "PNS/Electrical Stimulation"),
    ("Implanted Spinal Drug Delivery", "Intrathecal Pump"),
    ("Pain Management", "Pain Management (general)"),
]

rows = []

for rec in records:
    title = rec["title"]
    desc = rec.get("description") or ""
    item_type = rec["item_type"]
    source_page = rec["source_page"]
    text_l = (title + " " + desc).lower()

    row = {
        "source": "UHC",
        "source_type": "Payer public policy site (uhcprovider.com)",
        "record_id": rec["url"],
        "record_date": rec["last_published_iso"],
        "title": title,
        "text_or_description": desc if desc else "(no per-item description on listing page; title is the only available text)",
        "url": rec["url"],
        "payer": "UnitedHealthcare",
        "procedure": None,
        "topic": None,
        "duplicate_or_repost": "No",
        "signal_categories": [],
        "signal_types": [],
        "direct_or_supporting": None,
        "classification_reason": None,
        "evidence_quote_or_field": None,
    }

    for needle, proc in PAIN_PROC_MAP:
        if needle.lower() in text_l:
            row["procedure"] = proc
            break

    if item_type == "bulletin_archive_index":
        row["direct_or_supporting"] = "Irrelevant"
        row["classification_reason"] = ("This is a static index/archive pointer document ('a listing of the Medical Policy "
            "Update Bulletins for the past two rolling years'), not itself a policy or a description of any specific "
            "change -- no coverage/authorization/reimbursement content to classify.")
        row["evidence_quote_or_field"] = f"item_type={item_type}; description={desc!r}"

    elif item_type == "policy_update_bulletin":
        row["direct_or_supporting"] = "D"
        row["signal_categories"] = ["Coverage / Policy"]
        row["signal_types"] = ["Policy revision", "Effective-date change"]
        row["topic"] = "Monthly policy update bulletin"
        row["classification_reason"] = ("UHC's own monthly bulletin explicitly stating it documents 'recently approved, "
            "revised, and/or retired' policies -- this is the project's own defined UHC activity type ('monthly policy "
            "update') and is a direct, authoritative record of policy change, though it is a roll-up notice rather than "
            "a single-procedure change so no procedure-specific signal is assigned.")
        row["evidence_quote_or_field"] = desc or title

    elif source_page == "commercial_reimbursement":
        row["direct_or_supporting"] = "D"
        row["signal_categories"] = ["Reimbursement / Payment"]
        row["signal_types"] = ["Payment rule"]
        row["topic"] = "Reimbursement / billing policy"
        reason = ("This is an official, named UnitedHealthcare Reimbursement Policy document title (the formal payer "
                  "billing-rule document itself, not incidental text) -- by definition it sets a payment/billing rule "
                  "for the named service category.")
        if "frequency" in text_l:
            row["signal_categories"].append("Procedure / Device Access")
            row["signal_types"].append("Frequency restriction")
            row["signal_categories"].append("Authorization / Utilization Management")
            row["signal_types"].append("Frequency restriction (UM)")
            reason += " Title explicitly names a per-day/multiple-service 'Frequency' limit, which is both a payment rule and a utilization/frequency restriction."
        row["classification_reason"] = reason
        row["evidence_quote_or_field"] = title

    else:
        # commercial_medical or medicare_advantage individual policy with real description text
        row["direct_or_supporting"] = "D"
        row["signal_categories"] = ["Coverage / Policy", "Procedure / Device Access"]
        row["signal_types"] = ["Procedure/device coverage", "Procedure coverage"]
        row["topic"] = "Medical/coverage policy"
        reason = ("Official UHC coverage-policy document defining which CPT/HCPCS codes are covered and under what "
                  "clinical scope for this service -- description text explicitly states coverage scope and lists "
                  "applicable procedure codes.")

        if "precertification" in text_l or "evicore" in text_l:
            row["signal_categories"].append("Authorization / Utilization Management")
            row["signal_types"].append("PA requirement")
            reason += " Description explicitly states the service 'requires precertification' via eviCore, a direct utilization-management/prior-authorization signal."
        if "step therapy" in text_l:
            row["signal_categories"].append("Authorization / Utilization Management")
            row["signal_types"].append("Step therapy")
            reason += " Description explicitly names 'step therapy programs'."
        if "review at launch" in text_l or ("review" in text_l and "new to market" in text_l):
            row["signal_categories"].append("Authorization / Utilization Management")
            row["signal_types"].append("Utilization restriction")
            reason += " Policy requires utilization review of new-to-market provider-administered drugs before use/coverage."
        if any(dev in text_l for dev in ["stimulator", "stimulation device", "drug delivery system", "ventricular assist device", "deep brain"]):
            row["signal_categories"] = list(set(row["signal_categories"] + ["Procedure / Device Access"]))
            if "Device coverage" not in row["signal_types"]:
                row["signal_types"].append("Device coverage")
            reason += " Description concerns an implanted/durable medical device (not just a procedure), so a device-coverage signal is also assigned."

        row["signal_categories"] = list(dict.fromkeys(row["signal_categories"]))
        row["signal_types"] = list(dict.fromkeys(row["signal_types"]))
        row["classification_reason"] = reason
        row["evidence_quote_or_field"] = desc if desc else title

    rows.append(row)

with open("classified_rows_uhc.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2, ensure_ascii=False)

# ---- summary ----
from collections import Counter
ds = Counter(r["direct_or_supporting"] for r in rows)
print("D/S/Irrelevant breakdown:", dict(ds))

cat_counts = Counter()
for r in rows:
    if r["direct_or_supporting"] in ("D", "S"):
        for c in r["signal_categories"]:
            cat_counts[c] += 1
print("Signal category counts (D+S items, multi-label):", dict(cat_counts))
print("Total D+S:", sum(1 for r in rows if r["direct_or_supporting"] in ("D","S")))
