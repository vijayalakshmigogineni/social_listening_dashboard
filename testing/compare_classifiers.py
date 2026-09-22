"""
Compare the OLD forced L0-L3 zero-shot classifier (as used in
test_zero_shot.py) against the NEW hierarchical classifier
(sld_pipeline.classify_post) on the same set of example posts.

The example posts below are drawn straight from the real reddit_rcm_
candidates.json data (plus two canonical examples from the SLD business
spec) and deliberately cover every category the business spec cares
about: career, job_search, education, certification_training,
general_discussion, news, problem_experience (L0), information_request
(L1), solution_request (L2), vendor_request (L3), and an "opportunity
without a problem" case.

Usage:
    python compare_classifiers.py

Writes:
    comparison_results.csv
"""

import sys

import pandas as pd
from transformers import pipeline

import sld_pipeline

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

MODEL_NAME = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"

# ---------------------------------------------------------------------
# OLD classifier: exact reproduction of test_zero_shot.py's approach
# ---------------------------------------------------------------------

LEGACY_LABELS = [
    "the author is describing a problem they are experiencing",
    "the author is asking for information",
    "the author is looking for a solution to a problem",
    "the author is looking for a vendor or service provider",
    "the post does not express a specific request or problem-solving intent",
]

LEGACY_LABEL_MAP = {
    LEGACY_LABELS[0]: "L0",
    LEGACY_LABELS[1]: "L1",
    LEGACY_LABELS[2]: "L2",
    LEGACY_LABELS[3]: "L3",
    LEGACY_LABELS[4]: "NONE",
}


def legacy_classify(classifier, text: str):
    result = classifier(text, LEGACY_LABELS, multi_label=False)
    top_label = result["labels"][0]
    top_score = result["scores"][0]
    return LEGACY_LABEL_MAP[top_label], top_score


# ---------------------------------------------------------------------
# Example posts: (expected_category, text)
# ---------------------------------------------------------------------

EXAMPLES = [
    ("career", "MD from Dominican Republic transitioning to remote Medical Billing."),
    ("job_search", "Any coders work for Carle Health ?"),
    ("education/certification", "Healthcare accounting: would a billing and coding cert help me get into it?"),
    ("career", "I am a medical coder in India. I have recently joined access healthcare trivandrum. Is the work there stressful? How is the work atmosphere?"),
    ("career/job_search", "First CPC-a job"),
    ("certification_training", "NHA CBCS exam questions: Nothing on it is what I studied"),
    ("job_search", "Does anyone know of places that will hire and train vs taking billing/coding classes?"),
    ("job_search", "Hiring an Integrative Medicine Biller & Revenue Cycle Management [part-time, remote]"),
    ("job_search/vendor-ish (ambiguous)", "Anyone here do QA/audit work for medical coding? Looking to connect for a paid project"),
    ("problem_experience (L0)", "Our claims keep getting denied by UHC."),
    ("information_request (L1)", "How do you actually rework a CO-16 corrected claim — what's your process?"),
    ("solution_request (L2)", "Is there a better way to manage our denials?"),
    ("vendor_request (L3)", "Can anyone recommend an RCM company?"),
    ("vendor_request / opportunity-without-problem", "I am looking for a medical billing company that handles Medicare claims."),
    ("education/certification", "I am studying for the CPC exam."),
    ("general_discussion", "Newbies and potentials, this is what you are up against. We've all seen the complaints that the market is flooded. Nobody can get a job, etc."),
    ("news/general_discussion", "Working on a project about the CMS LEAD model and want to make sure I'm covering what people want to know. Feels like there is a lot of confusion out there."),
    ("problem_experience (L0)", "SUTTER CHARGED ME HOSPITAL BILLING AS AN OUTPATIENT. Sutter billed me $1,789.00 for nine labs for my yearly health exam. This was a nasty billing surprise as I was out nearly $400 out of pocket for what my insurance did not cover."),
]


def main():
    print(f"Loading zero-shot model: {MODEL_NAME}")
    classifier = pipeline("zero-shot-classification", model=MODEL_NAME)

    rows = []
    for expected, text in EXAMPLES:
        old_label, old_score = legacy_classify(classifier, text)
        new_result = sld_pipeline.classify_post(classifier, text)

        rows.append({
            "expected_category": expected,
            "text": text,
            "OLD_label": old_label,
            "OLD_score": round(old_score, 3),
            "NEW_content_type": new_result["content_type"],
            "NEW_intent_level": new_result["intent_level"],
            "NEW_sld_candidate": new_result["sld_candidate"],
            "NEW_confidence_tier": new_result["confidence_tier"],
            "NEW_needs_review": new_result["needs_review"],
        })

        print("-" * 100)
        print(f"Expected     : {expected}")
        print(f"Text         : {text[:100]}")
        print(f"OLD (forced) : {old_label}  (score={old_score:.2f})")
        print(
            f"NEW (v2)     : content_type={new_result['content_type']}  "
            f"intent_level={new_result['intent_level']}  "
            f"sld_candidate={new_result['sld_candidate']}  "
            f"confidence={new_result['confidence_tier']}"
        )

    print("-" * 100)

    df = pd.DataFrame(rows)
    df.to_csv("comparison_results.csv", index=False, encoding="utf-8")
    print(f"\nSaved {len(df)} comparisons to comparison_results.csv")


if __name__ == "__main__":
    main()
