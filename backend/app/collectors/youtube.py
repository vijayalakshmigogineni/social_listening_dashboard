"""
YouTube collector -- video discovery + comment collection via Apify.

The primary SLD signal on YouTube is the comment section, not the video:
the video is context, each comment is the evidence. So one normalized
record = one comment (or reply). Videos are never stored as their own
normalized_items rows (that would make them analysis/scoring candidates);
their details ride along on every comment in source_metadata.

Two actors, both pay-per-result:
  streamers/youtube-scraper           -- search discovery (~$0.004/video)
  streamers/youtube-comments-scraper  -- comments per video (~$0.002/comment)
Comment volume dominates cost, so --max-comments-per-video is the main
cost lever.

Discovery runs one actor call per query family (each result carries the
query that found it in `input`), so a failed family doesn't sink the run.
Videos found by several queries are merged before any comments are fetched.
Comments are then fetched in chunks of videos, again so one failure only
loses that chunk.

As with the other collectors, collection stores everything; Step 1 of the
analysis pipeline decides relevance. matched_rcm_keywords is computed from
the comment text only (as reddit.py does for post bodies), so a comment is
not credited with keywords that only appear in its video's title.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from app.analysis.lexicons import RCM_KEYWORDS
from app.collectors.apify_client import ApifyRunError, run_actor_sync

SEARCH_ACTOR_ID = "streamers/youtube-scraper"
COMMENTS_ACTOR_ID = "streamers/youtube-comments-scraper"

# Generic RCM discovery themes, not pain-management-specific (same stance as
# the Reddit/LinkedIn collectors). Payer names are always paired with an RCM
# term -- a bare "Aetna" or "Humana" search returns mostly consumer, stock
# and careers videos.
QUERY_FAMILIES: dict[str, list[str]] = {
    "medical_billing": [
        "medical billing problems",
        "medical billing challenges",
        "physician billing",
        "medical coding",
        "revenue cycle management healthcare",
    ],
    "claims_denials": [
        "medical claim denial",
        "denial management medical billing",
        "insurance reimbursement underpayment",
        "accounts receivable healthcare A/R",
    ],
    "prior_authorization": [
        "prior authorization",
        "prior auth problems",
        "authorization denial",
        "utilization management",
    ],
    "payers": [
        "UnitedHealthcare claim denial",
        "Aetna prior authorization",
        "Cigna claim denial",
        "Humana prior authorization",
        "Medicare billing",
        "Medicaid billing",
        "Blue Cross Blue Shield claim denial",
    ],
    "practice_operations": [
        "private practice problems",
        "medical practice management",
        "medical billing department",
        "practice revenue",
        "medical office problems",
    ],
}

DEFAULT_MAX_VIDEOS_PER_QUERY = 5
DEFAULT_MAX_COMMENTS_PER_VIDEO = 50
DEFAULT_MAX_VIDEOS_TOTAL = 60
VIDEOS_PER_COMMENT_RUN = 20
ACTOR_TIMEOUT_S = 1800.0

VIDEO_DATE_FILTERS = {"hour", "today", "week", "month", "year"}

DESCRIPTION_MAX_CHARS = 1000

_RELATIVE_UNITS_DAYS = {
    "second": 1 / 86400,
    "minute": 1 / 1440,
    "hour": 1 / 24,
    "day": 1,
    "week": 7,
    "month": 30,
    "year": 365,
}
_RELATIVE_RE = re.compile(r"(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago")


def parse_relative_time(text: str | None, now: datetime) -> datetime | None:
    """'3 weeks ago' -> approximate datetime. The comments actor only exposes
    YouTube's relative 'publishedTimeText', never an absolute timestamp."""
    if not text:
        return None
    m = _RELATIVE_RE.search(text.lower())
    if not m:
        return None
    return now - timedelta(days=int(m.group(1)) * _RELATIVE_UNITS_DAYS[m.group(2)])


def _matched_keywords(text: str) -> list[str]:
    if not text:
        return []
    lowered = text.lower()
    return [kw for kw in RCM_KEYWORDS if kw in lowered]


def _profile_url(author: str | None) -> str | None:
    if author and author.startswith("@"):
        return f"https://www.youtube.com/{author}"
    return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _video_context(video: dict[str, Any]) -> dict[str, Any]:
    """The subset of a discovered video kept on each of its comments."""
    return {
        "video_id": video.get("id"),
        "video_url": video.get("url"),
        "video_title": video.get("title"),
        "video_published_at": video.get("date"),
        "video_description": (video.get("text") or "")[:DESCRIPTION_MAX_CHARS] or None,
        "channel_id": video.get("channelId"),
        "channel_name": video.get("channelName"),
        "channel_url": video.get("channelUrl"),
        "video_stats": {
            "views": _int_or_none(video.get("viewCount")),
            "likes": _int_or_none(video.get("likes")),
            "comments": _int_or_none(video.get("commentsCount")),
        },
        "discovery_queries": list(video.get("_queries", [])),
        "query_families": list(video.get("_families", [])),
    }


def normalize_comment(
    comment: dict[str, Any], video: dict[str, Any], collected_at: datetime | None = None
) -> dict[str, Any]:
    collected_at = collected_at or datetime.now(timezone.utc)
    cid = comment.get("cid")
    video_id = comment.get("videoId") or video.get("id")
    parent_cid = comment.get("replyToCid")
    text = comment.get("comment") or ""
    author = comment.get("author")

    return {
        "source": "youtube",
        "source_item_id": cid,
        "url": f"https://www.youtube.com/watch?v={video_id}&lc={cid}",
        # Video title as the record title, text = the comment itself.
        "title": video.get("title") or comment.get("title"),
        "text": text,
        "author_id": author,
        "author_name": author,
        "author_profile_url": _profile_url(author),
        "author_role": None,
        "organization_name": None,
        "organization_url": None,
        "location": None,
        "created_at": parse_relative_time(comment.get("publishedTimeText"), collected_at),
        "collected_at": collected_at,
        "engagement": {
            "likes": _int_or_none(comment.get("voteCount")),
            "replies": _int_or_none(comment.get("replyCount")),
            "creator_heart": comment.get("hasCreatorHeart"),
        },
        "parent_id": parent_cid,
        "conversation_id": video_id,
        "media_type": "comment",
        "raw_data": comment,
        "source_metadata": {
            **_video_context(video),
            "comment_id": cid,
            "parent_comment_id": parent_cid,
            "is_reply": parent_cid is not None,
            "author_is_channel_owner": comment.get("authorIsChannelOwner"),
            "published_time_text": comment.get("publishedTimeText"),
            "created_at_is_approximate": True,
            "matched_rcm_keywords": _matched_keywords(text),
        },
    }


def discover_videos(
    query_families: dict[str, list[str]],
    max_videos_per_query: int = DEFAULT_MAX_VIDEOS_PER_QUERY,
    video_date_filter: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Search each family; return videos keyed by video_id, with every query
    and family that found them merged onto the one entry."""
    videos: dict[str, dict[str, Any]] = {}
    query_to_family = {q: f for f, qs in query_families.items() for q in qs}

    for family, queries in query_families.items():
        run_input: dict[str, Any] = {
            "searchQueries": queries,
            "maxResults": max_videos_per_query,
            "maxResultsShorts": 0,
            "maxResultStreams": 0,
            "sortingOrder": "relevance",
        }
        if video_date_filter:
            run_input["dateFilter"] = video_date_filter

        print(f"[youtube] discovering family '{family}' ({len(queries)} queries)...")
        try:
            results = run_actor_sync(SEARCH_ACTOR_ID, run_input, timeout_s=ACTOR_TIMEOUT_S)
        except (ApifyRunError, OSError) as exc:
            print(f"  ! discovery failed for family '{family}': {exc}")
            continue

        found = 0
        for video in results:
            video_id = video.get("id")
            if not video_id or video.get("type") not in (None, "video"):
                continue
            query = video.get("input")
            entry = videos.setdefault(video_id, {**video, "_queries": [], "_families": []})
            if query and query not in entry["_queries"]:
                entry["_queries"].append(query)
            fam = query_to_family.get(query, family)
            if fam not in entry["_families"]:
                entry["_families"].append(fam)
            found += 1
        print(f"[youtube] {family}: {found} results, {len(videos)} unique videos so far")

    return videos


def _has_comments(video: dict[str, Any]) -> bool:
    if video.get("commentsTurnedOff"):
        return False
    count = _int_or_none(video.get("commentsCount"))
    return count is None or count > 0


def collect_comments(
    videos: dict[str, dict[str, Any]],
    max_comments_per_video: int = DEFAULT_MAX_COMMENTS_PER_VIDEO,
    comment_days: int | None = None,
) -> list[dict[str, Any]]:
    video_ids = list(videos)
    records: dict[str, dict[str, Any]] = {}
    skipped = 0

    for start in range(0, len(video_ids), VIDEOS_PER_COMMENT_RUN):
        chunk = video_ids[start:start + VIDEOS_PER_COMMENT_RUN]
        run_input: dict[str, Any] = {
            "startUrls": [{"url": videos[v]["url"]} for v in chunk],
            "maxComments": max_comments_per_video,
            "sortCommentsBy": "NEWEST_FIRST",
        }
        if comment_days:
            run_input["oldestCommentDate"] = f"{comment_days} days"

        print(f"[youtube] fetching comments for videos {start + 1}-{start + len(chunk)} of {len(video_ids)}...")
        try:
            comments = run_actor_sync(COMMENTS_ACTOR_ID, run_input, timeout_s=ACTOR_TIMEOUT_S)
        except (ApifyRunError, OSError) as exc:
            print(f"  ! comment fetch failed for this chunk: {exc}")
            continue

        collected_at = datetime.now(timezone.utc)
        for comment in comments:
            cid = comment.get("cid")
            video = videos.get(comment.get("videoId"))
            if not cid or video is None or not (comment.get("comment") or "").strip():
                skipped += 1
                continue
            records[cid] = normalize_comment(comment, video, collected_at)

    if skipped:
        print(f"[youtube] skipped {skipped} comments (deleted/empty/unknown video)")
    return list(records.values())


def collect_families(
    query_families: dict[str, list[str]] | None = None,
    max_videos_per_query: int = DEFAULT_MAX_VIDEOS_PER_QUERY,
    max_videos_total: int = DEFAULT_MAX_VIDEOS_TOTAL,
    max_comments_per_video: int = DEFAULT_MAX_COMMENTS_PER_VIDEO,
    video_date_filter: str | None = None,
    comment_days: int | None = None,
) -> list[dict[str, Any]]:
    if video_date_filter and video_date_filter not in VIDEO_DATE_FILTERS:
        raise ValueError(f"video_date_filter must be one of {sorted(VIDEO_DATE_FILTERS)}")

    query_families = query_families or QUERY_FAMILIES
    videos = discover_videos(query_families, max_videos_per_query, video_date_filter)

    with_comments = {vid: v for vid, v in videos.items() if _has_comments(v)}
    print(
        f"[youtube] {len(videos)} unique videos, {len(videos) - len(with_comments)} "
        f"with comments off or none"
    )
    if len(with_comments) > max_videos_total:
        print(f"[youtube] capping at {max_videos_total} videos (--max-videos-total)")
        with_comments = dict(list(with_comments.items())[:max_videos_total])

    return collect_comments(with_comments, max_comments_per_video, comment_days)
