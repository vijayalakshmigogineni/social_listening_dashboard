import json
from collections import Counter

with open("aetna/aetna_cpb_changes_top100.json", encoding="utf-8") as f:
    payload = json.load(f)

records = payload["records"]
assert len(records) == 100, len(records)

DEVICE_WORDS = ["orthoses", "afo", "kafo", "prosthesis", "wheelchair", "scooter", "walker",
    "cane", "crutch", "monitor", "stimulator", "pump", "implant", "cochlear", "traction",
    "telescreening", "chairs", "device", "devices", "simulators", "assist devices"]

STATUS_MAP = {
    "01-New": ("New CPB", ["Coverage change", "Procedure/device coverage"]),
    "02-Revised": ("Revised CPB", ["Policy revision"]),
    "03-Updated": ("Updated CPB", ["Policy revision"]),
    "04-Deleted": ("Deleted/retired CPB", ["Coverage change"]),
}

rows = []
for rec in records:
    name = rec["cpb_name"]
    status = rec["status"]
    name_l = name.lower()

    activity_label, coverage_signal_types = STATUS_MAP[status]

    row = {
        "source": "Aetna",
        "source_type": "Payer public policy feed (aetna.com CPB 'what's new' XML)",
        "record_id": f"CPB-{rec['cpb_number']}-{rec['date_iso']}",
        "record_date": rec["date_iso"],
        "title": f"CPB {rec['cpb_number']} - {name} ({activity_label})",
        "text_or_description": f"Aetna Clinical Policy Bulletin (CPB) {rec['cpb_number']} '{name}' -- status: {status}. "
                                f"(Only the official change-log status/date/title are available; the full CPB body "
                                f"text was not fetched, so no criteria-level detail beyond the CPB subject is claimed.)",
        "url": rec["url"] or f"https://www.aetna.com/cpb/medical/data/ (CPB {rec['cpb_number']}, page removed -- deleted CPB)",
        "payer": "Aetna",
        "procedure": name,
        "topic": "Clinical Policy Bulletin change log",
        "duplicate_or_repost": "No",
        "direct_or_supporting": "D",
        "signal_categories": ["Coverage / Policy"],
        "signal_types": list(coverage_signal_types),
        "classification_reason": (
            f"Aetna's own official CPB change-log entry with explicit status code '{status}' -- this is a first-party, "
            f"authoritative record that this specific coverage policy was itself changed on {rec['date_iso']}. This is "
            f"the project's defined Aetna activity type ('{activity_label.lower()}'). No claim is made about *what* "
            f"clinical criteria changed inside the CPB (body text not retrieved), only that Aetna's own log confirms "
            f"a policy-change event occurred for this named CPB."
        ),
        "evidence_quote_or_field": f"status={status}; cpb={rec['cpb_number']} - {name}; date={rec['date_iso']}",
    }

    if any(w in name_l for w in DEVICE_WORDS):
        row["signal_categories"].append("Procedure / Device Access")
        row["signal_types"].append("Device coverage")
        row["classification_reason"] += " CPB subject names a physical device/DME/equipment, so a device-coverage signal is also assigned."
    else:
        row["signal_categories"].append("Procedure / Device Access")
        row["signal_types"].append("Procedure coverage")
        row["classification_reason"] += " CPB subject names a specific procedure/drug/service, so a procedure-coverage signal is also assigned."

    row["signal_categories"] = list(dict.fromkeys(row["signal_categories"]))
    row["signal_types"] = list(dict.fromkeys(row["signal_types"]))
    rows.append(row)

with open("classified_rows_aetna.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2, ensure_ascii=False)

ds = Counter(r["direct_or_supporting"] for r in rows)
print("D/S/Irrelevant breakdown:", dict(ds))
cat_counts = Counter()
for r in rows:
    for c in r["signal_categories"]:
        cat_counts[c] += 1
print("Signal category counts (multi-label):", dict(cat_counts))
print("status breakdown in top100:", Counter(r["record_id"].split('-')[-1] for r in records) if False else Counter(r["status"] for r in records))
