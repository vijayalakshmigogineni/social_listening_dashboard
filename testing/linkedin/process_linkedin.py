import json
from pathlib import Path


# ---------------------------------------
# File locations
# ---------------------------------------

INPUT_FILE = Path("data/raw/linkedin_posts.json")
OUTPUT_DIR = Path("data/processed")
OUTPUT_FILE = OUTPUT_DIR / "linkedin_posts_processed.json"


# ---------------------------------------
# Keywords
# ---------------------------------------

PAYERS = {
    "UnitedHealthcare": [
        "unitedhealthcare",
        "united healthcare",
        "uhc",
        "unitedhealth",
    ],
    "Humana": [
        "humana",
    ],
    "Aetna": [
        "aetna",
    ],
    "Cigna": [
        "cigna",
    ],
    "Medicare": [
        "medicare",
        "cms",
        "centers for medicare",
    ],
    "Blue Cross": [
        "blue cross",
        "bcbs",
        "blue shield",
    ],
}


PROCEDURES = {
    "RFA": [
        "rfa",
        "radiofrequency ablation",
        "radiofrequency",
    ],
    "PNS": [
        "pns",
        "peripheral nerve stimulation",
    ],
    "SCS": [
        "scs",
        "spinal cord stimulation",
        "spinal cord stimulator",
    ],
    "ESI": [
        "esi",
        "epidural steroid injection",
        "epidural injection",
    ],
    "SI Joint": [
        "si joint",
        "sacroiliac",
    ],
    "Kyphoplasty": [
        "kyphoplasty",
    ],
}


TOPICS = {
    "Authorization": [
        "prior authorization",
        "prior auth",
        "authorization",
        "preauthorization",
        "precertification",
    ],
    "Denials": [
        "denial",
        "denials",
        "denied",
        "claim denial",
    ],
    "Coverage": [
        "coverage",
        "covered",
        "not covered",
        "coverage policy",
    ],
    "Documentation": [
        "documentation",
        "medical records",
        "clinical documentation",
    ],
    "Reimbursement": [
        "reimbursement",
        "payment",
        "payments",
        "underpayment",
        "overpayment",
    ],
    "Policy": [
        "policy",
        "guideline",
        "guidelines",
        "regulation",
        "regulatory",
    ],
}


# ---------------------------------------
# Helper function
# ---------------------------------------

def find_matches(text, keyword_groups):
    """
    Find categories whose keywords appear in the text.
    """

    text = text.lower()

    matches = []

    for category, keywords in keyword_groups.items():

        for keyword in keywords:

            if keyword.lower() in text:
                matches.append(category)
                break

    return matches


# ---------------------------------------
# Load raw data
# ---------------------------------------

print("Loading LinkedIn data...")

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    posts = json.load(file)


print(f"Posts loaded: {len(posts)}")


# ---------------------------------------
# Process posts
# ---------------------------------------

processed_posts = []

for post in posts:

    text = post.get("text", "")

    payers = find_matches(text, PAYERS)
    procedures = find_matches(text, PROCEDURES)
    topics = find_matches(text, TOPICS)

    # A post is considered potentially relevant
    # if it mentions a payer, procedure, or RCM topic.
    relevant = bool(payers or procedures or topics)

    processed_post = {
        "author": post.get("authorName"),
        "author_type": post.get("authorType"),
        "posted_at": post.get("postedAtISO"),
        "text": text,
        "post_url": post.get("url"),

        "likes": post.get("numLikes", 0),
        "shares": post.get("numShares", 0),

        "payers": payers,
        "procedures": procedures,
        "topics": topics,

        "relevant": relevant,
    }

    processed_posts.append(processed_post)


# ---------------------------------------
# Save processed data
# ---------------------------------------

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(
        processed_posts,
        file,
        indent=2,
        ensure_ascii=False
    )


# ---------------------------------------
# Print summary
# ---------------------------------------

relevant_posts = [
    post for post in processed_posts
    if post["relevant"]
]


print()
print("=" * 60)
print("PROCESSING COMPLETE")
print("=" * 60)

print(f"Total posts: {len(processed_posts)}")
print(f"Potentially relevant: {len(relevant_posts)}")
print(f"Potentially irrelevant: {len(processed_posts) - len(relevant_posts)}")

print()
print("Potentially relevant posts:")
print("-" * 60)


for index, post in enumerate(relevant_posts, start=1):

    print()
    print(f"{index}. {post['author']}")

    print("Payers:", post["payers"])
    print("Procedures:", post["procedures"])
    print("Topics:", post["topics"])

    print("Text:")
    print(post["text"][:250])

print()
print(f"Saved processed data to: {OUTPUT_FILE}")