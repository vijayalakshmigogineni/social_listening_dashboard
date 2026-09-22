"""
Create a manual-labeling template by sampling rows from an existing
sld_classifications.csv (produced by run_sld_classification.py), so you
can hand-label 30-50 posts and measure real accuracy/precision/recall/F1.

Usage:
    python sample_for_labeling.py            # samples 40 rows
    python sample_for_labeling.py 30         # samples 30 rows
"""

import sys

import pandas as pd

INPUT_PATH = "sld_classifications.csv"
OUTPUT_PATH = "labeling_template.csv"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40

    df = pd.read_csv(INPUT_PATH)
    sample = df.sample(n=min(n, len(df)), random_state=42).copy()

    # Empty columns for you to fill in by hand. Leave gold_intent_level
    # blank for non-operational posts (career/education/job/general/news).
    sample["gold_content_type"] = ""
    sample["gold_intent_level"] = ""
    sample["gold_sld_candidate"] = ""
    sample["labeler_notes"] = ""

    cols = [
        "source_item_id", "title", "text", "content_type", "intent_level",
        "sld_candidate", "gold_content_type", "gold_intent_level",
        "gold_sld_candidate", "labeler_notes",
    ]
    sample = sample[[c for c in cols if c in sample.columns]]
    sample.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    print(f"Wrote {len(sample)} rows to {OUTPUT_PATH}")
    print(
        "Open it, read each 'text', and fill in:\n"
        "  gold_content_type   -- one of: problem_experience, "
        "information_request, solution_request, vendor_request, career, "
        "job_search, education, certification_training, "
        "general_discussion, news, other\n"
        "  gold_intent_level   -- L0/L1/L2/L3, or leave blank for "
        "non-operational content types\n"
        "  gold_sld_candidate  -- True if this post should surface on the "
        "dashboard, else False\n\n"
        "Then run: python evaluate_sld_classifier.py"
    )


if __name__ == "__main__":
    main()
