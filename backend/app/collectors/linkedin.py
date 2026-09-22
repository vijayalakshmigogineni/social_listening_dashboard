"""
LinkedIn collector -- ports testing/linkedin/fetch_linkedin_batch.py onto the
shared Apify client and canonical schema.

Per testing/SLD-ROADMAP.md Part 1.2, LinkedIn's RCM corner skews toward
vendor/consultant marketing content rather than practice-side operational
complaints -- volume expectations here should be modest; Step 4's speaker
classification is what will actually separate the marketing signal from the
rare practice-voice post, not the collector.

The search query is deliberately payer-agnostic and specialty-agnostic
(major payers x generic RCM terms), not pain-management-specific.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from app.collectors.apify_client import run_actor_sync
from app.collectors.common import parse_datetime

ACTOR_ID = "Wpp1BZ6yGWjySadk3"  # supreme_coder/linkedin-post

DEFAULT_QUERY = (
    "(UnitedHealthcare OR Aetna OR Cigna OR Humana OR Medicare OR Medicaid) "
    "prior authorization denial reimbursement billing"
)


def _search_url(query: str) -> str:
    return (
        "https://www.linkedin.com/search/results/content/"
        f"?keywords={quote(query)}&origin=FACETED_SEARCH"
    )


def normalize_post(post: dict[str, Any], search_query: str) -> dict[str, Any]:
    author = post.get("author") or {}

    return {
        "source": "linkedin",
        "source_item_id": post.get("urn") or post.get("shareUrn"),
        "url": post.get("url"),
        "title": None,
        "text": post.get("text"),
        "author_id": author.get("id") or post.get("authorUrn"),
        "author_name": post.get("authorName") or author.get("name"),
        "author_profile_url": post.get("authorProfileUrl"),
        "author_role": post.get("authorHeadline") or author.get("headline"),
        "organization_name": None,
        "organization_url": None,
        "location": None,
        "created_at": parse_datetime(post.get("postedAtISO") or post.get("postedAtTimestamp")),
        "collected_at": datetime.now(timezone.utc),
        "engagement": {
            "likes": post.get("numLikes"),
            "comments": post.get("numComments"),
            "shares": post.get("numShares"),
        },
        "parent_id": None,
        "conversation_id": post.get("urn"),
        "media_type": "text",
        "raw_data": post,
        "source_metadata": {
            "is_repost": post.get("isRepost"),
            "author_type": post.get("authorType"),
            "search_query": search_query,
        },
    }


def collect(query: str = DEFAULT_QUERY, limit: int = 25) -> list[dict[str, Any]]:
    run_input = {
        "deepScrape": False,
        "fetchDocumentDetails": False,
        "limitPerSource": limit,
        "numComments": 0,
        "numLikes": 0,
        "rawData": False,
        "urls": [_search_url(query)],
    }
    print(f"[linkedin] searching: {query!r} (limit {limit})")
    raw_posts = run_actor_sync(ACTOR_ID, run_input, timeout_s=900)
    print(f"[linkedin] {len(raw_posts)} posts returned")
    return [normalize_post(p, query) for p in raw_posts]
