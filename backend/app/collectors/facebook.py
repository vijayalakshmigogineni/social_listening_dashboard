"""
Facebook collector -- public group posts via Apify's apify/facebook-groups-scraper.

Actor choice comes from the source research in testing/problem-intelligence/
facebook/facebook_actor_recommendation.json: keyword-search actors mostly
return marketing, job and life-insurance noise, while this actor -- fed a known
public group URL -- was verified to return real practice-side billing
questions (run lwd1sFYEcsEnAx10X, group 290657479460430). Keyword discovery of
groups through this actor does not work without a login, so the group list is
explicit, and only PUBLIC groups are in scope.

Same collection contract as the other collectors: nothing is filtered on
content -- welcome posts, promos and off-topic posts are stored as-is, and
Step 1 of the analysis pipeline decides relevance. The only records dropped
are ones that cannot be a post at all (actor error rows, no stable id, no
text). Matched RCM keywords are stored in source_metadata as candidate
evidence, exactly like the Reddit collector.
"""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import zip_longest
from typing import Any

from app.analysis.lexicons import RCM_KEYWORDS
from app.collectors.apify_client import run_actor_sync
from app.collectors.common import parse_datetime

ACTOR_ID = "apify/facebook-groups-scraper"

# Public groups only, accepted on the evidence of their actual posts, not their
# names: see backend/data/facebook_sourcing/20260924/report.md. Of 28 groups
# considered, only this one had enough practice-side payer/denial/procedure
# posts (19 of 43 substantive posts in a 150-post sample); billing-named groups
# were mostly jobs, vendor ads and course promotion. medical_claims_tasks,
# usa_medical_billing and nemt_claims_denials_remittances were removed.
DEFAULT_GROUPS = {
    "pmr_interventional_pain_billing": "https://www.facebook.com/groups/290657479460430",
    # Evidence in backend/data/facebook_sourcing/deep_20260924/report.md (4/4
    # substantive posts were payer/denial/billing problems).
    "rural_health_clinics_info_exchange": "https://www.facebook.com/groups/1503414633296362",
    # Added at the user's request. PRIVATE group (82.1K members, Playwright check
    # 24 Sep 2026): the public groups scraper may return no posts for it.
    "medical_billing_coding_forum": "https://www.facebook.com/groups/408036195927123",
}

DEFAULT_LIMIT = 20
DEFAULT_PER_GROUP = 8
# Pay-per-result actor (~$0.005/post): a hard per-run charge ceiling, because
# the actor's own resultsLimit is not a guaranteed cap.
MAX_CHARGE_PER_RUN_USD = 0.10


def _matched_keywords(text: str) -> list[str]:
    if not text:
        return []
    lowered = text.lower()
    return [kw for kw in RCM_KEYWORDS if kw in lowered]


def post_id(post: dict[str, Any]) -> str | None:
    """The numeric post id (legacyId) is what appears in the permalink and is
    stable across runs; the base64 `id` embeds the author and is only a fallback."""
    value = post.get("legacyId") or post.get("postId") or post.get("id")
    return str(value) if value else None


def is_collectable(post: dict[str, Any]) -> bool:
    if post.get("error"):  # actor row for a private/empty group, not a post
        return False
    return bool(post_id(post)) and bool((post.get("text") or "").strip())


def normalize_post(post: dict[str, Any], group_key: str) -> dict[str, Any]:
    user = post.get("user") or {}
    text = post.get("text") or ""
    pid = post_id(post)
    attachments = post.get("attachments") or []

    return {
        "source": "facebook",
        "source_item_id": pid,
        "url": post.get("url"),
        "title": None,
        "text": text,
        "author_id": user.get("id"),
        "author_name": user.get("name"),
        # Never constructed from the id -- only stored when the actor gives one.
        "author_profile_url": user.get("url") or user.get("profileUrl"),
        "author_role": None,
        "organization_name": None,
        "organization_url": None,
        "location": None,
        "created_at": parse_datetime(post.get("time")),
        "collected_at": datetime.now(timezone.utc),
        "engagement": {
            "likes": post.get("likesCount"),
            "comments": post.get("commentsCount"),
            "shares": post.get("sharesCount"),
        },
        "parent_id": None,
        "conversation_id": pid,
        "media_type": "text+attachment" if attachments else "text",
        "raw_data": post,
        "source_metadata": {
            "group_key": group_key,
            "group_id": post.get("facebookId"),
            "group_title": post.get("groupTitle"),
            "group_url": post.get("facebookUrl") or post.get("inputUrl"),
            "matched_rcm_keywords": _matched_keywords(text),
        },
    }


def collect_group(
    group_url: str,
    max_items: int = DEFAULT_PER_GROUP,
    max_charge_usd: float = MAX_CHARGE_PER_RUN_USD,
) -> list[dict[str, Any]]:
    return run_actor_sync(
        ACTOR_ID,
        {
            "startUrls": [{"url": group_url}],
            "resultsLimit": max_items,
            "viewOption": "CHRONOLOGICAL",
        },
        max_items=max_items,
        max_total_charge_usd=max_charge_usd,
        timeout_s=900,
    )


def select_posts(
    raw_by_group: dict[str, list[dict[str, Any]]],
    limit: int = DEFAULT_LIMIT,
    exclude_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Round-robin across groups so one busy group cannot fill the whole
    sample, de-duplicating on post id, and stop at exactly `limit`.

    exclude_ids (post ids already stored) makes a top-up run add only new
    posts instead of re-selecting ones the DB already has."""
    selected: list[dict[str, Any]] = []
    seen: set[str] = set(exclude_ids or ())
    columns = [[(key, p) for p in posts] for key, posts in raw_by_group.items()]
    for row in zip_longest(*columns):
        for entry in row:
            if entry is None:
                continue
            group_key, post = entry
            if not is_collectable(post):
                continue
            pid = post_id(post)
            if pid in seen:
                continue
            seen.add(pid)
            selected.append(normalize_post(post, group_key))
            if len(selected) >= limit:
                return selected
    return selected


def collect(
    groups: dict[str, str] | None = None,
    limit: int = DEFAULT_LIMIT,
    per_group: int = DEFAULT_PER_GROUP,
    exclude_ids: set[str] | None = None,
    max_charge_usd: float = MAX_CHARGE_PER_RUN_USD,
) -> list[dict[str, Any]]:
    groups = groups or DEFAULT_GROUPS
    raw_by_group: dict[str, list[dict[str, Any]]] = {}
    for group_key, group_url in groups.items():
        print(f"[facebook] collecting group '{group_key}' (max {per_group})...")
        items = collect_group(group_url, per_group, max_charge_usd)
        usable = sum(1 for p in items if is_collectable(p))
        print(f"[facebook] {group_key}: {len(items)} returned, {usable} usable posts")
        raw_by_group[group_key] = items

    records = select_posts(raw_by_group, limit, exclude_ids)
    if len(records) < limit:
        print(f"[facebook] WARNING: only {len(records)} usable posts found (wanted {limit}); "
              "not padding the sample.")
    return records
