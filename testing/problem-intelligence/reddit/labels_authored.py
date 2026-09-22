"""
Hand-authored Phase 1 labels, one record per post id.

Every label was assigned by reading the post text in
data/reddit_60_posts.json. The `notes` field carries the quote or the
specific absence the label rests on, so each label is traceable back to the
post. Nothing here is inferred from the subreddit, the author name, or the
score.

Labelling rules actually applied (recorded so the run is reproducible):

  relevant_to_rcm
      yes  = the post concerns revenue cycle / billing / coding / payer /
             credentialing / practice-operations WORK.
      no   = the post concerns the labour market around that work -- exams,
             certification, job hunting, schooling, pay, career transitions.
             These are real posts and real frustrations, but they are not
             evidence of an operational RCM problem.

  problem_evidence
      Requires relevant_to_rcm = yes. Set to yes only where the post shows a
      concrete problem someone is actually experiencing. Industry commentary,
      pure knowledge questions with no blocker, self-promotion and
      anticipatory worry ("I'm nervous about the learning curve") are no.

  first_person_problem
      yes     = the author, or the author's organisation, has the problem.
      no      = the problem belongs to someone else, or no problem is present.
      unclear = the framing does not settle whether it is theirs.

  seeking_level
      L0 = describes a problem, asks for nothing
      L1 = wants information, a fact, an interpretation, or advice
      L2 = wants a solution -- a method, tool, process or workaround -- for an
           ongoing problem
      L3 = wants a vendor, service or company
      L4 = taking an internal action such as hiring or contracting

  identifiable_organization
      The organisation the AUTHOR works for or on behalf of. Third-party orgs
      named in a post (payers, software vendors, other providers, prospective
      employers) do NOT count -- those are tracked in `orgs_mentioned` instead,
      because naming a payer you are fighting is not the same as identifying
      yourself.

  painmedpa_service_match
      yes     = first-person operational problem at a provider organisation, in
                a service area PainMed-PA plausibly sells (prior auth, denials,
                billing/RCM, credentialing), AND pain_management_relevant = yes.
      unclear = same kind of operational problem, but the specialty is unknown
                or outside pain management.
      no      = not an operational provider-organisation problem at all.
"""

# (post_id, relevant_to_rcm, problem_evidence, first_person_problem,
#  problem_category, seeking_level, identifiable_role,
#  identifiable_organization, pain_management_relevant,
#  painmedpa_service_match, orgs_mentioned, notes)

LABELS = [
    (
        "t3_1wks93c", "yes", "yes", "yes", "Coding & Documentation", "L1",
        "yes", "no", "no", "unclear", ["AHA", "AAPC"],
        "Concrete blocker on coding reference access: \"I can't afford the $100+ paid access the AHA or AAPC site has.\" "
        "Role evidenced by \"a new position I have to take an HCC exam for\". Wants a fact about how others get access, "
        "not a service, so L1. Individual resource problem rather than a practice operations problem.",
    ),
    (
        "t3_1wj6a9k", "no", "no", "no", "None", "L1",
        "yes", "no", "no", "no", [],
        "Labour-market post: \"I just passed my CPC-A exam ... getting ready to start applying for jobs.\" "
        "Role is stated -- \"I do currently work in medical records in specialty office prepping charts\" -- "
        "but no operational RCM problem is described.",
    ),
    (
        "t3_1wi50ix", "yes", "yes", "yes", "Coding & Documentation", "L0",
        "yes", "no", "no", "no", [],
        "Upcoding pressure from physicians: \"Asking us to submit inaccurate codes for better reimbursement ... is potential fraud.\" "
        "Author is inside the affected group (\"our hard-earned certifications\"), so first-person, but it is a generalised "
        "RANT/VENT with no specific incident or employer -- weaker than incident-level evidence. Asks for nothing, so L0.",
    ),
    (
        "t3_1wi3y2k", "yes", "yes", "yes", "Denials & Appeals", "L2",
        "yes", "no", "no", "unclear", ["TheraNest"],
        "Strong first-person operational evidence: \"It's been months and I haven't been paid. My claims keep getting rejected.\" "
        "Role from \"Slp private practice\". L2 -- \"SOS contemplating switching billing systems\" is solution-seeking, "
        "though no vendor recommendation is requested. Specialty is speech-language pathology, not pain.",
    ),
    (
        "t3_1whxe3f", "no", "no", "no", "None", "L1",
        "no", "no", "no", "no", ["AAPC"],
        "Exam logistics -- whether used books are allowed. No RCM operational content, no role stated.",
    ),
    (
        "t3_1wh7k1f", "yes", "yes", "yes", "Denials & Appeals", "L1",
        "yes", "no", "no", "unclear", [],
        "Live claim problem: \"their primary came back with a remit CO-204\" with a Medicaid secondary. "
        "Billing role implied by working the remit. Asks for interpretation (\"Can anyone help with clarification\"), so L1. "
        "Specialty not stated.",
    ),
    (
        "t3_1wh1a0j", "no", "no", "no", "None", "L1",
        "yes", "no", "no", "no", [],
        "Job-market post despite deep RCM background. Role is well evidenced -- \"CPC, multiple Epic revenue cycle certifications, "
        "and nearly 9 years of experience in healthcare revenue cycle\" -- and employer type is given (\"a hospital system\") "
        "but never named. No operational problem: the difficulty is getting hired.",
    ),
    (
        "t3_1wg6h95", "no", "no", "no", "None", "L1",
        "no", "no", "no", "no", [],
        "One-line question about CBCS classes. No role, no organisation, no problem.",
    ),
    (
        "t3_1welq8u", "yes", "no", "no", "None", "L1",
        "no", "no", "no", "no", [],
        "Relevant to coding but NOT problem evidence -- this is exactly the commentary case. Author wants anecdotes to win an "
        "argument that \"coding is not black and white\" against a spouse who thinks AI will take over. "
        "Not currently in role: \"never obtained my certification.\"",
    ),
    (
        "t3_1wejcu1", "yes", "yes", "yes", "Denials & Appeals", "L1",
        "yes", "no", "no", "unclear", [],
        "First-person denial: \"We got a denial that said the patient was outside of the diagnosis age range.\" "
        "Role implied by coding the claim and reporting to \"higher ups\". L1 -- the ask is a citable source for the "
        "M81.0 age range, a fact, not a method. Diagnosis is osteoporosis, not pain management.",
    ),
    (
        "t3_1wdoty0", "yes", "yes", "unclear", "Credentialing & Enrollment", "L1",
        "unclear", "no", "no", "unclear", [],
        "Credentialing compliance concern -- an NPI being registered for someone \"not practicing ... nothing to do with patient care\". "
        "first_person marked unclear because the conditional phrasing (\"if I have a credential specialist registering\") does not "
        "settle whether this is a live situation or a hypothetical. Role never stated.",
    ),
    (
        "t3_1wcgvv8", "yes", "yes", "yes", "Staffing & Capacity", "L1",
        "yes", "no", "no", "no", [],
        "First-person capacity evidence at an employer: \"We constantly work OT and have holidays taken away from us\", plus "
        "micromanaging over 4 years. Role explicit -- \"an ED coder for 11 years\". Employee-side strain, not a practice "
        "shopping for help, so no service match. Ask is career advice, L1.",
    ),
    (
        "t3_1wb30rw", "no", "no", "no", "None", "L1",
        "unclear", "unclear", "no", "no", ["CSI (unspecified)"],
        "Asks what remote work at a contractor is like. Org marked unclear: the title names \"Csi companies\" and the author says "
        "\"Got a contract non coding position\", but which CSI, and whether it is confirmed, is not established. "
        "Role is a \"non coding position\", unspecified.",
    ),
    (
        "t3_1w9r1mz", "no", "no", "no", "None", "L2",
        "no", "no", "no", "no", ["AAPC"],
        "AAPC apprentice-removal form is blocking them and they want a way through it -- a concrete blocker with a workaround "
        "sought, so L2, but the subject is certification admin, not revenue cycle work.",
    ),
    (
        "t3_1w79yh4", "no", "no", "no", "None", "L1",
        "no", "no", "no", "no", [],
        "Two-line question about the difficulty of a 1-year certificate course.",
    ),
    (
        "t3_1w6wa1d", "yes", "no", "no", "None", "L1",
        "unclear", "no", "no", "no", [],
        "Coding-standards question (which ICD-10 version the UK uses). Relevant to coding work but no problem is described "
        "and no role is given beyond the implication of working somewhere that codes.",
    ),
    (
        "t3_1w6shp6", "no", "no", "no", "None", "L2",
        "no", "no", "no", "no", [],
        "Job-search distress -- \"I've gotten back 60 denials\" refers to job rejections, not claim denials. "
        "L2 because \"Is there anything else I can do?\" seeks a remedy, but the domain is the labour market. "
        "Not in role: CPC-A, unemployed.",
    ),
    (
        "t3_1w6pp7t", "yes", "yes", "yes", "Technology & Workflow", "L3",
        "unclear", "no", "no", "unclear", ["Kipu"],
        "Clear L3 -- buying intent stated outright: \"Looking for someone that's well versed in billing residential treatment "
        "facility claim and/or uses Kipu ... I am willing to pay for one on one training.\" Problem is a platform capability gap. "
        "Role implied by needing to bill RTF claims but never stated. Behavioural health, not pain.",
    ),
    (
        "t3_1w6mnzo", "yes", "yes", "yes", "Technology & Workflow", "L1",
        "yes", "no", "no", "no", [],
        "Detailed first-person workflow failure: OCR \"80% of the time it can't even read patient data ... requiring us to go in "
        "and manually correct it all\", against a background of \"we're understaffed\". Role: \"a medical administration job\" "
        "handling billing, claims and theatre lists. Closing \"What do I do?\" is advice about workplace conduct, so L1. "
        "\"Theatre lists\" suggests a non-US health system -- relevant to whether this generalises to US practices.",
    ),
    (
        "t3_1w6klj1", "yes", "no", "no", "None", "L1",
        "yes", "no", "no", "no", [],
        "Relevant topic (provider-based department billing/compliance) but the author is researching, not suffering: "
        "\"I'm a medical student and eventually hope to own my own practice.\" Role identifiable but not an RCM role.",
    ),
    (
        "t3_1w6k1x4", "no", "no", "no", "None", "L1",
        "yes", "no", "no", "no", [],
        "Compensation and career decision -- \"$60k/year doesn't go very far\", new job vs second job. "
        "Role well evidenced: \"I have my CCS and have been an inpatient coder since 2021.\" No operational problem.",
    ),
    (
        "t3_1w60ln3", "yes", "yes", "yes", "Coding & Documentation", "L1",
        "yes", "no", "no", "unclear", [],
        "Concrete audit failure: \"I missed a point for not coding the external cause for a wound debridement ... I was docked.\" "
        "Role: \"I've been a coder for many years.\" L1 -- wants \"a valid source to prove it\", a citation rather than a method.",
    ),
    (
        "t3_1w5k73w", "yes", "no", "no", "None", "L1",
        "yes", "no", "no", "no", ["NYM"],
        "NOT problem evidence, deliberately: nothing is broken. The author reports a rumour that \"my facility will start "
        "implementing AI automation to take over ED coding starting in 2027\" and says \"I'm feeling anxious about it.\" "
        "Anticipatory concern about a future vendor implementation. Role is clear (codes OP surgery and Observation); "
        "facility is referred to but never named.",
    ),
    (
        "t3_1w5i8qr", "yes", "yes", "yes", "Coding & Documentation", "L2",
        "yes", "no", "no", "no", ["AAPC"],
        "First-person accuracy problem with a trend: \"the number of audits that need corrections seems to be increasing\", and "
        "support has failed -- \"I've asked the leadership above me for assistance in seeing if they see any patterns and really "
        "have not been given me anything.\" L2 confirmed by the closing ask for \"inpatient training that's not super expensive\". "
        "Individual performance problem, so no service match.",
    ),
    (
        "t3_1w4cz5h", "no", "no", "no", "None", "L1",
        "no", "no", "no", "no", [],
        "Asks CPC-As who did NOT struggle to find work. Labour market, no role stated for the author.",
    ),
    (
        "t3_1w40y68", "no", "no", "no", "None", "L0",
        "no", "no", "no", "no", [],
        "AutoModerator monthly discussion thread. Counted, not skipped -- it is part of what a naive recency pull returns, "
        "and that is itself a finding for collector design.",
    ),
    (
        "t3_1w3l8vx", "yes", "yes", "yes", "Coding & Documentation", "L1",
        "yes", "no", "no", "unclear", [],
        "First-person audit finding against an outsourced biller: \"I am working on an audit for an outside billing company. "
        "They are often adding additional units or decreasing units for codes H0038 and H2015.\" Categorised as Coding & "
        "Documentation because the defect is in unit reporting; the vendor dimension is real but the author is the auditor, "
        "not a dissatisfied client. L1 -- \"Am I way off base here?\" seeks validation. H0038/H2015 are behavioural health.",
    ),
    (
        "t3_1w3d4en", "no", "no", "no", "None", "L1",
        "yes", "no", "no", "no", [],
        "Career transition question, coder to biller. Role evidenced: \"working as a medical coder for 15 yrs ... I have my RHIT.\"",
    ),
    (
        "t3_1w0c5bk", "yes", "yes", "yes", "Staffing & Capacity", "L1",
        "yes", "no", "no", "no", [],
        "First-person throughput problem with numbers: \"The location i work at said 200 cases is minimum ... In 8 hours I get to "
        "150 usually.\" Role: data entry billing in pathology. L1 -- asks whether the quota is normal, which is a fact about "
        "industry norms. Employee-side, so no service match.",
    ),
    (
        "t3_1w04mdh", "yes", "yes", "yes", "Coding & Documentation", "L1",
        "yes", "no", "no", "unclear", [],
        "Documentation insufficiency, first person: \"why do the drs i code for try to bill this shit and then give me the most "
        "basic short exam ive ever seen to try and go off of.\" Role: codes for physicians. L1 -- \"is there a list somewhere of "
        "the shit required for those weird Q modifiers\" is a request for a reference. Routine foot care/podiatry, not pain.",
    ),
    (
        "t3_1vr3umd", "yes", "no", "no", "None", "L1",
        "no", "no", "no", "no", [],
        "Topic is denials but this is NOT the author's problem -- \"I keep hearing that CO-16 ... corrected claims eat a lot of "
        "time, and I'm trying to understand why\", addressed to \"those of you who deal with these daily\". Reads as discovery "
        "research: asks for time-per-claim, tooling and \"What's the part that annoys you most?\" No role claimed. "
        "Near-duplicate of t3_1vr3ncs by the same author u/Maka_66.",
    ),
    (
        "t3_1vr3ncs", "yes", "no", "no", "None", "L1",
        "no", "no", "no", "no", [],
        "Same author and substantially the same text as t3_1vr3umd, posted minutes apart with a different title. "
        "Distinct post id, so it is a distinct row, but the pair is duplicated CONTENT and inflates any per-topic count. "
        "Same reasoning: researcher-voice, not problem evidence.",
    ),
    (
        "t3_1vfiji8", "no", "no", "no", "None", "L1",
        "no", "no", "no", "no", ["AAPC"],
        "Asks how long AAPC self-paced CPC training takes. Certification, not revenue cycle work.",
    ),
    (
        "t3_1vfddl7", "no", "no", "no", "None", "L1",
        "yes", "no", "no", "no", ["AAPC", "Coursera", "LinkedIn", "Indeed"],
        "Career transition into remote billing from abroad. Role identifiable -- \"I'm a medical doctor from the Dominican "
        "Republic ... taking the Certified Professional Biller (CPB) course\" -- but the ask is about job boards and "
        "certification order.",
    ),
    (
        "t3_1vfaugc", "yes", "yes", "no", "Reimbursement & Underpayment", "L1",
        "no", "no", "no", "no", ["BCBS", "DuPage Medical Group (Duly)"],
        "Genuine, specific billing problem -- a claim adjudicated at Tier 2 because \"DuPage Medical Group billing ... is Tier 2\" "
        "although the provider is Tier 1 -- but it is the author's FRIEND's problem and the author is a consumer, not RCM staff. "
        "Orgs are named, yet both are third parties, so identifiable_organization stays no under the author's-own-org rule.",
    ),
    (
        "t3_1veukld", "no", "no", "no", "None", "L1",
        "yes", "no", "no", "no", ["HFMA"],
        "Career pathing into a Revenue Cycle Analyst role. Role evidenced: \"I've been in Patient Access for about 6 years\" "
        "plus USAF Health Service Admin. No operational problem.",
    ),
    (
        "t3_1veuaxj", "no", "no", "no", "None", "L1",
        "no", "no", "no", "no", ["Carle Health"],
        "Title-only post, body empty -- \"Any coders work for Carle Health ?\" Employer sounding-out. "
        "Carle Health is a third party, not established as the author's employer.",
    ),
    (
        "t3_1veqie0", "no", "no", "no", "None", "L1",
        "no", "no", "no", "no", [],
        "Entry-level job seeking in NYC/NJ. Asks for \"companies that can help\" -- these are prospective EMPLOYERS, not vendors, "
        "so this is not L3 despite the recommendation-shaped wording.",
    ),
    (
        "t3_1veg7eo", "yes", "no", "no", "None", "L1",
        "no", "no", "no", "no", ["CMS"],
        "Relevant topic (CMS LEAD model) but the author is harvesting questions, not reporting a problem: \"Working on a project "
        "about the CMS LEAD model and want to make sure I'm covering what people want to know.\" Content research.",
    ),
    (
        "t3_1ve5mfi", "yes", "no", "no", "None", "L0",
        "yes", "no", "no", "no", ["CAQH"],
        "Self-promotion, not a problem: a credentialing specialist advertising availability -- \"five years of experience in CAQH "
        "and provider data management.\" Role is clearly identifiable. L0 is used as the floor because the seeking ladder has no "
        "value for supply-side posts; this is someone offering a service, not seeking one.",
    ),
    (
        "t3_1ve4rub", "yes", "no", "no", "None", "L1",
        "no", "no", "no", "no", ["Cotiviti"],
        "Title-only post, body empty: \"THOUGHTS ON COTIVITI\". Cotiviti is a payment-integrity vendor, so the topic is RCM-adjacent, "
        "but with no body it is impossible to tell whether this is about working there or about fighting their audits. "
        "Logged as an evidence limit, not guessed at.",
    ),
    (
        "t3_1ve2hzy", "no", "no", "no", "None", "L1",
        "no", "no", "no", "no", [],
        "Title-only externship request in San Jose, body empty. Labour market.",
    ),
    (
        "t3_1vdvoox", "yes", "no", "no", "None", "L1",
        "no", "no", "no", "no", [],
        "Title-only, body empty: \"Does anyone own their own medical billing and coding company?\" Business-ownership curiosity "
        "with no problem and no role stated.",
    ),
    (
        "t3_1vd7cz0", "yes", "yes", "yes", "Technology & Workflow", "L2",
        "yes", "no", "no", "unclear", ["AdvancedMD"],
        "Strong first-person operational defect: \"We got a check in ERA from Insurance 1, and somehow 2 Insurance 2 patients got "
        "$0 'payments' posted\", plus an audit trail anomaly -- \"the payment was posted 'by the employee' 2.5 hours prior to them "
        "arriving at work.\" Role evidenced by working ERAs, EOBs and audits. L2: an unresolved integrity problem they are "
        "actively trying to explain (\"Curious how this happened and how many other times it has\"). Practice never named.",
    ),
    (
        "t3_1vctchr", "yes", "yes", "yes", "Coding & Documentation", "L2",
        "no", "no", "no", "no", ["Quest"],
        "Real miscoding with a financial consequence -- TSH (84443) linked to Z13.1 diabetes screening and lipoprotein (83695) to "
        "E53.8 -- so the labs were denied. It IS the author's own problem, hence first_person yes, but the author is the PATIENT, "
        "not RCM staff, so identifiable_role is no. L2: the closing question is a resolution path -- \"do I first contact my PCP "
        "directly ... Or the medical system's billing office ... Or quest? Or my insurance company?\"",
    ),
    (
        "t3_1vct8j6", "no", "no", "no", "None", "L1",
        "no", "no", "no", "no", ["Quizlet"],
        "Asks for CPC Quizlet flashcard sets. Exam prep.",
    ),
    (
        "t3_1vcndms", "no", "no", "no", "None", "L1",
        "yes", "no", "no", "no", [],
        "Asks whether a billing/coding cert helps reach a hospital accounting job. Role given -- \"a very entry level support role "
        "at a hospital with a bachelors degree in accounting\" -- but the subject is career ROI.",
    ),
    (
        "t3_1vcazum", "yes", "no", "no", "None", "L1",
        "yes", "no", "no", "no", [],
        "NOT problem evidence: the concern is prospective. \"I have an opportunity to work remote for one of our clinics soon but "
        "it will be RHC billing which I have never done before ... nervous about the learning curve.\" Nothing is currently "
        "failing. Role is clear: facility/professional biller for a hospital, 1.5 years.",
    ),
    (
        "t3_1vc5jzy", "no", "no", "no", "None", "L1",
        "yes", "no", "no", "no", ["Preppy"],
        "Choosing between a community college program and Preppy. Role: \"changing careers from being a nursing assistant\".",
    ),
    (
        "t3_1vc1zga", "yes", "yes", "yes", "Coding & Documentation", "L1",
        "yes", "no", "no", "unclear", [],
        "Live coding blocker on a real encounter: \"this patient came in was seen by our doctor and it for OM resolved. Is there a "
        "better way of coding this?\" Role explicit: \"I bill out for a PCP office.\" Mild but genuine and first-person. "
        "Primary care, not pain.",
    ),
    (
        "t3_1vc0fyk", "yes", "yes", "yes", "Coding & Documentation", "L2",
        "yes", "no", "yes", "yes", [],
        "The single best PainMed-PA-shaped post in the sample. Hard operational constraint: \"This gives me 13 diagnoses, but a "
        "CMS-1500 only allows 12 diagnosis codes.\" Role explicit -- \"I'm a newer chiropractor\" -- and it is their own "
        "documentation and claims. L2: wants a decision method (\"how do you decide which diagnosis to leave off?\") and pointer "
        "linkage rules for 98941 and 97140. pain_management_relevant = yes on the text alone: cervical and lumbar radiculopathy, "
        "neck/low back/shoulder pain, MVA personal injury. Chiropractic rather than interventional pain medicine, which is worth "
        "noting, but the clinical and coding territory overlaps directly.",
    ),
    (
        "t3_1vbro6x", "no", "no", "no", "None", "L1",
        "yes", "yes", "no", "no", ["Access Healthcare Trivandrum"],
        "Title-only, body empty, but the title itself names the author's OWN employer: \"I am a medical coder in India. I have "
        "recently joined access healthcare trivandrum.\" That makes it one of only two posts in 60 with an author-attributable "
        "organisation. Subject is workplace conditions, not an operational problem.",
    ),
    (
        "t3_1vbarbf", "yes", "no", "unclear", "None", "L1",
        "unclear", "no", "no", "no", [],
        "Coding interpretation question -- whether G2211 can be added to 99211 + 85610QW for protime monitoring. Presented as a "
        "\"Scenario:\", which does not settle whether it is a live case, hence first_person unclear. This is revenue optimisation, "
        "not a problem: nothing is described as failing.",
    ),
    (
        "t3_1vb8pz7", "no", "no", "no", "None", "L0",
        "yes", "no", "no", "no", [],
        "Supply-side post: a job seeker listing experience and asking to be contacted (\"Please reach out to me\"). Role is well "
        "evidenced -- patient access, front desk, insurance verification, denial follow-up, Medicaid claims, payment posting, "
        "3 years. A past employer problem is mentioned (\"an employer's inability to provide me with the necessary technology\") "
        "but it is historical and not an operational problem now.",
    ),
    (
        "t3_1vb6kv8", "no", "no", "no", "None", "L1",
        "unclear", "no", "no", "no", ["CVS"],
        "Asks how to strengthen an application for a CVS Claims Benefit Specialist role. Current role only hinted at -- "
        "\"auto insurance is not the change I want\" -- so role is unclear. CVS is a prospective employer, a third party.",
    ),
    (
        "t3_1vb49of", "no", "no", "no", "None", "L1",
        "yes", "no", "no", "no", [],
        "Career change into healthcare after a layoff. Role evidenced: \"I worked in billing and accounts receivable\" at a SaaS "
        "company. The billing experience is non-healthcare, which matters if this is ever used as role evidence.",
    ),
    (
        "t3_1vb45x7", "no", "no", "no", "None", "L1",
        "yes", "no", "no", "no", [],
        "Career development -- \"How hard is IP coding compared to OP coding?\" Role: \"working as an OP coder for about 4 years.\"",
    ),
    (
        "t3_1v9vu1u", "yes", "yes", "yes", "Authorization & Pre-Certification", "L2",
        "yes", "no", "unclear", "unclear", ["Availity"],
        "Strong first-person operational problem at scale: \"we can't fully rely on it because the information is often "
        "incomplete. We also can't use portals like Availity since we work with a large number of providers, each with different "
        "NPIs and Tax IDs.\" Categorised as Authorization & Pre-Certification because the failing activity is pre-service benefit "
        "and coverage verification; the portal limitation is the mechanism. L2 -- \"How do you usually verify coverage for CCM, "
        "PCM, RTM\" asks for a working method. pain_management_relevant unclear: RTM is commonly musculoskeletal, but the post "
        "never says so. Service match unclear for a different reason -- the author's org is itself an RCM service provider, "
        "so it is a peer or competitor rather than a prospect.",
    ),
    (
        "t3_1v9rx5n", "yes", "yes", "yes", "Denials & Appeals", "L2",
        "yes", "no", "no", "unclear", ["Healthy Blue North Carolina"],
        "The highest-quality denial evidence in the sample: payer named, codes named (97153, 97155, 97156, 97151), duration given "
        "-- \"For the past few months Healthy Blue North Carolina (Medicaid MCO) has been denying telehealth services as "
        "'non-covered under the patient's plan'\" -- and escalation already exhausted: \"the authorizations department doesn't seem "
        "to have any information + when I call the eligibili department they give me a nonsense answer.\" Role explicit: \"I work "
        "with claim denials for a facility providing outpatient ABA services in NC.\" Facility itself never named. ABA, not pain.",
    ),
    (
        "t3_1v9gwor", "yes", "yes", "yes", "Vendor / Outsourcing Dissatisfaction", "L3",
        "yes", "no", "no", "unclear", [],
        "The clearest L3 in the sample -- explicit vendor-seeking with stated dissatisfaction: \"the only companies(2 that I know "
        "of) that do this specific type of billing don't seem trustworthy and also get a very high percentage. Can anyone advise "
        "how to find a reputable person or company to do this?\" Role and practice type explicit: \"I am a paramedical tattoo "
        "practitioner\" doing post-mastectomy areola and scar work, in PA. Practice never named. Not pain management.",
    ),
]
