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

from app.collectors.apify_client import run_actor_sync
from app.collectors.common import parse_datetime

ACTOR_ID = "harvestapi/linkedin-post-search"  # no cookies needed; maintained selectors

DEFAULT_QUERY = (
    "(UnitedHealthcare OR Aetna OR Cigna OR Humana OR Medicare OR Medicaid) "
    "prior authorization denial reimbursement billing"
)

# Query-family strategy (see testing/SLD-ROADMAP.md Sec 1.2, Phase 3 Test 3):
# the payer+policy query above selects for policy commentary by construction
# and measured 0/95 practice-voice yield on its own. These families broaden
# recall to posts that describe an operational problem without naming a
# payer. Each query stays a single flat OR-group -- the actor's search
# backend rejects deeply-nested multi-OR-group boolean queries (confirmed in
# testing/linkedin/fetch_linkedin_batch.py).
QUERY_FAMILIES = {
    "payer_policy": DEFAULT_QUERY,
    "practice_voice": (
        '"our billing team" OR "our practice" OR "our claims" OR "our denials" '
        "medical billing revenue cycle"
    ),
    "authorization": (
        "prior authorization OR prior auth OR utilization management OR "
        "utilization review OR medical necessity"
    ),
    "denials_reimbursement": (
        "claim denial OR claim rejection OR appeal OR underpayment OR "
        "reimbursement delay"
    ),
    "vendor_seeking": (
        '"looking for a billing company" OR "recommend a billing service" OR '
        '"outsource our billing" OR "evaluating vendors"'
    ),
}


def normalize_post(post: dict[str, Any], search_query: str) -> dict[str, Any]:
    author = post.get("author") or {}
    engagement = post.get("engagement") or {}
    posted_at = post.get("postedAt") or {}

    return {
        "source": "linkedin",
        "source_item_id": post.get("id") or post.get("linkedinUrl"),
        "url": post.get("linkedinUrl"),
        "title": None,
        "text": post.get("content"),
        "author_id": author.get("linkedinUrl"),
        "author_name": author.get("name"),
        "author_profile_url": author.get("linkedinUrl"),
        "author_role": author.get("info"),
        "organization_name": None,
        "organization_url": None,
        "location": None,
        "created_at": parse_datetime(posted_at.get("date") if isinstance(posted_at, dict) else posted_at),
        "collected_at": datetime.now(timezone.utc),
        "engagement": {
            "likes": engagement.get("likes"),
            "comments": engagement.get("comments"),
            "shares": engagement.get("shares"),
        },
        "parent_id": None,
        "conversation_id": post.get("id"),
        "media_type": "text",
        "raw_data": post,
        "source_metadata": {
            "search_query": search_query,
        },
    }


def collect(query: str = DEFAULT_QUERY, limit: int = 30) -> list[dict[str, Any]]:
    run_input = {
        "searchQueries": [query],
        "maxPosts": limit,
        "sortBy": "date",
    }
    print(f"[linkedin] searching: {query!r} (limit {limit})")
    raw_posts = run_actor_sync(ACTOR_ID, run_input, timeout_s=900)
    print(f"[linkedin] {len(raw_posts)} posts returned")
    return [normalize_post(p, query) for p in raw_posts]


def collect_families(
    query_families: dict[str, str] | None = None, limit_per_query: int = 30
) -> list[dict[str, Any]]:
    """
    Run one actor call per query family (same pattern as reddit.collect()'s
    per-subreddit loop), so each returned post can be tagged with the query
    that found it. The same LinkedIn post can be returned by more than one
    family -- that's expected, and is resolved by the existing
    (source, source_item_id) upsert identity in collectors/common.py, which
    needs no change here.
    """
    query_families = query_families or QUERY_FAMILIES
    all_records: list[dict[str, Any]] = []
    for family, query in query_families.items():
        print(f"[linkedin] family '{family}': {query!r}")
        all_records.extend(collect(query=query, limit=limit_per_query))
    return all_records
