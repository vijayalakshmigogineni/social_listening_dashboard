"""
Run the v2 hierarchical SLD classifier over the RCM candidate posts.

Usage:
    python run_sld_classification.py

Reads:
    ...\\testing\\reddit\\reddit_rcm_candidates.json
    (produced by testing/reddit/test_normalise_reddit.py)

Writes:
    sld_classifications.csv  (in this directory)
"""

import json
import sys

import pandas as pd
from transformers import pipeline

import sld_pipeline

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

INPUT_PATH = r"C:\Users\HEMA LATHA\social-listening\testing\reddit\reddit_rcm_candidates.json"
OUTPUT_PATH = "sld_classifications.csv"

# facebook/bart-large-mnli was tested and rejected: on the 18-post
# comparison set (see compare_classifiers.py) it forced several
# career/job/general-discussion posts into confident-looking vendor_request/
# L3 results (e.g. "MD from Dominican Republic transitioning to remote
# Medical Billing" -> vendor_request). deberta-v3-base-zeroshot-v2.0 is a
# newer model specifically fine-tuned for zero-shot classification and
# got all of those right, at a similar (base-sized) model weight. Same
# pipeline API -- swap the string if you want to try something else.
MODEL_NAME = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"


def load_posts(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_text(post: dict) -> str:
    title = (post.get("title") or "").strip()
    body = (post.get("text") or "").strip()
    if not body or body == title:
        return title
    return (title + "\n" + body).strip()


def main():
    posts = load_posts(INPUT_PATH)
    print(f"Loaded {len(posts)} RCM candidate posts from {INPUT_PATH}")

    if not posts:
        raise SystemExit("No posts to classify -- nothing to do.")

    print(f"Loading zero-shot model: {MODEL_NAME}")
    classifier = pipeline("zero-shot-classification", model=MODEL_NAME)

    rows = []
    for i, post in enumerate(posts, start=1):
        text = build_text(post)
        matched_keywords = post.get("source_metadata", {}).get(
            "matched_rcm_keywords", []
        )

        result = sld_pipeline.classify_post(classifier, text, matched_keywords)

        row = {
            "source_item_id": post.get("source_item_id"),
            "title": post.get("title"),
            "url": post.get("url"),
            "text": text,
            "matched_keywords": matched_keywords,
            **result,
        }
        rows.append(row)

        print(
            f"[{i}/{len(posts)}] {row['source_item_id']}: "
            f"content_type={result['content_type']} "
            f"intent_level={result['intent_level']} "
            f"sld_candidate={result['sld_candidate']} "
            f"({result['confidence_tier']}"
            f"{', NEEDS REVIEW' if result['needs_review'] else ''})"
        )

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"Saved {len(df)} classified posts to {OUTPUT_PATH}")
    print("=" * 70)

    print("\nContent type counts:")
    print(df["content_type"].value_counts())

    print("\nIntent level counts (NaN = non-operational):")
    print(df["intent_level"].value_counts(dropna=False))

    print("\nSLD candidate counts:")
    print(df["sld_candidate"].value_counts())

    print("\nNeeds review counts:")
    print(df["needs_review"].value_counts())


if __name__ == "__main__":
    main()
