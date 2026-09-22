import json, csv
from collections import Counter, defaultdict

FILES = [
    "classified_rows_uhc.json",
    "classified_rows_aetna.json",
    "classified_rows_cigna.json",
    "classified_rows_humana.json",
    "classified_rows_noridian.json",
    "classified_rows_novitas.json",
    "classified_rows_cms.json",
    "classified_rows_federal_register.json",
    "classified_rows_linkedin_100.json",
]

SCHEMA = ["source","source_type","record_id","record_date","title","text_or_description","url",
          "direct_or_supporting","signal_categories","signal_types","payer","procedure","topic",
          "duplicate_or_repost","underlying_event_id","classification_reason","evidence_quote_or_field"]

all_rows = []
per_source_raw_count = Counter()
for fname in FILES:
    with open(fname, encoding="utf-8") as f:
        rows = json.load(f)
    for r in rows:
        norm = {k: r.get(k) for k in SCHEMA}
        if norm["duplicate_or_repost"] is None:
            norm["duplicate_or_repost"] = "No"
        if norm["signal_categories"] is None:
            norm["signal_categories"] = []
        if norm["signal_types"] is None:
            norm["signal_types"] = []
        all_rows.append(norm)
        per_source_raw_count[norm["source"]] += 1

print("=== RAW ROW COUNTS PER SOURCE (from classified_rows_*.json) ===")
for s, c in per_source_raw_count.items():
    print(f"  {s}: {c}")
print("TOTAL rows consolidated:", len(all_rows))

# ---- CONSISTENCY CHECK ----
print("\n=== CONSISTENCY CHECK ===")
CATS = ["Authorization / Utilization Management", "Denials / Claims Friction", "Coverage / Policy",
        "Documentation / Medical Necessity", "Reimbursement / Payment", "Procedure / Device Access"]

by_source = defaultdict(list)
for r in all_rows:
    by_source[r["source"]].append(r)

discrepancies = []
summary_table1 = {}
for source, rows in by_source.items():
    total = len(rows)
    d = sum(1 for r in rows if r["direct_or_supporting"] == "D")
    s = sum(1 for r in rows if r["direct_or_supporting"] == "S")
    irr = sum(1 for r in rows if r["direct_or_supporting"] == "Irrelevant")
    ds_total = d + s

    if d + s + irr != total:
        discrepancies.append(f"{source}: D({d})+S({s})+Irrelevant({irr}) = {d+s+irr} != total rows {total}")

    cat_counts = {}
    other_unmapped = 0
    for r in rows:
        if r["direct_or_supporting"] not in ("D", "S"):
            if r["signal_categories"]:
                discrepancies.append(f"{source}/{r['record_id']}: classified as {r['direct_or_supporting']} but has signal_categories {r['signal_categories']} (should be empty)")
            continue
        cats_here = set(r["signal_categories"])
        unmapped_cats = cats_here - set(CATS)
        if unmapped_cats:
            discrepancies.append(f"{source}/{r['record_id']}: unrecognized category label(s) {unmapped_cats}")
        if not cats_here:
            other_unmapped += 1
    for cat in CATS:
        cat_counts[cat] = sum(1 for r in rows if r["direct_or_supporting"] in ("D","S") and cat in (r["signal_categories"] or []))

    # cross-check: does every category count trace to actual records with that exact category string?
    for cat in CATS:
        traced = [r["record_id"] for r in rows if r["direct_or_supporting"] in ("D","S") and cat in (r["signal_categories"] or [])]
        if len(traced) != cat_counts[cat]:
            discrepancies.append(f"{source}/{cat}: count {cat_counts[cat]} does not match traced record list length {len(traced)}")

    summary_table1[source] = {
        "total_activities": total,
        "d": d, "s": s, "irrelevant": irr, "ds_total": ds_total,
        **cat_counts,
        "other_unmapped": other_unmapped,
    }

if discrepancies:
    print("DISCREPANCIES FOUND (reporting, not silently correcting):")
    for disc in discrepancies:
        print(" -", disc)
else:
    print("No discrepancies found: every source's D+S+Irrelevant reconciles to its total row count,")
    print("every signal-category count traces to an explicit list of record_ids carrying that exact category,")
    print("and no Irrelevant record carries a signal category.")

print("\n=== TABLE 1 DATA (per source) ===")
header = ["source","total_activities","ds_total","Authorization / Utilization Management","Denials / Claims Friction",
          "Coverage / Policy","Documentation / Medical Necessity","Reimbursement / Payment","Procedure / Device Access","other_unmapped"]
for s, v in summary_table1.items():
    print(s, {k: v[k] for k in ["total_activities","d","s","irrelevant","ds_total"]+CATS+["other_unmapped"]})

with open("table1_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary_table1, f, indent=2, ensure_ascii=False)

# ---- write master CSV/JSON ----
with open("../signal_distribution_classified.json", "w", encoding="utf-8") as f:
    json.dump(all_rows, f, indent=2, ensure_ascii=False)

with open("../signal_distribution_classified.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=SCHEMA)
    writer.writeheader()
    for r in all_rows:
        row_out = dict(r)
        row_out["signal_categories"] = "; ".join(r["signal_categories"])
        row_out["signal_types"] = "; ".join(r["signal_types"])
        writer.writerow(row_out)

print(f"\nWrote {len(all_rows)} rows to signal_distribution_classified.json/.csv")
