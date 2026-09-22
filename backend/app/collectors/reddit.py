"""
Reddit collector -- ports the proven pattern from
testing/reddit/test_normalise_reddit.py onto the shared Apify client and the
strict canonical schema.

Subreddits are generic RCM/billing communities (per the source research in
testing/SLD-ROADMAP.md Part 1.2), not pain-management-specific. Matched
keywords are stored in source_metadata as candidate evidence for the
analysis pipeline -- they do NOT gate what gets stored. Collection stores
everything; Step 1 of the analysis pipeline decides relevance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.analysis.lexicons import RCM_KEYWORDS
from app.collectors.apify_client import run_actor_sync
from app.collectors.common import parse_datetime

ACTOR_ID = "clearpath~reddit-subreddit-posts-scraper"

DEFAULT_SUBREDDITS = [
    "CodingandBilling",
    "MedicalCoding",
    "Medicalbillingandcoding",
]


def _matched_keywords(text: str) -> list[str]:
    if not text:
        return []
    lowered = text.lower()
    return [kw for kw in RCM_KEYWORDS if kw in lowered]


def _get_text(post: dict[str, Any]) -> str:
    return post.get("text") or post.get("selftext") or post.get("body") or post.get("title") or ""


def _author_fields(post: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    author = post.get("author") or {}
    if isinstance(author, str):
        return None, author, None
    return (
        author.get("id") or author.get("authorId"),
        author.get("name") or author.get("username") or author.get("displayName"),
        author.get("url") or author.get("profileUrl"),
    )


def normalize_post(post: dict[str, Any], subreddit: str) -> dict[str, Any]:
    text = _get_text(post)
    author_id, author_name, author_profile_url = _author_fields(post)

    return {
        "source": "reddit",
        "source_item_id": str(post.get("id") or post.get("postId") or post.get("name")),
        "url": post.get("url") or post.get("permalink"),
        "title": post.get("title"),
        "text": text,
        "author_id": author_id,
        "author_name": author_name,
        "author_profile_url": author_profile_url,
        "author_role": None,
        "organization_name": None,
        "organization_url": None,
        "location": None,
        "created_at": parse_datetime(post.get("createdAt") or post.get("created_at")),
        "collected_at": datetime.now(timezone.utc),
        "engagement": {
            "score": post.get("score"),
            "upvotes": post.get("upvotes"),
            "downvotes": post.get("downvotes"),
            "comments": post.get("numComments") or post.get("commentCount") or post.get("comments"),
        },
        "parent_id": post.get("parentId"),
        "conversation_id": post.get("conversationId") or str(post.get("id") or ""),
        "media_type": "text",
        "raw_data": post,
        "source_metadata": {
            "subreddit": subreddit,
            "matched_rcm_keywords": _matched_keywords(text),
        },
    }


def collect_subreddit(subreddit: str, max_items: int = 100) -> list[dict[str, Any]]:
    raw_posts = run_actor_sync(
        ACTOR_ID,
        {"subreddit": subreddit, "maxPostsPerSubreddit": max_items, "sort": "new"},
    )
    return [normalize_post(p, subreddit) for p in raw_posts]


def collect(subreddits: list[str] | None = None, max_items_per_subreddit: int = 100) -> list[dict[str, Any]]:
    subreddits = subreddits or DEFAULT_SUBREDDITS
    all_records: list[dict[str, Any]] = []
    for subreddit in subreddits:
        print(f"[reddit] collecting r/{subreddit} (max {max_items_per_subreddit})...")
        records = collect_subreddit(subreddit, max_items_per_subreddit)
        print(f"[reddit] r/{subreddit}: {len(records)} posts")
        all_records.extend(records)
    return all_records
