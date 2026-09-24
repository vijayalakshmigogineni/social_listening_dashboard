"""
X (Twitter) collector -- public posts from validated accounts via Apify's
tweetapi/twitter-x-search-scraper (native X search, no login, ~$0.25/1K posts).

Source choice comes from backend/data/x_sourcing/20260924/report.md: keyword
searches on X are dominated by news, politics, stock chatter and vendor ads,
so collection is per ACCOUNT, and only accounts whose own recent posts showed
recurring practice-side reimbursement/payer problems are listed. Names, bios
and hashtags were not used to accept an account.

One deliberate difference from the other collectors: every account posts far
more off-topic than on-topic content (politics, sport, clinical chatter), so
each account's X query is scoped with PROBLEM_TERMS. That is a source-query
definition, applied identically to every account -- it is not relevance
scoring, and Step 1 of the pipeline still decides relevance independently.
Posts too short to carry a problem statement (MIN_TEXT_CHARS) and retweets are
not collected. Matched RCM keywords go into source_metadata as candidate
evidence, exactly like the Reddit and Facebook collectors.
"""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import zip_longest
from typing import Any

from app.analysis.lexicons import RCM_KEYWORDS
from app.collectors.apify_client import run_actor_sync
from app.collectors.common import parse_datetime

ACTOR_ID = "tweetapi/twitter-x-search-scraper"

# Payer/reimbursement problem vocabulary shared by every account query.
PROBLEM_TERMS = (
    '(denied OR denial OR denials OR denying OR "prior auth" OR "prior authorization" '
    'OR "peer to peer" OR reimbursement OR underpay OR unpaid OR downcode OR downcoding '
    'OR modifier OR IDR OR QPA OR "fee schedule" OR "Medicare Advantage" OR WISeR '
    'OR payment OR paid OR EOB OR "out of network" OR insurer OR insurance)'
)

# Accepted on the evidence of 30 recent posts each (report.md, Phase 2). The
# number is how many of those 30 showed a real reimbursement/payer problem.
DEFAULT_ACCOUNTS = {
    "DrBruggeman": "spine surgeon / practice CEO; IDR, MA prior auth, PFS, WISeR (~20/30)",
    "EdGainesIII": "reimbursement attorney / coding educator; payer + NSA policy (~15/30)",
    "DrAlexUrology": "independent urologist; payer PA, modifier-25, fee cuts (~12/30)",
    "EPotterMD": "independent surgeon; payer denials, out-of-network, CPT (~10/30)",
    "amyfaithho": "EM physician; fee schedule, IDR, payer behaviour (~8/30)",
    "STzorfas": "private-practice neurologist; payment delay, MA code denials (~6/30)",
    "dougbeall": "interventional spine; kyphoplasty/RFA denials, WISeR (5/30, on-target)",
    "josonenine": "ASC/practice owner; facility underpayment, QPA (~4/30)",
    "JahangirAsgha10": "practice owner; PA hold times, payer payment, IDR (earlier posts)",
}

DEFAULT_LIMIT = 20
DEFAULT_PER_ACCOUNT = 15
DEFAULT_SINCE = "2025-09-24"  # rolling 12 months at collection time
MIN_TEXT_CHARS = 100
MAX_CHARGE_PER_RUN_USD = 0.03


def build_query(handle: str, since: str = DEFAULT_SINCE) -> str:
    return f"from:{handle} {PROBLEM_TERMS} since:{since} lang:en -filter:retweets"


def _matched_keywords(text: str) -> list[str]:
    if not text:
        return []
    lowered = text.lower()
    return [kw for kw in RCM_KEYWORDS if kw in lowered]


def is_collectable(post: dict[str, Any]) -> bool:
    if post.get("recordType") not in (None, "tweet") or post.get("retweetedTweetId"):
        return False
    return bool(post.get("id")) and len((post.get("text") or "").strip()) >= MIN_TEXT_CHARS


def normalize_post(post: dict[str, Any], account_key: str | None,
                   search_query: str | None = None) -> dict[str, Any]:
    author = post.get("author") or {}
    text = post.get("text") or ""
    reply_to = post.get("replyTo") or None
    parent_id = None
    if isinstance(reply_to, dict):
        parent_id = reply_to.get("id") or reply_to.get("tweetId")
    elif reply_to:
        parent_id = str(reply_to)
    metrics = post.get("metrics") or {}

    return {
        "source": "x",
        "source_item_id": str(post["id"]),
        "url": post.get("url"),
        "title": None,
        "text": text,
        "author_id": author.get("id"),
        "author_name": author.get("name"),
        "author_profile_url": author.get("url"),
        "author_role": None,
        "organization_name": None,
        "organization_url": None,
        "location": None,
        "created_at": parse_datetime(post.get("createdAt")),
        "collected_at": datetime.now(timezone.utc),
        "engagement": {
            "likes": metrics.get("likes"),
            "replies": metrics.get("replies"),
            "reposts": metrics.get("retweets"),
            "quotes": metrics.get("quotes"),
            "views": metrics.get("views"),
        },
        "parent_id": parent_id,
        "conversation_id": post.get("conversationId"),
        "media_type": "text+media" if post.get("media") else "text",
        "raw_data": post,
        "source_metadata": {
            "account_key": account_key,
            "username": author.get("username"),
            "post_type": post.get("type"),
            "quoted_post_id": post.get("quotedTweetId"),
            "is_reply": bool(reply_to),
            "reply_to_username": reply_to.get("username") if isinstance(reply_to, dict) else None,
            "actor": ACTOR_ID,
            "search_query": search_query,
            "matched_rcm_keywords": _matched_keywords(text),
        },
    }


def collect_account(handle: str, max_items: int = DEFAULT_PER_ACCOUNT,
                    since: str = DEFAULT_SINCE) -> list[dict[str, Any]]:
    query = build_query(handle, since)
    return run_actor_sync(
        ACTOR_ID,
        {"query": query, "mode": "Latest", "maxItems": max_items},
        max_items=max_items,
        max_total_charge_usd=MAX_CHARGE_PER_RUN_USD,
        timeout_s=600,
    )


def select_posts(
    raw_by_account: dict[str, list[dict[str, Any]]],
    limit: int = DEFAULT_LIMIT,
    exclude_ids: set[str] | None = None,
    queries: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Round-robin across accounts (newest first within each, as the actor
    returns them) so no single prolific account fills the sample; dedupe on
    post id; stop at exactly `limit`."""
    selected: list[dict[str, Any]] = []
    seen: set[str] = set(exclude_ids or ())
    columns = [[(key, p) for p in posts] for key, posts in raw_by_account.items()]
    for row in zip_longest(*columns):
        for entry in row:
            if entry is None:
                continue
            key, post = entry
            if not is_collectable(post):
                continue
            pid = str(post["id"])
            if pid in seen:
                continue
            seen.add(pid)
            selected.append(normalize_post(post, key, (queries or {}).get(key)))
            if len(selected) >= limit:
                return selected
    return selected
