# -*- coding: utf-8 -*-
import json
from collections import Counter

with open("data/raw/linkedin_posts_latest100.json", encoding="utf-8") as f:
    posts = json.load(f)

assert len(posts) == 95, len(posts)

UHC_PA_EVENT = "UHC-PA-Reduction-Oct2026"

# index (1-based, in file order) -> classification
# ds: "S" (LinkedIn is never treated as D per project rule 12 -- public conversation is
#      Supporting evidence at best, even when it cites a real payer/CMS action) or "Irrelevant"
C = {}

def s(cats, types, reason, payer=None, procedure=None, event=None, dup="No"):
    return dict(ds="S", cats=cats, types=types, reason=reason, payer=payer, procedure=procedure, event=event, dup=dup)

def irr(reason, event=None, dup="No"):
    return dict(ds="Irrelevant", cats=[], types=[], reason=reason, payer=None, procedure=None, event=event, dup=dup)

AUM = "Authorization / Utilization Management"
DEN = "Denials / Claims Friction"
COV = "Coverage / Policy"
DOC = "Documentation / Medical Necessity"
REI = "Reimbursement / Payment"
PROC = "Procedure / Device Access"
OTH = "Other / Unmapped"

C[1] = s([AUM], ["PA approval/denial", "PA turnaround"], "Discusses KFF analysis of CMS-0057-F transparency requirements (approval/denial rates, decision turnaround now publicly reported) -- specific real regulation cited, not generic keyword use.")
C[2] = s([AUM, DOC, DEN], ["PA requirement", "Documentation requirement", "Denial rate"], "Reports UHC eliminating PA for ~1,700 codes Oct 1, names affected procedure categories, cites AMA PA-volume stat and RCM concerns re: documentation/medical necessity/denials.", payer="UnitedHealthcare", event=UHC_PA_EVENT)
C[3] = s([AUM], ["PA requirement"], "Reports the same real UHC PA-elimination announcement (1,700 codes, Oct 1, 30% reduction).", payer="UnitedHealthcare", event=UHC_PA_EVENT)
C[4] = s([AUM, DEN, COV, REI], ["PA requirement", "Denial rate", "Coverage change", "Payment rule"], "Cites specific real items: OIG HAC-list review (OEI-06-26-00210), OIG NY/Kansas Medicaid MCO parity findings on PA, CMS Transmittal 13888 adding a denial-reason field -- concrete, citable regulatory items, not vague commentary.")
C[5] = irr("Generic consumer-education explainer of what PA means -- no specific event, payer action, or data cited.")
C[6] = irr("About federal patient-data-interoperability/EHI-exchange defaults between insurers and providers -- not an authorization, denial, coverage, documentation, or reimbursement action.")
C[7] = s([AUM, DEN], ["PA requirement", "PA documentation", "New denial reason"], "Detailed, specific analysis of the CMS-0057-F Prior Authorization API requirement (published criteria checklist) and the already-effective denial-reason mandate.")
C[8] = s([AUM], ["PA requirement"], "Names the specific real regulation (CMS-0057-F) and its 2027 deadline as the subject of a leadership-readiness discussion.")
C[9] = irr("About an FDA leadership appointment; speculative commentary on possible future influence on PA/reimbursement, not a reported payer/RCM action itself.")
C[10] = s([DEN], ["Coverage denial"], "Reports a specific real bipartisan House bill that would restrict AI-based claim-denial systems and require licensed human oversight of adverse benefit determinations.")
C[11] = s([AUM, DEN], ["PA requirement", "Denial rate", "Appeal outcome"], "Cites a real KFF PA-denial-rate analysis (12-18% across MA/Medicaid/ACA) and specific appeal-overturn percentages, plus the 2026 electronic-PA CMS requirement.")
C[12] = s([AUM, DEN], ["PA requirement", "Denial rate"], "Reports UHC's PA elimination and a specific KFF-sourced UHC MA denial-rate figure (17%, 2025).", payer="UnitedHealthcare", event=UHC_PA_EVENT)
C[13] = irr("Generic engagement/discussion prompt about prior authorization with no specific event or data.")
C[14] = s([AUM], ["PA requirement"], "Personal reaction to the specific real UHC PA-reduction announcement.", payer="UnitedHealthcare", event=UHC_PA_EVENT)
C[15] = irr("One-line share note ('this will impact Home health/DME providers') with no substantive content of what 'this' is.")
C[16] = s([AUM, COV, DEN], ["PA requirement", "Coverage restriction", "Denial rate"], "Cites two specific real OIG audits (NY Aug 12, Kansas Aug 9) on Medicaid MCO parity/PA compliance and the CMS Inpatient-Only list removal counts (285 removed, 637 proposed).")
C[17] = s([REI, AUM], ["Rate change"], "Cites the specific real CMS 2027 Physician Fee Schedule proposed conversion factors ($33.17 / $32.84) and frames the RCM chain including prior auth.")
C[18] = s([DEN, AUM], ["Denial rate"], "Cites a specific real PA denial-rate range (2%-25%) across MA/Medicaid/ACA plans per a named Healthcare Dive article.")
C[19] = s([AUM], ["PA requirement", "PA turnaround"], "Detailed, specific breakdown of CMS-0057-F/CMS-0062-P turnaround requirements (72hr/7-day) and the 2027 electronic PA API mandate, plus the drug-PA scope gap.")
C[20] = s([AUM], ["PA requirement"], "Reports the same real UHC 1,700-code PA elimination.", payer="UnitedHealthcare", event=UHC_PA_EVENT)
C[21] = s([DEN, DOC, AUM], ["Denial rate", "Documentation denial"], "Cites a specific neurology PA denial rate (18% vs 5-10% baseline) and names concrete documentation failure points (Botox headache-frequency docs, EEG sleep-architecture, nerve-conduction coding) driving those denials.")
C[22] = s([AUM, PROC], ["PA requirement", "Procedure PA"], "Official Medicare Administrative Contractor (CGS, the Jurisdiction B/C DME MAC) announcing its own updated Prior Authorization guidance for named DMEPOS categories -- a real first-party contractor announcement, though only verifiable via the linked CGS webpage, not this post itself.", payer="CGS Administrators (DME MAC, Jurisdiction B/C)")
C[23] = irr("About RCM/billing workforce staffing shortages -- generic labor-market commentary, not a specific authorization/denial/coverage/reimbursement event.")
C[24] = irr("Generic single-sentence templated content ('patients denied coverage often win on appeal') with no specific data or event -- identical text also posted by 3 other unrelated accounts (syndicated content).", event="SYNDICATED-DENIAL-APPEAL-TEMPLATE")
C[25] = s([AUM, DEN], ["PA requirement", "PA documentation", "New denial reason"], "Detailed breakdown of the real 2027 electronic PA API capabilities CMS is mandating (documentation visibility, denial-reason electronic delivery).")
C[26] = irr("Vague reactive comment on an unspecified shared article (isRepost=True, no article text captured) -- no identifiable specific fact in the post text itself.")
C[27] = irr("Identical templated text to post 24 (syndicated content, different account).", event="SYNDICATED-DENIAL-APPEAL-TEMPLATE", dup="Yes (identical text to post #24, syndicated content asset)")
C[28] = s([AUM, REI, DEN], ["PA requirement", "Rate change", "Denial rate"], "Cites the real CMS-0057-F effective date and the specific real CY2026 dual Medicare conversion factors ($33.57 qualifying APM / $33.40 non-qualifying) -- concrete, citable.", event="INSTANCY-2026-RCM-WATCHLIST")
C[29] = s([AUM, REI, DEN], ["PA requirement", "Rate change", "Denial rate"], "Identical content to post 28 (same company's CEO cross-posting), citing the same real CMS-0057-F and dual-conversion-factor facts.", event="INSTANCY-2026-RCM-WATCHLIST", dup="Yes (identical text to post #28, same company/CEO)")
C[30] = irr("Identical templated text to posts 24/27 (syndicated content, different account/firm).", event="SYNDICATED-DENIAL-APPEAL-TEMPLATE", dup="Yes (identical text to post #24, syndicated content asset)")
C[31] = s([AUM], ["PA turnaround"], "States the specific real CMS requirement for 7-day standard / 72-hour expedited PA decisions.")
C[32] = s([AUM, DEN], ["PA turnaround", "New denial reason"], "Cites the specific real CMS-0057-F effective date (Jan 1 2026) and its turnaround/denial-reason requirements.")
C[33] = irr("About dental insurance billing/EOB complexity in general -- no specific payer action or data, and outside the medical-payer scope of this project's 10 sources.")
C[34] = irr("Practice-marketing post listing accepted insurance plans and appointment wait times -- not an authorization/denial/coverage/reimbursement signal.")
C[35] = irr("Generic podcast-episode teaser about prior-auth workflow philosophy ('beyond compliance mindset') -- no specific event or data cited.")
C[36] = s([AUM], ["PA requirement", "PA documentation"], "Cites the real CMS-0057-F 2027 API deadline and the real April 2026 proposal extending electronic PA to drugs, plus a specific PA workload stat (40/week, 12 staff hours).")
C[37] = s([AUM, COV, DEN], ["PA turnaround", "Coverage change", "New denial reason"], "Detailed, specific description of a real named bill (H.R. 8375, Medicare Advantage Improvement Act of 2026): 72hr/24hr PA decision windows, requirement that MA coverage criteria align with traditional Medicare, and a no-reauthorization rule for already-approved care.")
C[38] = s([AUM, PROC], ["PA requirement", "Procedure PA"], "Very specific real UHC policy detail: exact CPT codes (92507, 92508, 92526) exempted from PA for speech-language pathology services under MA/D-SNP, effective Oct 1 2026.", payer="UnitedHealthcare", procedure="Speech-Language Pathology (CPT 92507/92508/92526)")
C[39] = s([AUM, DOC], ["PA requirement", "Documentation requirement"], "Concrete front-end RCM checklist specifically reacting to real payer PA-reduction announcements (verifying PA truly removed per plan/service, medical-necessity requirements still active).")
C[40] = s([DEN, AUM, REI], ["Denial rate", "PA requirement", "Claim rework"], "Cites the real AHA 'Cost of Caring' report figures: ~50 million MA prior-auth requests in 2023, ~$26B hospital cost managing claims, 70% of denied claims eventually paid.")
C[41] = s([AUM], ["PA requirement"], "Cites a specific real Health Affairs study figure: PA costs the U.S. healthcare system $93.3 billion annually.")
C[42] = s([DEN, AUM], ["Appeal outcome", "Denial rate"], "Cites a real, specific OIG finding that MA organizations overturned nearly all appealed PA denials for SNF admission on review.")
C[43] = s([AUM], ["PA requirement"], "References real FOIA-obtained documents showing CMS's WISeR AI prior-authorization pilot was rushed despite vendor warnings.")
C[44] = irr("Vague reminder that Ohio Medicaid behavioral-health 'proposed rules' comments are due -- does not state what the proposed rules actually change.")
C[45] = s([DEN, DOC], ["Coding denial", "Documentation denial"], "Concrete claim-formatting/coding guidance (POS, modifiers, taxonomy codes) specifically for pain-rehab claims to avoid denials -- directly relevant to the practice's pain-management billing focus.", procedure="Integrative pain rehabilitation (HCFA-1500 claims)")
C[46] = s([AUM, DOC, COV, PROC], ["PA requirement", "Clinical criteria", "Policy revision", "Procedure PA"], "Highly specific: real March 2026 CMS TMS billing-policy update, exact CPT codes (90867-90869), exact covered ICD-10 diagnosis codes (F32.2, F33.2), and Highmark's specific 3/1/2026 addition of TMS to its PA list.", payer="Highmark; CMS/Medicare", procedure="Transcranial Magnetic Stimulation (TMS)")
C[47] = irr("Generic reflective commentary on 'what causes PA denials' -- no specific event, payer, or data cited.")
C[48] = s([AUM, DEN], ["PA requirement", "PA turnaround", "New denial reason"], "Detailed, accurate summary of the real CMS-0057-F Interoperability and Prior Authorization Final Rule (72hr/7-day timelines, denial-reason transparency, 2027 API mandate).", event="SYNDICATED-CMS-0057F-SUMMARY")
C[49] = s([AUM, DEN], ["PA requirement", "PA turnaround", "New denial reason"], "Identical CMS-0057-F summary text to post 48 (syndicated healthcare-content distribution, different account).", event="SYNDICATED-CMS-0057F-SUMMARY", dup="Yes (identical text to post #48, syndicated content asset)")
C[50] = s([DEN, REI], ["Appeal outcome", "Payment delay"], "Reports specific real health systems (Mayo Clinic, NewYork-Presbyterian, Mount Sinai, ~30 total) dropping Medicare Advantage contracts in 2026 citing PA denials and slow reimbursement, with a specific >80% appeal-overturn / <10% appeal-rate stat.")
C[51] = irr("Bare link with no substantive post text ('from 2025').")
C[52] = irr("Generic educational primer on what prior authorization is and why it exists (evergreen explainer series) -- no specific event or new data.")
C[53] = s([AUM], ["PA requirement"], "Commentary specifically analyzing operational risk of the real UHC 30% PA reduction (workflow cutover risk).", payer="UnitedHealthcare", event=UHC_PA_EVENT)
C[54] = s([DEN, AUM], ["New denial reason"], "Cites the specific real CMS requirement (effective 2026) that impacted payers give a specific reason for denied non-drug PA decisions, and the 2027 electronic denial-reason API mandate.")
C[55] = irr("Identical templated text to posts 24/27/30 (syndicated content, different account).", event="SYNDICATED-DENIAL-APPEAL-TEMPLATE", dup="Yes (identical text to post #24, syndicated content asset)")
C[56] = s([AUM], ["PA requirement"], "Discusses the real CMS-0057-F 2027 electronic PA API deadline and vendor-readiness questions.")
C[57] = irr("A personal grievance letter regarding a cashless-authorization denial from 'Care Insurance' -- an Indian health insurer, outside the US Medicare/Medicaid/commercial payer scope this project tracks (UHC/Aetna/Cigna/Humana/CMS).")
C[58] = s([AUM, DOC, DEN], ["PA requirement", "Clinical criteria", "Documentation denial"], "Specific cardiology billing checklist citing a concrete PA-prevalence stat (85% of advanced cardiology procedures require PA) and named documentation/ICD-10 alignment requirements.", procedure="Cardiology imaging/interventional procedures")
C[59] = s([DEN, AUM], ["Denial rate", "Appeal outcome"], "Cites a specific denial-rate range (2%-25%) and specific appeal-overturn range (43%-67%) by payer.")
C[60] = s([DEN, AUM], ["Denial rate", "Appeal outcome"], "Bloomberg News reporting a specific, named data point: 5 large insurers covering 160M+ people denied >10% of standard PA requests in 2025; ~50% appeal win rate.")
C[61] = irr("Generic 'panel of experts weighs in' content-marketing roundup on denial/PA trends -- no single specific traceable fact or event.")
C[62] = s([REI], ["Payment rule"], "NYT-sourced report that CMS is developing a new Medicare payment category specifically to reimburse AI-supported diagnostic/care software.")
C[63] = s([AUM], ["PA requirement"], "States a specific, notable scope-limitation fact about CMS-0057-F: the rule does not reach most commercial insurance plans.")
C[64] = s([DEN, COV], ["Appeal outcome", "Coverage denial"], "Cites specific named insurers (CVS Caremark, Quantum Health, Cigna, Oxford/UnitedHealth) and a specific reversal-rate statistic (~1/3) for medical-necessity/coverage-denial challenges.", payer="Cigna; UnitedHealthcare (Oxford); CVS Caremark; Quantum Health")
C[65] = s([AUM, DEN, REI], ["PA requirement", "PA turnaround", "New denial reason", "Payment rule"], "Very detailed, accurate breakdown of CMS-0057-F requirements (72hr/7-day, denial reasons, FHIR/USCDI/SMART/Da Vinci PAS standards) plus specific cost figures ($20-50/hr, 13hrs/week, $34k/provider/year, $15B savings estimate).")
C[66] = s([DEN, AUM], ["Denial rate", "Appeal outcome"], "Cites specific real stats: MA SNF-admission denials up 56% YoY in 2026, and an OIG finding of ~95% appeal-overturn rate for MA PA denials, with active OIG investigation into SNF/IRF/LTACH PA practices.")
C[67] = s([AUM, REI], ["PA requirement", "Payment rule"], "Detailed original analysis of the real UHC PA reduction, naming Aetna/Cigna/Centene as industry comparators, with specific methodology figures (880->162 procedure groups, 67% PA-volume reduction, >90% dollar-value retention).", payer="UnitedHealthcare; Aetna; Cigna; Centene", event=UHC_PA_EVENT)
C[68] = s([AUM, PROC], ["PA requirement", "Device PA"], "Reports a specific real CMS action: EXPANDING required PA for named DMEPOS categories (TLSO/knee/upper-limb orthoses, pressure-reducing surfaces, manual wheelchairs) effective Oct 28.", payer="CMS/Medicare", procedure="DMEPOS (orthoses, wheelchairs, support surfaces)")
C[69] = s([DEN, AUM, DOC], ["Coding denial", "Claim rework"], "Concrete denial-prevention checklist citing the specific real CO-15 denial code and PA-to-claim mismatch scenarios for radiation/oncology/urology/behavioral health.")
C[70] = irr("Bare link to an external blog with minimal framing text ('here's the rest of the story') -- no specific content in the post itself.")
C[71] = s([AUM, PROC], ["PA requirement", "Procedure PA"], "Very specific real UHC program detail: the National Gold Card portal (opened Sept 1), its exact qualifying criteria (10+ eligible PAs/year for 2 years, 92%+ approval rate), and Oct 1 go-live for ASC procedures.", payer="UnitedHealthcare", procedure="Ambulatory Surgery Center (ASC) procedures")
C[72] = s([AUM], ["PA turnaround"], "Analyzes specific interpretive questions under the real CMS-0057-F rule (timing/extension rules, weekend ownership of the decision clock).", event="PRIOR-AUTH-CLOCK-ARTICLE")
C[73] = s([AUM], ["PA turnaround"], "Identical 'Prior-Authorization Clock' article promo text to post 72 (different account).", event="PRIOR-AUTH-CLOCK-ARTICLE", dup="Yes (identical text to post #72/#83, same article promo)")
C[74] = irr("Generic industry-panel reflection on MA contract management challenges -- no specific new fact or event.")
C[75] = s([AUM], ["PA requirement"], "Reports the real UHC PA-elimination announcement including the home-health-specific detail.", payer="UnitedHealthcare", event=UHC_PA_EVENT)
C[76] = s([AUM], ["PA requirement"], "References the real CMS WISeR AI prior-authorization pilot.")
C[77] = s([AUM], ["PA requirement"], "Reports the real UHC 1,700-code PA elimination (Oct 2026).", payer="UnitedHealthcare", event=UHC_PA_EVENT)
C[78] = s([DEN, AUM, DOC], ["Claim rework", "PA approval/denial", "Clinical criteria"], "Concrete denial-prevention framework naming a specific real operational detail: payers give only 24 hours to update a surgery authorization to match what was actually performed.")
C[79] = s([DEN, AUM], ["Denial rate", "Appeal outcome"], "Cites specific real KFF figures: >=1-in-8 standard PA requests denied; appeal-overturn rates by program (67% MA, ~50% Medicaid, 43% ACA).")
C[80] = irr("Generic consumer-education explainer of what PA is -- no specific event or data.")
C[81] = s([AUM], ["Utilization restriction"], "Describes a documented special report on outsourced/delegated Utilization Management financial-incentive structures, citing public financial records, regulatory examinations, and federal audits as its evidentiary basis.")
C[82] = s([REI], ["Underpayment"], "Reports a specific, real, sourced financial-integrity event: Aetna agreeing to pay $117.7M to settle Medicare Advantage overbilling claims.", payer="Aetna")
C[83] = s([AUM], ["PA turnaround"], "Identical 'Prior-Authorization Clock' article promo text to posts 72/73 (author's own personal account).", event="PRIOR-AUTH-CLOCK-ARTICLE", dup="Yes (identical text to post #72/#73, same article promo)")
C[84] = s([DEN], ["Appeal outcome"], "Discusses specific real Bloomberg/WSJ reporting on successfully appealing PA denials.")
C[85] = s([DEN, DOC, COV], ["Medical-necessity denial", "Appeal outcome", "Clinical history"], "Detailed real documented case: UHC denied continued inpatient rehab coverage citing lack of 'notable continued progress'/not medically necessary despite a neurosurgeon's supporting letter; appeals denied.", payer="UnitedHealthcare")
C[86] = s([AUM, DEN, REI], ["PA requirement", "PA turnaround", "New denial reason"], "Cites the real specific CMS requirements (72hr/7-day decisions effective Jan 1 2026; FHIR-based Provider Access/PA APIs by Jan 1 2027).")
C[87] = s([REI], ["Rate change"], "Specific real regulatory detail on the 340B rebate repository timeline (voluntary Oct 1, proposed mandatory 2027) under the Inflation Reduction Act's rebate-exclusion requirement.")
C[88] = s([AUM, PROC, DEN], ["PA requirement", "Procedure PA", "Payment delay"], "STAT News reporting on real FOIA documents showing a WISeR AI PA vendor's failures, including a named example involving delayed PA for a kyphoplasty/vertebral augmentation procedure.", procedure="Kyphoplasty / vertebral augmentation")
C[89] = irr("Personal AI-research-project showcase applying prior-auth/denial/reimbursement concepts to build an analytics tool -- not itself a report of a specific payer/RCM event.")
C[90] = s([AUM, DEN], ["PA requirement", "PA approval/denial"], "Detailed critical analysis of the real UHC PA reduction citing a specific real AMA survey figure (26% of physicians reporting a serious adverse event linked to PA) and CMS's aggregate PA-reporting requirement.", payer="UnitedHealthcare", event=UHC_PA_EVENT)
C[91] = s([DEN], ["Denial rate"], "Cites specific real KFF payer-level PA denial rates: Centene 25% (ACA), Independence Health 23% (Medicaid), UHC 17% (MA).", payer="UnitedHealthcare; Centene; Independence Health Group")
C[92] = s([DEN, AUM, COV], ["Denial rate", "Appeal outcome", "PA approval/denial", "Provider bulletin"], "Detailed real KFF/CMS 2024 contract-level data: 52.8M PA decisions, 92.3% approved, 7.7% not approved, 11.5% appealed, 80.7% overturned on appeal; plus the 2026 MA public-reporting mandate.")
C[93] = irr("Generic '2026 RCM trends' listicle covering PA/coding/reimbursement broadly -- no single specific traceable event or data point.")
C[94] = s([], [], "Reports a real, specific regulatory-authority change (RFK Jr. extending HHS-OIG provider-exclusion authority to CMS) -- a genuine program-integrity/enforcement action, but it does not fit Authorization/UM, Denials, Coverage, Documentation, Reimbursement, or Procedure/Device categories as defined (counted under Other/Unmapped: signal_categories intentionally empty).")
C[95] = irr("Generic commentary on AI reducing PA administrative burden (podcast teaser) -- no specific payer action or data.")

rows = []
for i, post in enumerate(posts, start=1):
    cls = C[i]
    row = {
        "source": "LinkedIn",
        "source_type": "Social / public conversation",
        "record_id": post.get("urn"),
        "record_date": post.get("postedAtISO"),
        "title": f"LinkedIn post by {post.get('authorName')}",
        "text_or_description": post.get("text"),
        "url": post.get("url"),
        "payer": cls["payer"],
        "procedure": cls["procedure"],
        "topic": "Prior authorization / RCM (search: payer + PA/denial/reimbursement keywords)",
        "duplicate_or_repost": cls["dup"],
        "underlying_event_id": cls["event"],
        "direct_or_supporting": cls["ds"],
        "signal_categories": cls["cats"],
        "signal_types": cls["types"],
        "classification_reason": cls["reason"],
        "evidence_quote_or_field": (post.get("text") or "")[:300],
    }
    rows.append(row)

with open("classified_rows_linkedin_100.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2, ensure_ascii=False)

ds = Counter(r["direct_or_supporting"] for r in rows)
print("D/S/Irrelevant:", dict(ds))
cat_counts = Counter()
for r in rows:
    for c in r["signal_categories"]:
        cat_counts[c] += 1
print("Signal categories (multi-label):", dict(cat_counts))
print("Flagged duplicates:", sum(1 for r in rows if r["duplicate_or_repost"] != "No"))
events = Counter(r["underlying_event_id"] for r in rows if r["underlying_event_id"])
print("Underlying event clusters:", dict(events))
