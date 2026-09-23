"""
AAPC collector -- public discussion forum RSS + thread-page scraping.

Ports the pattern proven in testing/problem-intelligence/aapc/aapc_rss_fetch.py
(RSS listing) and parse_aapc.py (XenForo thread HTML -> per-post fields) onto
the canonical schema. Forums chosen are generic RCM topics (billing,
payer/health-plan, coding modifiers), not specialty-specific.

Per testing/SLD-ROADMAP.md Part 3 Test 4, AAPC's discussion forums are
publicly readable/search-indexed with no official API -- this collector
fetches public pages with a standard User-Agent, at a conservative rate
(a short delay between thread fetches), matching what was already
validated as accessible in the existing research code.
"""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from app.collectors.common import parse_datetime

HEADERS = {"User-Agent": "Mozilla/5.0"}
BASE_URL = "https://www.aapc.com"

DEFAULT_FORUMS = {
    "billing_reimbursement": "https://www.aapc.com/discuss/forums/billing-reimbursement.583/index.rss",
    "payer_health_plan": "https://www.aapc.com/discuss/forums/payer-health-plan.661/index.rss",
    "modifiers": "https://www.aapc.com/discuss/forums/modifiers.483/index.rss",
    # RSS-accessibility-validated in testing/problem-intelligence/aapc/
    # (aapc_pagination_report.json) but not yet collected in production.
    "anesthesia": "https://www.aapc.com/discuss/forums/anesthesia.440/index.rss",
    "interventional_radiology": "https://www.aapc.com/discuss/forums/interventional-radiology.480/index.rss",
    "medicare_regulations": "https://www.aapc.com/discuss/forums/medicare-regulations.479/index.rss",
    "orthopaedics": "https://www.aapc.com/discuss/forums/orthopaedics.427/index.rss",
    "general_discussion": "https://www.aapc.com/discuss/forums/general-discussion.582/index.rss",
}

REQUEST_DELAY_S = 1.5


def fetch_forum_threads(rss_url: str) -> list[dict[str, Any]]:
    response = requests.get(rss_url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    items = root.find("channel").findall("item")

    threads = []
    for item in items:
        threads.append(
            {
                "title": item.findtext("title"),
                "url": item.findtext("link"),
                "guid": item.findtext("guid"),
                "pub_date": item.findtext("pubDate"),
            }
        )
    return threads


def _text_of(el) -> str | None:
    return el.get_text(" ", strip=True) if el else None


def parse_thread_posts(thread_url: str, forum: str) -> list[dict[str, Any]]:
    response = requests.get(thread_url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    thread_title = _text_of(soup.select_one("h1"))
    thread_id = thread_url.rstrip("/").split(".")[-1].split("/")[0]

    posts = []
    for post_el in soup.select("article.message.message--post"):
        raw_post_id = post_el.get("data-content")
        post_id = raw_post_id.replace("post-", "") if raw_post_id else None

        author_el = post_el.select_one(".message-name .username")
        author_name = _text_of(author_el)
        author_id = author_el.get("data-user-id") if author_el else None
        author_profile_url = (
            urljoin(BASE_URL, author_el["href"]) if author_el and author_el.get("href") else None
        )

        role_el = post_el.select_one(".message-userTitle")
        author_role = _text_of(role_el)

        location_el = post_el.select_one(".message-userExtras a[href*='location-info']")
        location = _text_of(location_el)

        time_el = post_el.select_one("time.u-dt")
        created_at_raw = time_el.get("datetime") if time_el else None

        message_el = post_el.select_one(".message-body .bbWrapper")
        text = message_el.get_text("\n", strip=True) if message_el else None

        post_url = f"{thread_url.rstrip('/')}/post-{post_id}" if post_id else thread_url

        posts.append(
            {
                "thread_id": thread_id,
                "thread_title": thread_title,
                "thread_url": thread_url,
                "forum": forum,
                "post_id": post_id or f"{thread_id}-0",
                "post_url": post_url,
                "author_name": author_name,
                "author_id": author_id,
                "author_profile_url": author_profile_url,
                "author_role": author_role,
                "location": location,
                "created_at_raw": created_at_raw,
                "text": text,
            }
        )

    return posts


def normalize_post(raw_post: dict[str, Any]) -> dict[str, Any]:
    thread_id = raw_post["thread_id"]
    post_id = raw_post["post_id"]
    is_first_post = post_id == raw_post.get("_first_post_id")

    return {
        "source": "aapc",
        "source_item_id": f"{thread_id}:{post_id}",
        "url": raw_post["post_url"],
        "title": raw_post["thread_title"] if is_first_post else None,
        "text": raw_post["text"],
        "author_id": raw_post["author_id"],
        "author_name": raw_post["author_name"],
        "author_profile_url": raw_post["author_profile_url"],
        "author_role": raw_post["author_role"],
        "organization_name": None,
        "organization_url": None,
        "location": raw_post["location"],
        "created_at": parse_datetime(raw_post["created_at_raw"]),
        "collected_at": datetime.now(timezone.utc),
        "engagement": None,
        "parent_id": None if is_first_post else f"{thread_id}:{raw_post.get('_first_post_id')}",
        "conversation_id": thread_id,
        "media_type": "text",
        "raw_data": raw_post,
        "source_metadata": {"forum": raw_post["forum"], "thread_url": raw_post["thread_url"]},
    }


def collect(forums: dict[str, str] | None = None, max_threads_per_forum: int = 15) -> list[dict[str, Any]]:
    forums = forums or DEFAULT_FORUMS
    all_records: list[dict[str, Any]] = []

    for forum_name, rss_url in forums.items():
        print(f"[aapc] fetching thread list for forum '{forum_name}'...")
        threads = fetch_forum_threads(rss_url)[:max_threads_per_forum]
        print(f"[aapc] {forum_name}: {len(threads)} threads")

        for thread in threads:
            try:
                raw_posts = parse_thread_posts(thread["url"], forum_name)
            except requests.RequestException as exc:
                print(f"  ! failed to fetch thread {thread['url']}: {exc}")
                continue

            if not raw_posts:
                continue

            first_post_id = raw_posts[0]["post_id"]
            for post in raw_posts:
                post["_first_post_id"] = first_post_id
                all_records.append(normalize_post(post))

            time.sleep(REQUEST_DELAY_S)

    return all_records
