import json

INPUT_FILE = "aapc_test_threads.json"
OUTPUT_FILE = "aapc_canonical_posts.json"


def build_canonical_posts():

    # Load extracted AAPC threads
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        threads = json.load(f)

    canonical_posts = []

    for thread in threads:

        for post in thread["posts"]:

            canonical_post = {
                # -------------------------
                # SOURCE / RAW DATA
                # -------------------------
                "source": thread["source"],

                "source_item_id": thread["source_item_id"],

                "thread_id": thread["source_item_id"],

                "post_id": post["post_id"],

                "title": thread["title"],

                "url": thread["url"],

                "post_url": (
                    thread["url"]
                    + "#"
                    + post["post_id"]
                    if post["post_id"]
                    else thread["url"]
                ),

                "text": post["text"],

                "author_name": post["author_name"],

                "author_profile_url": post["author_profile_url"],

                "author_id": None,

                "author_role": None,

                "organization_name": None,

                "organization_url": None,

                "location": post["location"],

                "created_at": post["created_at"],

                "collected_at": None,

                "engagement": None,

                "parent_id": None,

                "conversation_id": thread["source_item_id"],

                "media_type": "text",

                # -------------------------
                # INTELLIGENCE FIELDS
                # -------------------------
                "rcm_relevant": None,

                "problem_evidence": None,

                "first_person": None,

                "problem_category": None,

                "pain_management_relevant": None,

                "seeking_level": None,

                "evidence_quote": None,

                "classification_reason": None,

                "classification_version": None,

                # -------------------------
                # EXTRACTED / DERIVED TAGS
                # -------------------------
                "procedure_tags": [],

                "payer_tags": [],

                "denial_reason_tags": [],

                # -------------------------
                # RAW SOURCE PRESERVATION
                # -------------------------
                "raw_data": {
                    "thread": thread,
                    "post": post
                }
            }

            canonical_posts.append(canonical_post)

    return canonical_posts


def main():

    posts = build_canonical_posts()

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            posts,
            f,
            indent=2,
            ensure_ascii=False
        )

    print("================================")
    print("AAPC Canonical Dataset")
    print("================================")

    print(f"Threads processed: 3")
    print(f"Posts processed: {len(posts)}")
    print(f"Saved to: {OUTPUT_FILE}")

    print("\nFirst 3 canonical records:")

    for post in posts[:3]:

        print("\n--------------------------------")

        print(
            "Thread:",
            post["title"]
        )

        print(
            "Post ID:",
            post["post_id"]
        )

        print(
            "Author:",
            post["author_name"]
        )

        print(
            "Location:",
            post["location"]
        )

        print(
            "Created:",
            post["created_at"]
        )

        print(
            "RCM Relevant:",
            post["rcm_relevant"]
        )

        print(
            "Problem Category:",
            post["problem_category"]
        )


if __name__ == "__main__":
    main()