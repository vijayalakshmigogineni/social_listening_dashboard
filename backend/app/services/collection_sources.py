"""
Source adapters for dashboard-started collection jobs.

Each adapter drives an EXISTING collector (app/collectors/*) one unit at a
time -- a subreddit, LinkedIn query family, AAPC forum, Facebook group or X
account -- using the same functions the terminal scripts call, so actor
inputs, normalization and cost caps are unchanged. Working per unit is what
lets a job report live progress and keep going when one unit fails.

None of the collectors' actors accept a date range (X's `since:` is the one
exception, and only to day granularity), so every source fetches newest-first
to a per-unit depth and the window/post limit is applied afterwards in
select(). That is why a window reaching further back than the fetch depth
can come back incomplete: fetch_unit reports that as `depth_reached` and the
job surfaces it as a warning.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import zip_longest
from typing import Any

from app.collectors import aapc, facebook, linkedin, reddit, x
from app.collectors.common import parse_datetime
from app.config import APIFY_TOKEN

MAX_POST_LIMIT = 200  # per source, per job -- bounds Apify spend from the UI


@dataclass
class FetchPlan:
    mode: str  # since_last_sweep | custom_range | latest_n
    window_start: datetime | None = None
    window_end: datetime | None = None
    limit: int | None = None  # per source; None = everything in the window


@dataclass
class UnitFetch:
    records: list[dict[str, Any]]
    depth_reached: bool  # the unit returned as many items as were asked for


def post_time(record: dict[str, Any]) -> datetime | None:
    """When the post was made. Reddit's normalizer does not read the
    fatihtahta actor's `created_utc`, so its stored created_at is empty; fall
    back to the raw field here (read-only -- the stored record is unchanged)."""
    value = record.get("created_at")
    if value is None:
        value = parse_datetime((record.get("raw_data") or {}).get("created_utc"))
    if isinstance(value, datetime) and value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


class SourceAdapter:
    key: str
    label: str
    unit_label: str
    sweep_depth: int  # per unit, when the job has no post count (= script default)
    max_depth: int
    needs_apify = True
    # Facebook/X collectors round-robin across units so one busy group or
    # account cannot fill the sample; the others are ranked newest-first.
    round_robin = False
    # Roughly how many posts one unit of depth yields (AAPC: posts per thread).
    posts_per_depth = 1.0
    cost_note = ""

    def units(self) -> dict[str, Any]:
        raise NotImplementedError

    def fetch_unit(self, name: str, arg: Any, depth: int, plan: FetchPlan) -> UnitFetch:
        raise NotImplementedError

    def unavailable_reason(self) -> str | None:
        if self.needs_apify and not APIFY_TOKEN:
            return "APIFY_TOKEN is not set in the backend .env"
        return None

    def depth_for(self, plan: FetchPlan) -> int:
        if plan.limit is None:
            return self.sweep_depth
        per_unit = math.ceil(plan.limit / (len(self.units()) * self.posts_per_depth))
        if plan.mode == "custom_range":
            # The window filter discards posts, so fetch at least a sweep's worth.
            per_unit = max(per_unit, self.sweep_depth)
        return max(1, min(per_unit, self.max_depth))

    def select(self, by_unit: dict[str, list[dict[str, Any]]], plan: FetchPlan) -> list[dict[str, Any]]:
        if self.round_robin:
            ordered = [r for row in zip_longest(*by_unit.values()) for r in row if r is not None]
        else:
            ordered = sorted(
                (r for records in by_unit.values() for r in records),
                key=lambda r: post_time(r) or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )

        selected: list[dict[str, Any]] = []
        seen: set[str] = set()
        for record in ordered:
            sid = record["source_item_id"]
            if sid in seen:  # same post via two units (e.g. two LinkedIn families)
                continue
            if plan.window_start or plan.window_end:
                when = post_time(record)
                if when is None:
                    continue
                if plan.window_start and when < plan.window_start:
                    continue
                if plan.window_end and when > plan.window_end:
                    continue
            seen.add(sid)
            selected.append(record)
            if plan.limit is not None and len(selected) >= plan.limit:
                break
        return selected

    def describe(self) -> dict[str, Any]:
        reason = self.unavailable_reason()
        return {
            "key": self.key,
            "label": self.label,
            "available": reason is None,
            "unavailable_reason": reason,
            "unit_label": self.unit_label,
            "units": list(self.units()),
            "sweep_depth_per_unit": self.sweep_depth,
            "cost_note": self.cost_note,
        }


class RedditAdapter(SourceAdapter):
    key, label, unit_label = "reddit", "Reddit", "subreddit"
    sweep_depth, max_depth = 30, 100
    cost_note = "Apify credits per post fetched"

    def units(self):
        return {f"r/{s}": s for s in reddit.DEFAULT_SUBREDDITS}

    def fetch_unit(self, name, arg, depth, plan):
        records = reddit.collect_subreddit(arg, depth)
        return UnitFetch(records, len(records) >= depth)


class LinkedInAdapter(SourceAdapter):
    key, label, unit_label = "linkedin", "LinkedIn", "query family"
    sweep_depth, max_depth = 10, 50
    cost_note = "Apify credits per post fetched"

    def units(self):
        return dict(linkedin.QUERY_FAMILIES)

    def fetch_unit(self, name, arg, depth, plan):
        records = linkedin.collect(query=arg, limit=depth)
        return UnitFetch(records, len(records) >= depth)


class AapcAdapter(SourceAdapter):
    key, label, unit_label = "aapc", "AAPC", "forum"
    sweep_depth, max_depth = 5, 20  # threads per forum
    needs_apify = False
    posts_per_depth = 3.0
    cost_note = "Free (public forum pages); ~1.5 s per thread"

    def units(self):
        return dict(aapc.DEFAULT_FORUMS)

    def fetch_unit(self, name, arg, depth, plan):
        records = aapc.collect(forums={name: arg}, max_threads_per_forum=depth)
        threads = {r["conversation_id"] for r in records}
        return UnitFetch(records, len(threads) >= depth)


class FacebookAdapter(SourceAdapter):
    key, label, unit_label = "facebook", "Facebook", "group"
    sweep_depth, max_depth = facebook.DEFAULT_PER_GROUP, 30
    round_robin = True
    posts_per_depth = 0.7  # some returned rows are not usable posts
    cost_note = f"~$0.005 per post, capped at ${facebook.MAX_CHARGE_PER_RUN_USD:.2f} per group run"

    def units(self):
        return dict(facebook.DEFAULT_GROUPS)

    def fetch_unit(self, name, arg, depth, plan):
        raw = facebook.collect_group(arg, depth)
        records = facebook.select_posts({name: raw}, limit=len(raw))
        return UnitFetch(records, len(raw) >= depth)


class XAdapter(SourceAdapter):
    key, label, unit_label = "x", "X", "account"
    sweep_depth, max_depth = x.DEFAULT_PER_ACCOUNT, 50
    round_robin = True
    posts_per_depth = 0.7  # short posts and retweets are not collected
    cost_note = f"~$0.25 per 1K posts, capped at ${x.MAX_CHARGE_PER_RUN_USD:.2f} per account run"

    def units(self):
        return {f"@{h}": h for h in x.DEFAULT_ACCOUNTS}

    def fetch_unit(self, name, arg, depth, plan):
        # X search is the one source that can narrow by date server-side.
        since = plan.window_start.strftime("%Y-%m-%d") if plan.window_start else x.DEFAULT_SINCE
        raw = x.collect_account(arg, depth, since=since)
        records = x.select_posts({name: raw}, limit=len(raw), queries={name: x.build_query(arg, since)})
        return UnitFetch(records, len(raw) >= depth)


ADAPTERS: dict[str, SourceAdapter] = {
    a.key: a
    for a in (AapcAdapter(), RedditAdapter(), LinkedInAdapter(), FacebookAdapter(), XAdapter())
}
