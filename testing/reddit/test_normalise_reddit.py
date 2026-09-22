import os
import sys
import time
import requests
import json
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()


# ============================================================
# CONFIG
# ============================================================

APIFY_TOKEN = os.getenv("APIFY_TOKEN")

if not APIFY_TOKEN:
    raise ValueError("APIFY_TOKEN not found in .env")

ACTOR_ID = "clearpath~reddit-subreddit-posts-scraper"

SUBREDDIT = "CodingandBilling"
MAX_ITEMS = 50

# ============================================================
# BROAD RCM KEYWORDS
# ============================================================

RCM_KEYWORDS = [
    # Billing / RCM
    "medical billing",
    "medical biller",
    "billing",
    "billing company",
    "billing service",
    "revenue cycle",
    "revenue cycle management",
    "rcm",

    # Claims
    "claim",
    "claims",
    "claim submission",
    "claim processing",
    "claim denied",
    "claim denial",
    "claim rejected",
    "claim rejection",
    "resubmit claim",
    "claim rework",

    # Denials / Appeals
    "denial",
    "denials",
    "denied",
    "rejected",
    "rejection",
    "appeal",
    "appeals",
    "denial management",

    # Prior authorization
    "prior authorization",
    "prior auth",
    "prior-auth",
    "pre authorization",
    "preauthorization",
    "pre-auth",
    "authorization",
    "authorizations",

    # Reimbursement / Payment
    "reimbursement",
    "reimburse",
    "reimbursed",
    "payment",
    "payments",
    "payment issue",
    "payment problem",
    "payment delay",
    "underpayment",
    "underpaid",
    "unpaid",

    # Coding
    "medical coding",
    "medical coder",
    "coding",
    "coder",
    "cpt",
    "icd",
    "icd-10",
    "hcpcs",
    "modifier",
    "modifiers",
    "coding error",
    "coding issue",
    "coding denial",

    # Documentation / Medical necessity
    "medical necessity",
    "documentation",
    "documentation requirement",
    "documentation requirements",
    "additional documentation",
    "medical records",
    "clinical documentation",

    # Payers / Insurance
    "payer",
    "payers",
    "insurance",
    "insurance company",
    "medicare",
    "medicaid",
    "medicare advantage",
    "unitedhealthcare",
    "uhc",
    "aetna",
    "cigna",
    "humana",
    "bcbs",
    "blue cross",
    "blue shield",
    "anthem",
    "optum",

    # Other RCM operations
    "accounts receivable",
    "a/r",
    "ar",
    "collections",
    "eligibility",
    "credentialing",
]

# ============================================================
# HELPERS
# ============================================================

def contains_rcm_keyword(text):
    """
    Broad first-pass filter.

    This is NOT the final RCM classifier.
    It only identifies posts worth sending to the next stage.
    """

    if not text:
        return False, []

    text_lower = text.lower()

    matched_keywords = []

    for keyword in RCM_KEYWORDS:
        if keyword in text_lower:
            matched_keywords.append(keyword)

    return len(matched_keywords) > 0, matched_keywords


def get_text(post):
    """
    Try common text fields returned by Reddit scrapers.
    """

    return (
        post.get("text")
        or post.get("selftext")
        or post.get("body")
        or post.get("title")
        or ""
    )


def normalize_post(post):
    """
    Convert Reddit result into the exact canonical
    collection model agreed for SLD.
    """

    text = get_text(post)

    rcm_relevant, matched_keywords = contains_rcm_keyword(text)

    author = post.get("author") or {}

    # Some scrapers may return author as a string
    if isinstance(author, str):
        author_name = author
        author_id = None
        author_profile_url = None
    else:
        author_name = (
            author.get("name")
            or author.get("username")
            or author.get("displayName")
        )

        author_id = (
            author.get("id")
            or author.get("authorId")
        )

        author_profile_url = (
            author.get("url")
            or author.get("profileUrl")
        )

    # Preserve the complete original record
    raw_data = post

    return {
        # -----------------------------
        # Exact canonical collection model
        # -----------------------------

        "source": "Reddit",

        "source_item_id": (
            post.get("id")
            or post.get("postId")
            or post.get("name")
        ),

        "url": (
            post.get("url")
            or post.get("permalink")
        ),

        "title": post.get("title"),

        "text": text,

        "author_id": author_id,

        "author_name": author_name,

        "author_profile_url": author_profile_url,

        "author_role": None,

        "organization_name": None,

        "organization_url": None,

        "location": None,

        "created_at": (
            post.get("createdAt")
            or post.get("created_at")
        ),

        "collected_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "engagement": {
            "score": post.get("score"),
            "upvotes": post.get("upvotes"),
            "downvotes": post.get("downvotes"),
            "comments": post.get("numComments")
                or post.get("commentCount")
                or post.get("comments"),
        },

        "parent_id": post.get("parentId"),

        "conversation_id": (
            post.get("conversationId")
            or post.get("id")
        ),

        "media_type": "text",

        "raw_data": raw_data,

        "source_metadata": {
            "subreddit": SUBREDDIT,
            "matched_rcm_keywords": matched_keywords,
            "keyword_filter": "broad_rcm_v1",
        },
    }


# ============================================================
# FETCH LOOP CONFIG
# ============================================================

TARGET_RCM_CANDIDATES = 50
MAX_ITEMS_CAP = 800
MAX_ATTEMPTS = 4


def run_apify_actor(max_items):
    """Start the actor, wait for it to finish, and return raw posts."""

    run_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs"

    payload = {
        "subreddit": SUBREDDIT,
        "maxPostsPerSubreddit": max_items,
        "sort": "new",
    }

    headers = {
        "Authorization": f"Bearer {APIFY_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        run_url,
        headers=headers,
        json=payload,
        timeout=60,
    )

    print("Start status:", response.status_code)

    if response.status_code != 201:
        print(response.text)
        raise SystemExit("❌ Failed to start Apify Actor")

    run_data = response.json()["data"]

    run_id = run_data["id"]
    dataset_id = run_data["defaultDatasetId"]

    print("✅ Actor started")
    print("Run ID:", run_id)
    print("Dataset ID:", dataset_id)

    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}"

    print("\nWaiting for Reddit collection...")

    while True:

        response = requests.get(
            status_url,
            params={"token": APIFY_TOKEN},
            timeout=30,
        )

        if response.status_code != 200:
            print(response.text)
            raise SystemExit("❌ Could not check run status")

        status = response.json()["data"]["status"]

        print("Status:", status)

        if status in [
            "SUCCEEDED",
            "FAILED",
            "ABORTED",
            "TIMED-OUT",
        ]:
            break

        time.sleep(5)

    if status != "SUCCEEDED":
        print(
            f"\n❌ Reddit collection failed."
            f"\nFinal status: {status}"
        )
        raise SystemExit

    dataset_url = (
        f"https://api.apify.com/v2/datasets/"
        f"{dataset_id}/items"
    )

    response = requests.get(
        dataset_url,
        params={
            "token": APIFY_TOKEN,
            "clean": "true",
        },
        timeout=60,
    )

    if response.status_code != 200:
        print(response.text)
        raise SystemExit("❌ Could not retrieve Reddit dataset")

    return response.json()


# ============================================================
# FETCH UNTIL WE HAVE ENOUGH RCM CANDIDATES
# ============================================================

print("=" * 70)
print("Starting Reddit collection")
print("=" * 70)

current_max_items = MAX_ITEMS
posts = []
normalized_posts = []
rcm_posts = []

for attempt in range(1, MAX_ATTEMPTS + 1):

    print(f"\n--- Attempt {attempt}: requesting {current_max_items} raw posts ---")

    posts = run_apify_actor(current_max_items)

    print("Total posts fetched:", len(posts))

    normalized_posts = [
        normalize_post(post)
        for post in posts
    ]

    rcm_posts = [
        post
        for post in normalized_posts
        if post["source_metadata"]["matched_rcm_keywords"]
    ]

    print(f"RCM candidates so far: {len(rcm_posts)} / target {TARGET_RCM_CANDIDATES}")

    if len(rcm_posts) >= TARGET_RCM_CANDIDATES:
        break

    if current_max_items >= MAX_ITEMS_CAP:
        print(
            f"⚠️ Reached max raw fetch cap ({MAX_ITEMS_CAP}); "
            f"stopping with {len(rcm_posts)} candidates."
        )
        break

    current_max_items = min(current_max_items * 2, MAX_ITEMS_CAP)

rcm_posts = rcm_posts[:TARGET_RCM_CANDIDATES]

print("\n" + "=" * 70)
print("COLLECTION COMPLETE")
print("=" * 70)

if not posts:
    raise SystemExit(
        "❌ No posts fetched — aborting without overwriting existing data files."
    )


# ============================================================
# SAVE ALL RAW POSTS
# ============================================================

with open(
    "reddit_50_raw.json",
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        posts,
        f,
        indent=2,
        ensure_ascii=False,
    )

print("✅ Saved: reddit_50_raw.json")


# ============================================================
# SAVE ALL NORMALIZED POSTS
# ============================================================

with open(
    "reddit_50_normalized.json",
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        normalized_posts,
        f,
        indent=2,
        ensure_ascii=False,
    )

print("✅ Saved: reddit_50_normalized.json")


# ============================================================
# SAVE ALL POSTS AS CSV
# ============================================================

df_all = pd.DataFrame(normalized_posts)

df_all.to_csv(
    "reddit_50_normalized.csv",
    index=False,
    encoding="utf-8",
)

print("✅ Saved: reddit_50_normalized.csv")


# ============================================================
# SAVE RCM CANDIDATES
# ============================================================

with open(
    "reddit_rcm_candidates.json",
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        rcm_posts,
        f,
        indent=2,
        ensure_ascii=False,
    )

print("✅ Saved: reddit_rcm_candidates.json")


df_rcm = pd.DataFrame(rcm_posts)

df_rcm.to_csv(
    "reddit_rcm_candidates.csv",
    index=False,
    encoding="utf-8",
)

print("✅ Saved: reddit_rcm_candidates.csv")


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("RCM FILTER SUMMARY")
print("=" * 70)

print("Total posts fetched :", len(normalized_posts))
print("RCM candidates      :", len(rcm_posts))
print(
    "Filtered out        :",
    len(normalized_posts) - len(rcm_posts),
)

if normalized_posts:

    percentage = (
        len(rcm_posts)
        / len(normalized_posts)
        * 100
    )

    print(
        f"RCM candidate rate  : {percentage:.1f}%"
    )


# ============================================================
# SHOW RCM CANDIDATES
# ============================================================

print("\n" + "=" * 70)
print("RCM CANDIDATES")
print("=" * 70)

for i, post in enumerate(rcm_posts, start=1):

    print("\n" + "-" * 70)

    print(f"POST {i}")

    print("ID:")
    print(post["source_item_id"])

    print("\nTitle:")
    print(post["title"])

    print("\nURL:")
    print(post["url"])

    print("\nMatched RCM keywords:")
    print(
        post["source_metadata"]
        ["matched_rcm_keywords"]
    )

    print("\nText:")
    print(post["text"][:1000])

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)