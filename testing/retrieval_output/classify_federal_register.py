import json
from collections import Counter

with open("federal_register_condensed.json", encoding="utf-8") as f:
    records = json.load(f)

assert len(records) == 100, len(records)

# Explicit, evidence-based per-record classification.
# Keyed by document_number. Anything NOT in this dict defaults to Irrelevant
# (generic PRA/info-collection notices, unrelated-agency actions, etc.)
CLASS = {
    "2026-19061": dict(cat=["Coverage / Policy"], types=["Provider bulletin"],
        reason="CMS approval of DNV's continued hospital-accreditation recognition -- governs which hospitals can participate in Medicare/Medicaid.",
        event="DNV-Hospital-Accreditation-CMS-3483", dup="Yes (final-stage notice of a 2-stage accreditation action; see 2026-06861)"),
    "2026-06861": dict(cat=["Coverage / Policy"], types=["Provider bulletin"],
        reason="CMS notice of RECEIPT of DNV's hospital-accreditation renewal application -- earlier procedural stage of the same accreditation action.",
        event="DNV-Hospital-Accreditation-CMS-3483", dup="Yes (receipt-stage notice; approval published later as 2026-19061)"),
    "2026-19016": dict(cat=["Denials / Claims Friction"], types=["Appeal outcome"],
        reason="Annual adjustment to the Amount-in-Controversy thresholds for Medicare ALJ/judicial-review appeals -- directly governs the claims-appeal process."),
    "2026-19015": dict(cat=["Reimbursement / Payment", "Documentation / Medical Necessity"], types=["Fee schedule", "Documentation requirement"],
        reason="HCPCS Level II public coding meeting -- new/revised codes directly determine what services can be billed and how they map to payment."),
    "2026-18226": dict(cat=["Reimbursement / Payment", "Procedure / Device Access"], types=["Payment rule", "Device coverage"],
        reason="Town hall on FY2028 New Technology Add-On Payment (NTAP) applications under IPPS -- directly about new-technology/device payment eligibility."),
    "2026-17622": dict(cat=["Reimbursement / Payment", "Denials / Claims Friction"], types=["Payment rule", "Appeal outcome"],
        reason="Correction to the Federal IDR (No Surprises Act) final rule -- the out-of-network claims payment-dispute mechanism itself.",
        event="Federal-IDR-CMS-9897", dup="Yes (technical correction to 2026-11140)"),
    "2026-11140": dict(cat=["Reimbursement / Payment", "Denials / Claims Friction"], types=["Payment rule", "Appeal outcome"],
        reason="Federal IDR Operations final rule implementing the No Surprises Act dispute-resolution process for out-of-network payment/denial disputes.",
        event="Federal-IDR-CMS-9897", dup="No (original final rule; 2026-17622 is its correction)"),
    "2026-16508": dict(cat=["Coverage / Policy"], types=["New exclusion"],
        reason="Final rule prohibiting Medicaid/CHIP payment for a defined category of pediatric procedures -- an explicit payment/coverage exclusion."),
    "2026-16472": dict(cat=["Reimbursement / Payment"], types=["Payment delay", "Payment rule"],
        reason="CMS advisory that APM Incentive Payments cannot be disbursed without updated billing information -- a direct payment-disbursement/billing issue."),
    "2026-16368": dict(cat=["Coverage / Policy", "Procedure / Device Access"], types=["Coverage change", "Device coverage"],
        reason="Establishes the RAPID accelerated national Medicare coverage pathway for new technologies -- a coverage-determination process change."),
    "2026-15833": dict(cat=["Reimbursement / Payment"], types=["Rate change", "Fee schedule"],
        reason="IPPS/LTCH FY2027 final rule -- the core annual hospital inpatient payment-rate rule.",
        event="IPPS-FY2027-CMS-1849", dup="No (final rule; see linked proposed rule 2026-07203 and corrections 2026-07470, 2026-10276)"),
    "2026-15686": dict(cat=["Reimbursement / Payment"], types=["Rate change"],
        reason="Hospice wage index and payment-rate update for FY2027 -- a direct Medicare payment-rate rule.",
        event="Hospice-PPS-FY2027-CMS-1851"),
    "2026-15652": dict(cat=["Reimbursement / Payment"], types=["Rate change"],
        reason="Inpatient Rehabilitation Facility PPS FY2027 final rule -- direct Medicare payment-rate rule.",
        event="IRF-PPS-FY2027-CMS-1845"),
    "2026-15633": dict(cat=["Reimbursement / Payment"], types=["Rate change"],
        reason="340B Rebate Model Pilot -- a drug-pricing/reimbursement mechanism for covered entities."),
    "2026-15588": dict(cat=["Reimbursement / Payment"], types=["Rate change"],
        reason="Inpatient Psychiatric Facilities PPS FY2027 final rate update.",
        event="IPF-PPS-FY2027-CMS-1847", dup="No (final rule; see proposed rule 2026-06675)"),
    "2026-06675": dict(cat=["Reimbursement / Payment"], types=["Rate change"],
        reason="Inpatient Psychiatric Facilities PPS FY2027 PROPOSED rate update -- earlier stage of the same rulemaking as 2026-15588.",
        event="IPF-PPS-FY2027-CMS-1847", dup="Yes (proposed-rule stage; finalized as 2026-15588)"),
    "2026-15562": dict(cat=["Reimbursement / Payment"], types=["Rate change", "Bundling"],
        reason="SNF PPS and Consolidated Billing FY2027 final rule -- direct Medicare payment-rate and billing-bundling rule.",
        event="SNF-PPS-FY2027-CMS-1843", dup="No (final rule; see proposed rule 2026-06674)"),
    "2026-06674": dict(cat=["Reimbursement / Payment", "Reimbursement / Payment"], types=["Rate change", "Bundling"],
        reason="SNF PPS and Consolidated Billing FY2027 PROPOSED rule -- earlier stage of the same rulemaking as 2026-15562.",
        event="SNF-PPS-FY2027-CMS-1843", dup="Yes (proposed-rule stage; finalized as 2026-15562)"),
    "2026-15446": dict(cat=["Authorization / Utilization Management"], types=["PA requirement"],
        reason="Updates the HCPCS Master List of items subject to Required Face-to-Face/Prior-Authorization -- a direct, explicit prior-authorization requirement change."),
    "2026-15116": dict(cat=["Coverage / Policy"], types=["Provider bulletin"],
        reason="CMS approval renewing NCQA's deeming authority for Medicare Advantage HMO/PPO oversight."),
    "2026-14897": dict(cat=["Reimbursement / Payment"], types=["Payment rule"],
        reason="Proposed rule revising the indirect hold-harmless threshold for state health-care-related taxes -- a Medicaid financing/reimbursement mechanism."),
    "2026-14583": dict(cat=["Reimbursement / Payment"], types=["Rate change"],
        reason="Medicare Drug Price Negotiation Program draft guidance -- directly sets Medicare drug payment amounts."),
    "2026-14327": dict(cat=["Reimbursement / Payment", "Coverage / Policy"], types=["Rate change", "Fee schedule", "Coverage change"],
        reason="CY2027 Physician Fee Schedule proposed rule -- the core annual Medicare Part B payment and coverage-policy rule."),
    "2026-13918": dict(cat=["Coverage / Policy"], types=["Provider bulletin"],
        reason="CMS approval of Joint Commission's continued Home Health Agency accreditation recognition."),
    "2026-13793": dict(cat=["Reimbursement / Payment"], types=["Fee schedule"],
        reason="Advisory Panel on Hospital Outpatient Payment meeting -- advises on APC payment weights (OPPS fee schedule)."),
    "2026-13656": dict(cat=["Reimbursement / Payment", "Authorization / Utilization Management", "Coverage / Policy"],
        types=["Rate change", "PA requirement", "Coverage change"],
        reason="OPPS/ASC CY2027 proposed rule -- includes an explicit Prior Authorization RFI section plus core hospital-outpatient payment rates and EMTALA/AO coverage provisions."),
    "2026-13602": dict(cat=["Reimbursement / Payment", "Procedure / Device Access"], types=["Rate change", "Device coverage"],
        reason="Home Health PPS CY2027 proposed rule -- also sets DMEPOS (device) enrollment/payment policy."),
    "2026-13515": dict(cat=["Reimbursement / Payment"], types=["Bundling", "Rate change"],
        reason="TRICARE demonstration adding unbundled ambulance add-on reimbursement for a specific service -- a direct federal-payer payment-rule change."),
    "2026-13309": dict(cat=["Reimbursement / Payment"], types=["Payment rule"],
        reason="Annual HPSA shortage-area list -- directly determines eligibility for Medicare HPSA bonus payments."),
    "C1-2026-11094": dict(cat=["Coverage / Policy"], types=["Coverage restriction"],
        reason="Correction to the Medicaid Community Engagement (work requirement) rule -- a Medicaid eligibility/coverage-restriction mechanism.",
        event="Medicaid-Community-Engagement-CMS-2454", dup="Yes (correction notice for 2026-11094)"),
    "2026-11094": dict(cat=["Coverage / Policy"], types=["Coverage restriction"],
        reason="Interim final rule implementing the Medicaid community-engagement (work requirement) eligibility condition -- a coverage-restriction mechanism.",
        event="Medicaid-Community-Engagement-CMS-2454", dup="No (original IFC; C1-2026-11094 is its correction)"),
    "2026-12925": dict(cat=["Reimbursement / Payment"], types=["Rate change"],
        reason="ESRD PPS CY2027 proposed rule -- direct Medicare dialysis payment-rate rule."),
    "2026-12344": dict(cat=["Reimbursement / Payment"], types=["Payment rule"],
        reason="RFI on Pharmacy Benefit Manager compensation/remuneration restrictions -- directly affects drug-reimbursement flows."),
    "2026-12069": dict(cat=["Coverage / Policy"], types=["Provider bulletin"],
        reason="Final rule strengthening oversight of Medicare accrediting organizations -- governs the provider-certification framework underlying billing eligibility."),
    "2026-12059": dict(cat=["Reimbursement / Payment"], types=["Rate change"],
        reason="Medicare Drug Price Negotiation Program / Part D Benefit proposed rule -- directly sets Medicare drug payment policy."),
    "2026-10890": dict(cat=["Reimbursement / Payment", "Procedure / Device Access"], types=["Payment rule", "Procedure coverage"],
        reason="Increasing Organ Transplant Access (IOTA) Alternative Payment Model update -- a Medicare APM payment/procedure-access program."),
    "2026-10292": dict(cat=["Reimbursement / Payment"], types=["Rate change", "Payment rule"],
        reason="Medicaid Managed Care State Directed Payments / FFS practitioner payment proposed rule -- direct Medicaid reimbursement-mechanism change."),
    "2026-10276": dict(cat=["Reimbursement / Payment"], types=["Rate change"],
        reason="Second technical correction to the IPPS FY2027 proposed rule.",
        event="IPPS-FY2027-CMS-1849", dup="Yes (technical correction; see 2026-07203, 2026-07470, 2026-15833)"),
    "2026-10050": dict(cat=["Coverage / Policy", "Reimbursement / Payment"], types=["Coverage change", "Payment rule"],
        reason="ACA HHS Notice of Benefit and Payment Parameters for 2027 -- the core annual ACA marketplace coverage/payment-parameters rule."),
    "2026-09718": dict(cat=["Authorization / Utilization Management", "Coverage / Policy"], types=["Utilization restriction"],
        reason="Nationwide 6-month moratorium on new Medicare hospice enrollment -- a direct access/utilization restriction.",
        event="Enrollment-Moratoria-2026-05"),
    "2026-09717": dict(cat=["Authorization / Utilization Management", "Coverage / Policy"], types=["Utilization restriction"],
        reason="Nationwide 6-month moratorium on new Medicare home-health-agency enrollment -- a direct access/utilization restriction.",
        event="Enrollment-Moratoria-2026-05"),
    "2026-08513": dict(cat=["Reimbursement / Payment"], types=["Fee schedule"],
        reason="Medicare Advisory Panel on Clinical Diagnostic Laboratory Tests meeting -- advises on Clinical Laboratory Fee Schedule payment amounts."),
    "2026-08512": dict(cat=["Reimbursement / Payment"], types=["Fee schedule"],
        reason="Rechartering of the same Clinical Diagnostic Laboratory Tests advisory panel governing lab-test payment rates."),
    "2026-08511": dict(cat=["Reimbursement / Payment", "Documentation / Medical Necessity"], types=["Fee schedule", "Documentation requirement"],
        reason="Public meeting on new/reconsidered lab-test HCPCS codes for the CY2027 Clinical Laboratory Fee Schedule."),
    "2026-07470": dict(cat=["Reimbursement / Payment"], types=["Rate change"],
        reason="Technical correction to the IPPS FY2027 proposed rule.",
        event="IPPS-FY2027-CMS-1849", dup="Yes (technical correction; see 2026-07203, 2026-10276, 2026-15833)"),
    "2026-07226": dict(cat=["Reimbursement / Payment", "Documentation / Medical Necessity"], types=["Fee schedule", "Documentation requirement"],
        reason="First 2026 biannual HCPCS Level II public coding meeting -- new/revised codes affect billing and payment."),
    "2026-07205": dict(cat=["Authorization / Utilization Management"], types=["PA requirement", "PA turnaround"],
        reason="CMS interoperability and electronic Prior Authorization proposed rule for MA/Medicaid/CHIP/QHP -- directly mandates PA process/turnaround-time requirements."),
    "2026-07203": dict(cat=["Reimbursement / Payment"], types=["Rate change"],
        reason="IPPS/LTCH FY2027 original proposed rule -- core annual hospital payment-rate rulemaking.",
        event="IPPS-FY2027-CMS-1849", dup="No (original proposed rule; see corrections 2026-07470, 2026-10276 and final rule 2026-15833)"),
    "2026-06674": dict(cat=["Reimbursement / Payment"], types=["Rate change", "Bundling"],
        reason="SNF PPS and Consolidated Billing FY2027 PROPOSED rule.",
        event="SNF-PPS-FY2027-CMS-1843", dup="Yes (proposed-rule stage; finalized as 2026-15562)"),
}

rows = []
for rec in records:
    doc = rec["document_number"]
    c = CLASS.get(doc)
    agencies = [a for a in (rec.get("agencies") or []) if a]

    row = {
        "source": "Federal Register",
        "source_type": "Official U.S. government regulatory/publication record (federalregister.gov API)",
        "record_id": doc,
        "record_date": rec["publication_date"],
        "title": rec["title"],
        "text_or_description": rec.get("abstract") or "(no abstract published for this document)",
        "url": rec.get("html_url"),
        "payer": "; ".join(agencies) if agencies else None,
        "procedure": None,
        "topic": rec.get("type"),
        "duplicate_or_repost": "No",
        "underlying_event_id": None,
        "direct_or_supporting": "Irrelevant",
        "signal_categories": [],
        "signal_types": [],
        "classification_reason": None,
        "evidence_quote_or_field": (rec.get("abstract") or rec["title"])[:300],
    }

    if c:
        row["direct_or_supporting"] = "D"
        row["signal_categories"] = c["cat"]
        row["signal_types"] = c["types"]
        row["classification_reason"] = c["reason"]
        row["underlying_event_id"] = c.get("event")
        if "dup" in c:
            row["duplicate_or_repost"] = c["dup"]
    else:
        is_health_agency = any(a in agencies for a in
            ["Health and Human Services Department", "Centers for Medicare & Medicaid Services",
             "Food and Drug Administration", "Health Resources and Services Administration"])
        if is_health_agency:
            row["classification_reason"] = ("HHS/CMS/FDA/HRSA document, but its content is purely administrative/"
                "procedural (e.g. generic Paperwork Reduction Act information-collection notice, regulatory-agenda "
                "index, meeting-panel item, or privacy-system notice unrelated to a specific billing/coverage/"
                "authorization/reimbursement/documentation change) -- no traceable authorization, denial, coverage, "
                "documentation, reimbursement, or procedure/device-access content per the evidence-based rule.")
        else:
            row["classification_reason"] = (f"Matched only on a generic phrase ('{', '.join(rec.get('matched_query_terms') or [])}') "
                f"used in an unrelated context by a non-healthcare agency ({', '.join(agencies) if agencies else 'unlisted agency'}); "
                f"content is not about payer/RCM authorization, denials, coverage, documentation, reimbursement, or procedure/device access.")

    row["signal_categories"] = list(dict.fromkeys(row["signal_categories"]))
    row["signal_types"] = list(dict.fromkeys(row["signal_types"]))
    rows.append(row)

with open("classified_rows_federal_register.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2, ensure_ascii=False)

ds = Counter(r["direct_or_supporting"] for r in rows)
print("D/S/Irrelevant breakdown:", dict(ds))
cat_counts = Counter()
for r in rows:
    for cat in r["signal_categories"]:
        cat_counts[cat] += 1
print("Signal categories (D+S, multi-label):", dict(cat_counts))
dup_count = sum(1 for r in rows if r["duplicate_or_repost"] != "No")
print("Flagged as duplicate/linked-event records:", dup_count)
events = Counter(r["underlying_event_id"] for r in rows if r["underlying_event_id"])
print("Underlying event clusters:", dict(events))
