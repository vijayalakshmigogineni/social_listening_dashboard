import json
from collections import Counter

DEVICE_WORDS = ["stimulator", "stimulation device", "pump", "implant", "prosthesis", "monitor",
                "valve", "device", "orthoses", "wheelchair", "tavr", "cgm", "glucose monitor"]

def classify_file(path, source_label, default_payer):
    with open(path, encoding="utf-8") as f:
        records = json.load(f)
    assert len(records) == 100, (path, len(records))

    rows = []
    for rec in records:
        dtype = rec.get("document_type")
        title = rec.get("title") or ""
        title_l = title.lower()
        payer = rec.get("contractor_name_type")
        if payer:
            payer = payer.replace("\r\n", " ").strip()
        else:
            payer = default_payer

        date = rec.get("updated_on") or rec.get("last_updated") or ""
        # normalize MM/DD/YYYY -> YYYY-MM-DD for record_date where possible
        record_date = date
        if date and "/" in date:
            mm, dd, yyyy = date.split("/")
            record_date = f"{yyyy}-{mm}-{dd}"

        row = {
            "source": source_label,
            "source_type": "CMS Medicare Coverage Database API (api.coverage.cms.gov) -- official government coverage-policy records",
            "record_id": rec.get("document_display_id"),
            "record_date": record_date,
            "title": title,
            "text_or_description": rec.get("note") or rec.get("whats_new_description") or "(no free-text description field returned by this endpoint beyond title)",
            "url": rec.get("url"),
            "payer": payer,
            "procedure": None,
            "topic": None,
            "duplicate_or_repost": "No",
            "direct_or_supporting": "D",
            "signal_categories": [],
            "signal_types": [],
            "classification_reason": None,
            "evidence_quote_or_field": f"document_type={dtype}; document_display_id={rec.get('document_display_id')}; updated={date}",
        }

        is_device = any(w in title_l for w in DEVICE_WORDS)

        if dtype == "LCD":
            proc_name = title.split(" - ")[0] if " - " in title else title
            row["procedure"] = proc_name
            row["topic"] = "Local Coverage Determination (LCD)"
            row["signal_categories"] = ["Coverage / Policy", "Documentation / Medical Necessity",
                                         "Procedure / Device Access"]
            row["signal_types"] = ["LCD/NCD change", "Policy revision", "Clinical criteria",
                                    "Device coverage" if is_device else "Procedure medical necessity"]
            row["classification_reason"] = ("An LCD is, by CMS's own regulatory definition (42 CFR 400.202), a "
                "contractor-wide determination of whether an item/service is 'reasonable and necessary' -- i.e. an "
                "LCD's substantive content IS coverage criteria + medical-necessity criteria by definition, not an "
                "inference from title keywords. Appearing in the MAC's own 'recently updated' LCD list is direct, "
                "authoritative evidence of an active local coverage record.")

        elif dtype == "Article" and title_l.startswith("billing and coding"):
            proc_name = title.split(":", 1)[1].strip() if ":" in title else title
            row["procedure"] = proc_name
            row["topic"] = "Billing & Coding Article"
            row["signal_categories"] = ["Coverage / Policy", "Documentation / Medical Necessity",
                                         "Procedure / Device Access"]
            row["signal_types"] = ["Procedure/device coverage", "Documentation requirement",
                                    "Device coverage" if is_device else "Procedure coverage"]
            row["classification_reason"] = ("CMS 'Billing and Coding' articles operationalize an associated LCD: they "
                "specify covered HCPCS/CPT codes, ICD-10 support, and required documentation elements for the named "
                "procedure/service. This is the article's defined, standard function per CMS's own MCD documentation "
                "-- not an inference from incidental wording.")

        elif dtype == "Article" and title_l.startswith("response to comments"):
            proc_name = title.split(":", 1)[1].strip() if ":" in title else title
            row["procedure"] = proc_name
            row["topic"] = "Response to Comments (LCD finalization record)"
            row["signal_categories"] = ["Coverage / Policy"]
            row["signal_types"] = ["LCD/NCD change", "Policy revision"]
            row["classification_reason"] = ("A 'Response to Comments' article is CMS's formal record of the "
                "notice-and-comment process finalizing or revising the associated LCD -- direct evidence of a "
                "coverage-policy governance action, per CMS MCD's own document taxonomy.")

        elif dtype == "Article":
            proc_name = title
            row["procedure"] = proc_name
            row["topic"] = "Coverage Article (other)"
            row["signal_categories"] = ["Coverage / Policy"]
            row["signal_types"] = ["Procedure/device coverage"]
            row["classification_reason"] = "MCD coverage Article associated with a local coverage record; classified conservatively on Coverage/Policy only since title does not match the standard Billing-and-Coding or Response-to-Comments patterns."

        elif dtype in ("NCA", "NCD"):
            proc_name = title
            row["procedure"] = proc_name
            row["topic"] = "National Coverage Analysis/Determination"
            row["signal_categories"] = ["Coverage / Policy", "Procedure / Device Access"]
            row["signal_types"] = ["LCD/NCD change", "Coverage change",
                                    "Device coverage" if is_device else "Procedure coverage"]
            desc = rec.get("whats_new_description", "")
            row["classification_reason"] = (f"National Coverage Analysis/Determination process record -- CMS's own "
                f"'What's New' national feed description states: '{desc}'. This is a direct, first-party record of "
                f"CMS national coverage-policy activity for the named item/procedure.")

        else:
            row["direct_or_supporting"] = "Irrelevant"
            row["classification_reason"] = f"Unrecognized document_type '{dtype}' with no clear coverage/RCM content."

        row["signal_categories"] = list(dict.fromkeys(row["signal_categories"]))
        row["signal_types"] = list(dict.fromkeys(row["signal_types"]))
        rows.append(row)

    return rows


all_out = {}
for path, label, payer in [
    ("cms/cms_activity.json", "CMS", "CMS (multi-MAC national aggregate -- see contractor_name_type per record)"),
    ("noridian/noridian_activity.json", "Noridian", "Noridian Healthcare Solutions, LLC"),
    ("novitas/novitas_activity.json", "Novitas", "Novitas Solutions, Inc."),
]:
    rows = classify_file(path, label, payer)
    out_name = f"classified_rows_{label.lower()}.json"
    with open(out_name, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    ds = Counter(r["direct_or_supporting"] for r in rows)
    cat_counts = Counter()
    for r in rows:
        for c in r["signal_categories"]:
            cat_counts[c] += 1
    print(f"=== {label} ===")
    print("D/S/Irrelevant:", dict(ds))
    print("Signal categories:", dict(cat_counts))
    print()
