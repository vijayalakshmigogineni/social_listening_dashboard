import json
import re


INPUT_FILE = "reddit_normalized.json"
OUTPUT_FILE = "reddit_relevant.json"


# ---------------------------------------------------------
# 1. Terms that indicate healthcare revenue-cycle topics
# ---------------------------------------------------------

HEALTHCARE_TERMS = [
    "medical billing",
    "medical bill",
    "health insurance",
    "healthcare",
    "payer",
    "insurance",
    "claim",
    "claims",
    "remittance",
    "era",
    "eob",
    "denial",
    "denied",
    "appeal",
    "reimbursement",
    "prior authorization",
    "prior auth",
    "authorization",
    "medical necessity",
    "coverage",
    "coding",
    "billing",
    "provider",
]


# ---------------------------------------------------------
# 2. Terms that indicate operational relevance
# ---------------------------------------------------------

OPERATIONAL_TERMS = [
    "rework",
    "resubmit",
    "submission",
    "documentation",
    "missing information",
    "invalid information",
    "payment",
    "underpayment",
    "payment delay",
    "fee schedule",
    "policy",
    "requirement",
    "restriction",
    "approval",
    "denial",
    "appeal",
    "turnaround",
    "processing",
    "authorization",
    "claim",
]


# ---------------------------------------------------------
# 3. Terms that indicate irrelevant career discussions
# ---------------------------------------------------------

CAREER_TERMS = [
    "job",
    "jobs",
    "career",
    "hiring",
    "resume",
    "certification",
    "certified",
    "salary",
    "interview",
    "employment",
    "work from home",
    "remote job",
]


def contains_term(text, terms):
    """
    Return True if any term appears in the text.
    """
    text = text.lower()

    for term in terms:
        if term in text:
            return True

    return False


def classify_relevance(post):
    """
    Decide whether a Reddit post is relevant to SLD.
    """

    title = post.get("title", "")
    content = post.get("content", "")

    text = f"{title} {content}".lower()

    healthcare_match = [
        term
        for term in HEALTHCARE_TERMS
        if term in text
    ]

    operational_match = [
        term
        for term in OPERATIONAL_TERMS
        if term in text
    ]

    career_match = [
        term
        for term in CAREER_TERMS
        if term in text
    ]

    # -----------------------------------------------------
    # Rule 1: Strong operational healthcare discussion
    # -----------------------------------------------------

    if healthcare_match and operational_match:

        return {
            "relevance": "relevant",
            "reason": "Healthcare revenue-cycle topic with operational impact",
            "matched_healthcare_terms": healthcare_match,
            "matched_operational_terms": operational_match,
            "matched_career_terms": career_match,
        }

    # -----------------------------------------------------
    # Rule 2: Career-only discussions
    # -----------------------------------------------------

    if career_match and not operational_match:

        return {
            "relevance": "irrelevant",
            "reason": "Career/employment discussion",
            "matched_healthcare_terms": healthcare_match,
            "matched_operational_terms": operational_match,
            "matched_career_terms": career_match,
        }

    # -----------------------------------------------------
    # Rule 3: Healthcare discussion without clear
    # operational relevance
    # -----------------------------------------------------

    if healthcare_match:

        return {
            "relevance": "review",
            "reason": "Healthcare-related but operational relevance is unclear",
            "matched_healthcare_terms": healthcare_match,
            "matched_operational_terms": operational_match,
            "matched_career_terms": career_match,
        }

    # -----------------------------------------------------
    # Rule 4: Everything else
    # -----------------------------------------------------

    return {
        "relevance": "irrelevant",
        "reason": "No SLD-relevant healthcare topic detected",
        "matched_healthcare_terms": healthcare_match,
        "matched_operational_terms": operational_match,
        "matched_career_terms": career_match,
    }


# ---------------------------------------------------------
# Load normalized Reddit data
# ---------------------------------------------------------

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    posts = json.load(file)


relevant_posts = []
review_posts = []
irrelevant_posts = []


# ---------------------------------------------------------
# Run relevance filter
# ---------------------------------------------------------

for post in posts:

    result = classify_relevance(post)

    post_with_relevance = {
        **post,
        "relevance": result["relevance"],
        "relevance_reason": result["reason"],
        "matched_healthcare_terms": result["matched_healthcare_terms"],
        "matched_operational_terms": result["matched_operational_terms"],
        "matched_career_terms": result["matched_career_terms"],
    }

    if result["relevance"] == "relevant":
        relevant_posts.append(post_with_relevance)

    elif result["relevance"] == "review":
        review_posts.append(post_with_relevance)

    else:
        irrelevant_posts.append(post_with_relevance)


# ---------------------------------------------------------
# Save relevant + review posts
# ---------------------------------------------------------

output = {
    "relevant": relevant_posts,
    "review": review_posts,
}


with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(
        output,
        file,
        indent=2,
        ensure_ascii=False
    )


# ---------------------------------------------------------
# Print results
# ---------------------------------------------------------

print()
print("=" * 70)
print("REDDIT RELEVANCE FILTER")
print("=" * 70)

print(f"Total posts:      {len(posts)}")
print(f"Relevant:         {len(relevant_posts)}")
print(f"Needs review:     {len(review_posts)}")
print(f"Irrelevant:       {len(irrelevant_posts)}")

print()
print("=" * 70)
print("RELEVANT POSTS")
print("=" * 70)

for index, post in enumerate(relevant_posts, start=1):

    print()
    print(f"{index}. {post['title']}")
    print(f"   Community: {post['source_name']}")
    print(f"   Reason:    {post['relevance_reason']}")
    print(f"   Healthcare: {post['matched_healthcare_terms']}")
    print(f"   Operational: {post['matched_operational_terms']}")


print()
print("=" * 70)
print("NEEDS REVIEW")
print("=" * 70)

for index, post in enumerate(review_posts, start=1):

    print()
    print(f"{index}. {post['title']}")
    print(f"   Reason: {post['relevance_reason']}")


print()
print("=" * 70)
print(f"Saved results to: {OUTPUT_FILE}")
print("=" * 70)