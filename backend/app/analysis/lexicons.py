"""
Shared RCM lexicons/dictionaries used across collection tagging and the
analysis pipeline (Steps 1, 3, 4).

IMPORTANT: these are deliberately broad and specialty-agnostic. Do not add
pain-management-specific weighting here -- procedures like RFA/SCS/PNS/
Intracept/epidurals are listed as ordinary entries in PROCEDURE_TAGS, exactly
like any other procedure, never privileged.

Keywords are candidate evidence for the rule-based first pass of each stage,
never the final decision by themselves (see each step's module for how they
combine with semantic/contextual checks).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Step 1 -- RCM domain relevance lexicon (broad, high recall by design)
# ---------------------------------------------------------------------------
RCM_KEYWORDS = [
    "medical billing", "medical biller", "billing", "billing company", "billing service",
    "revenue cycle", "revenue cycle management", "rcm",
    "claim", "claims", "claim submission", "claim processing", "claim denied",
    "claim denial", "claim rejected", "claim rejection", "resubmit claim", "claim rework",
    "denial", "denials", "denied", "rejected", "rejection", "appeal", "appeals",
    "denial management",
    "prior authorization", "prior auth", "prior-auth", "pre authorization",
    "preauthorization", "pre-auth", "precert", "precertification", "authorization",
    "authorizations", "peer-to-peer", "gold card",
    "reimbursement", "reimburse", "reimbursed", "payment", "payments", "payment issue",
    "payment problem", "payment delay", "underpayment", "underpaid", "overpayment",
    "unpaid", "takeback", "recoupment", "fee schedule", "conversion factor",
    "medical coding", "medical coder", "coding", "coder", "cpt", "icd", "icd-10",
    "hcpcs", "modifier", "modifiers", "coding error", "coding issue", "coding denial",
    "medical necessity", "documentation", "documentation requirement",
    "documentation requirements", "additional documentation", "medical records",
    "clinical documentation",
    "payer", "payers", "insurance", "insurance company", "medicare", "medicaid",
    "medicare advantage", "unitedhealthcare", "uhc", "aetna", "cigna", "humana",
    "bcbs", "blue cross", "blue shield", "anthem", "optum",
    "accounts receivable", "a/r", "ar aging", "collections", "eligibility",
    "credentialing", "caqh", "enrollment", "npi", "lcd", "ncd",
    "clearinghouse", "eob", "era", "remit", "superbill",
]

# ---------------------------------------------------------------------------
# Step 2 -- first-person / peer-directed / pain / seeking markers
# ---------------------------------------------------------------------------
FIRST_PERSON_MARKERS = [
    "our practice", "our clinic", "our office", "our billing team", "our billing dept",
    "our billing department", "our staff", "our providers", "my practice", "my office",
    "i'm the biller", "i'm the coder", "i'm the manager", "i'm the owner",
    "we're a provider", "at our clinic", "we bill", "we submit", "we're hiring",
    "our team", "our company",
]

PEER_QUESTION_MARKERS = [
    "how do you handle", "how do others handle", "how do other practices",
    "has anyone", "does anyone", "anyone else seeing", "anyone else getting",
    "anyone else having", "what are you all doing about", "am i the only one",
]

PAIN_MARKERS = [
    "struggl", "can't keep up", "backlog", "drowning", "spending hours",
    "spending all day", "overwhelm", "nightmare", "behind on", "falling behind",
    "short-staffed", "burnt out", "burned out", "keeps getting denied",
    "huge increase in", "through the roof", "no idea why", "stuck", "sitting in a/r",
    "taking weeks", "taking months", "constantly",
]

SEEKING_MARKERS_BY_LEVEL = {
    "L1": ["how do", "what is", "can someone explain", "does anyone know"],
    "L2": ["is there a better way", "looking for a better", "any suggestions for",
           "recommendations for a tool", "recommendations for software"],
    "L3": ["looking for an rcm company", "looking for a billing company",
           "recommend a vendor", "recommend a billing service", "worth outsourcing",
           "should we outsource", "evaluating vendors", "anyone use a billing service"],
}

VENDOR_SELFPROMO_MARKERS = [
    "we provide", "we offer", "we specialize", "our solution", "our platform",
    "book a demo", "dm me", "link in bio", "contact us for a quote",
]

# ---------------------------------------------------------------------------
# Step 3 -- taxonomy / entity dictionaries
# ---------------------------------------------------------------------------
PAYERS = {
    "UnitedHealthcare": ["unitedhealthcare", "united healthcare", "uhc", "unitedhealth"],
    "Humana": ["humana"],
    "Aetna": ["aetna"],
    "Cigna": ["cigna"],
    "Medicare": ["medicare", "cms", "centers for medicare"],
    "Medicaid": ["medicaid"],
    "Blue Cross Blue Shield": ["blue cross", "bcbs", "blue shield", "anthem"],
    "Optum": ["optum"],
}

# Deliberately broad/specialty-agnostic. Pain-related procedures (RFA, SCS,
# PNS, Intracept, ESI) are ordinary entries here, not privileged in any way.
PROCEDURES = {
    "RFA": ["rfa", "radiofrequency ablation"],
    "PNS": ["pns", "peripheral nerve stimulation"],
    "SCS": ["scs", "spinal cord stimulation", "spinal cord stimulator"],
    "ESI": ["esi", "epidural steroid injection", "epidural injection"],
    "SI Joint Fusion": ["si joint", "sacroiliac"],
    "Kyphoplasty": ["kyphoplasty"],
    "Intracept": ["intracept", "basivertebral nerve ablation"],
    "Colonoscopy": ["colonoscopy"],
    "MRI": ["mri", "magnetic resonance imaging"],
    "Physical Therapy": ["physical therapy", " pt visit", "pt evaluation"],
    "Infusion Therapy": ["infusion therapy", "infusion"],
    "Cardiac Catheterization": ["cardiac catheterization", "cath lab"],
}

DENIAL_REASONS = {
    "Medical Necessity": ["not medically necessary", "medical necessity denial"],
    "Missing/Invalid Documentation": ["missing documentation", "insufficient documentation",
                                       "additional documentation required"],
    "Prior Auth Not Obtained": ["no prior authorization", "authorization not obtained",
                                 "missing prior auth"],
    "Timely Filing": ["timely filing"],
    "Coding Error": ["incorrect coding", "coding error", "invalid modifier",
                      "unbundling", "bundling denial"],
    "Duplicate Claim": ["duplicate claim"],
    "Eligibility": ["not eligible", "eligibility denial", "coverage terminated"],
    "Non-Covered Service": ["not a covered service", "non-covered", "excluded from coverage"],
}

PROBLEM_CATEGORY_KEYWORDS = {
    "authorization_utilization_management": [
        "prior authorization", "prior auth", "precert", "precertification",
        "peer-to-peer", "gold card", "utilization management", "utilization review",
    ],
    "denials_claims_friction": [
        "denial", "denied", "claim rejected", "claim rejection", "appeal",
        "resubmit", "carc", "rarc",
    ],
    "coverage_policy": [
        "not covered", "coverage policy", "lcd", "ncd", "plan policy",
        "policy change", "coverage determination",
    ],
    "documentation_medical_necessity": [
        "medical necessity", "documentation requirement", "clinical documentation",
        "chart notes", "additional documentation",
    ],
    "reimbursement_payment": [
        "underpayment", "underpaid", "overpayment", "fee schedule", "takeback",
        "recoupment", "conversion factor", "reimbursement rate",
    ],
    "procedure_device_access": [
        "step therapy", "device access", "procedure denied", "not approved for",
    ],
}

SPECIALTY_KEYWORDS = {
    "pain_management": ["pain management", "pain clinic", "interventional pain"],
    "orthopedics": ["orthopedic", "orthopedics", "ortho practice"],
    "cardiology": ["cardiology", "cardiologist", "cardiac"],
    "dermatology": ["dermatology", "dermatologist"],
    "primary_care": ["primary care", "family medicine", "internal medicine"],
    "physical_therapy": ["physical therapy", "physical therapist"],
    "behavioral_health": ["behavioral health", "mental health", "psychiatry", "psychology"],
    "radiology": ["radiology", "imaging center"],
    "gastroenterology": ["gastroenterology", "gastroenterologist", "gi practice"],
}

CPT_CONTEXT_MARKERS = ["cpt", "hcpcs", "code", "billed as", "billed under"]

# ---------------------------------------------------------------------------
# Step 6/7 scoring -- severity/impact observable-feature markers.
# Distinct from PAIN_MARKERS (Step 2, "is there a problem at all") -- these
# answer "how bad/how big is it", which is what SEVERITY and part of
# PROBLEM_STRENGTH need as deterministic, inspectable inputs.
# ---------------------------------------------------------------------------
REPETITION_MARKERS = [
    "constantly", "every month", "every week", "every day", "keeps happening",
    "keeps getting denied", "recurring", "ongoing issue", "for months",
    "for weeks", "repeatedly", "over and over",
]

DURATION_MARKERS = [
    "for months", "for weeks", "for over a year", "for the past year",
    "since january", "since last year", "months now", "weeks now",
]

VOLUME_MARKERS = [
    "hundreds of claims", "dozens of claims", "large backlog", "high volume",
    "every claim", "most of our claims", "majority of claims",
]

FINANCIAL_IMPACT_MARKERS = [
    "losing thousands", "lost revenue", "revenue loss", "costing us",
    "written off", "write-off", "unable to get paid", "not getting paid",
    "money we're owed", "underpaid by",
]

OPERATIONAL_IMPACT_MARKERS = [
    "hours reworking", "spending hours", "spending all day", "billing staff spend",
    "our staff spend", "understaffed", "short-staffed", "backlog", "drowning",
    "hours a week", "hours every week", "days to resolve",
]
