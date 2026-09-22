import json

rows = []

def row(**kw):
    base = {
        "source": "LinkedIn",
        "source_type": "Social / public conversation",
        "payer": None,
        "procedure": None,
        "topic": None,
        "duplicate_or_repost": "No",
        "signal_categories": [],
        "signal_types": [],
    }
    base.update(kw)
    rows.append(base)

row(
    record_id="urn:li:activity:7506034845148672000",
    record_date="2026-09-16T17:02:42.467Z",
    title="Michael Londo post on MA plans",
    text_or_description="MA plans were originally touted as a cheaper, better alternative to standard Medicare... Up-coding, delays, denials etc...",
    url="https://www.linkedin.com/posts/michael-londo-0756a7a_humana-unitedhealthcare-received-178m-in-activity-7506034845148672000-vYNB",
    direct_or_supporting="Irrelevant",
    classification_reason="Generic opinion/political commentary about the Medicare Advantage business model as a whole. Mentions 'denials' and 'delays' only as unspecific grievances -- no identifiable payer policy, procedure, claim, or dated event is described. Per evidence-based classification rule, a keyword ('denials') appearing in a general rant does not establish a usable RCM signal.",
    evidence_quote_or_field="'Up-coding, delays, denials etc., they are a grift for insurance companies'"
)

row(
    record_id="urn:li:activity:7506173371479445506",
    record_date="2026-09-17T02:13:09.718Z",
    title="A.R Rehman post on UnitedHealth Group / Optum WellMed clinic sale to TPG",
    text_or_description="UnitedHealth Group just sold part of its Florida clinics, run under Optum's WellMed brand, to private equity firm TPG... revenue in healthcare comes from how claims get priced, coded, and paid...",
    url="https://www.linkedin.com/posts/activity-7506173371479445506-M83Q",
    direct_or_supporting="Irrelevant",
    payer="UnitedHealthcare/Optum",
    classification_reason="Reports a private-equity clinic ownership transaction (M&A/corporate structure news) with generic commentary about claims integrity. Does not describe an actual authorization, denial, coverage, documentation, or reimbursement policy/operational change -- no specific claim rule, rate, or procedure is named.",
    evidence_quote_or_field="'revenue in healthcare comes from how claims get priced, coded, and paid'"
)

row(
    record_id="urn:li:activity:7506014393432788992",
    record_date="2026-09-16T15:41:26.398Z",
    title="Healthcare Finance News: OIG seeks $46.9M refund from UnitedHealthcare",
    text_or_description="OIG seeks $46.9M refund from UnitedHealthcare",
    url="https://www.linkedin.com/posts/healthcare-finance-news_oig-seeks-469m-refund-from-unitedhealthcare-activity-7506014393432788992-UGLb",
    direct_or_supporting="S",
    payer="UnitedHealthcare",
    signal_categories=["Reimbursement / Payment"],
    signal_types=["Overpayment recovery / payment integrity action (closest listed analog: Underpayment/Payment rule)"],
    classification_reason="A named federal oversight body (HHS OIG) is reported seeking recovery of a specific dollar amount from a named payer, shared via a healthcare trade-publication account. This is a real, specific, dated financial/payment-integrity event, but it reaches us only as a one-line trade-press repost on LinkedIn, not the primary OIG report itself -- so it is Supporting evidence requiring verification against the official OIG record, not a confirmed/direct policy record.",
    evidence_quote_or_field="'OIG seeks $46.9M refund from UnitedHealthcare'"
)

row(
    record_id="urn:li:activity:7505956785200214016",
    record_date="2026-09-16T11:52:31.525Z",
    title="Ahmed Taher repost on healthcare workforce/AI discussion",
    text_or_description="Great discussions on the forces reshaping healthcare -- particularly workforce transformation, the implications and opportunities of AI...",
    url="https://www.linkedin.com/posts/aktaher_uoft-gemba-tradewars-activity-7505956785200214016-qnXB",
    direct_or_supporting="Irrelevant",
    duplicate_or_repost="Yes (isRepost=True per source field)",
    classification_reason="General healthcare workforce/AI conference commentary. No payer, procedure, authorization, denial, coverage, documentation, or reimbursement content.",
    evidence_quote_or_field="isRepost: true; text is generic conference reflection"
)

row(
    record_id="urn:li:activity:7506004036739973121",
    record_date="2026-09-16T15:00:17.170Z",
    title="solli x Doceree healthcare media planning workbook",
    text_or_description="...Healthcare Media Planners Workbook is designed to support... partner evaluation for RFP season...",
    url="https://www.linkedin.com/posts/solli-global_healthcaremedia-mediaplanning-pharmamedia-activity-7506004036739973121-fk0h",
    direct_or_supporting="Irrelevant",
    classification_reason="B2B pharma/healthcare advertising and media-planning marketing content. No RCM, payer, or claims relevance.",
    evidence_quote_or_field="'Healthcare Media Planners Workbook'"
)

row(
    record_id="urn:li:activity:7506016413938008065",
    record_date="2026-09-16T15:49:28.124Z",
    title="Dariya B. on UCHealth freestyle rap community event",
    text_or_description="I'm still thinking about the energy in the room yesterday at UCHealth's 100th collaborative episode with Harry Mack...",
    url="https://www.linkedin.com/posts/dariya-bryant_uchealth-harrymack-freestylerap-activity-7506016413938008065-x_rp",
    direct_or_supporting="Irrelevant",
    classification_reason="Community/patient-experience human-interest story. No RCM content.",
    evidence_quote_or_field="entire post is a narrative about a hospital community event"
)

row(
    record_id="urn:li:activity:7506162773333229569",
    record_date="2026-09-17T01:31:02.923Z",
    title="REGAN HealthCare Services medical check-up package promotion (Myanmar/Thailand)",
    text_or_description="[Burmese/Thai-language ad] Buy 1 Get 1 FREE comprehensive health screening package, Ladprao General Hospital, Bangkok...",
    url="https://www.linkedin.com/posts/regan-healthcare-services_reganbbibbmbbrbaubblbbsbatbatbbubbnbbobbu-activity-7506162773333229569-6yb9",
    direct_or_supporting="Irrelevant",
    classification_reason="Medical-tourism marketing advertisement in Myanmar/Thailand, unrelated to US payer RCM, authorization, denials, coverage, or reimbursement.",
    evidence_quote_or_field="promotional health-checkup package pricing, no US payer/RCM content"
)

row(
    record_id="urn:li:activity:7506203640148205568",
    record_date="2026-09-17T04:13:26.331Z",
    title="Doctorials Academy: The Rise of Healthcare Jobs article promotion",
    text_or_description="The healthcare industry is transforming rapidly, creating new opportunities across clinical care, healthcare management...",
    url="https://www.linkedin.com/posts/doctorials-academ-healthcaremanagement_healthcarejobs-healthcarecareers-healthcaremanagement-activity-7506203640148205568-p_rV",
    direct_or_supporting="Irrelevant",
    classification_reason="Healthcare careers/education marketing content. No RCM relevance.",
    evidence_quote_or_field="'The Rise of Healthcare Jobs: How Healthcare Is Reshaping Careers and Employment'"
)

row(
    record_id="urn:li:activity:7505969873324433408",
    record_date="2026-09-16T12:44:31.977Z",
    title="Paul T. Kim on FDA PDUFA VIII public meeting",
    text_or_description="Returning from a brief hiatus to today's FDA public meeting on the PDUFA VIII draft agreement...",
    url="https://www.linkedin.com/posts/paultkim_fda-pdufa-innovation-activity-7505969873324433408-GU1t",
    direct_or_supporting="Irrelevant",
    classification_reason="Concerns FDA drug-review user-fee funding/regulatory-capture policy debate (PDUFA), a drug-approval funding mechanism -- not payer coverage, authorization, denials, claims, documentation, or reimbursement. Falls outside the project's RCM/payer taxonomy despite being 'healthcare policy'.",
    evidence_quote_or_field="'FDA public meeting on the PDUFA VIII draft agreement'"
)

row(
    record_id="urn:li:activity:7506178553328058368",
    record_date="2026-09-17T02:33:45.167Z",
    title="Ewa K. Panetta on Michigan rural hospital legislative advocacy day",
    text_or_description="Can't let the day go by without reflecting on today's Michigan Health & Hospital Association Small & Rural Hospital Legislative Day...",
    url="https://www.linkedin.com/posts/ewa-k-panetta-cpps-a637322b_ruralhealth-hospitaladvocacy-healthcareaccess-activity-7506178553328058368-2i7i",
    direct_or_supporting="Irrelevant",
    classification_reason="General rural-hospital funding advocacy sentiment. No specific payer, procedure, authorization, denial, coverage, or reimbursement event named -- too generic to trace to a concrete RCM signal per evidence-based classification rule.",
    evidence_quote_or_field="'Policies that reduce hospital resources without addressing the true drivers of healthcare costs are not solutions.'"
)

with open("classified_rows_linkedin.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2, ensure_ascii=False)

print("wrote", len(rows), "rows")
