"""Step 5 - one consolidated record of exactly what this source yields.

Reads the three step reports already on disk, then takes a small fresh sample
(3 RCM boards, 2 threads each, first 2 posts of each) so the report carries
real records rather than only claims about them.

Deliberately small: this is a feasibility probe, not a collection run.

Nothing here is classified. Recency is measured because "is this source still
alive" is a feasibility question, but no post is labelled or scored.
"""

import json
import os
import re
import time
from collections import Counter

from mbl_common import (
    FORUM, BOARDS, fetch, clean_url, squash, board_url, topic_url
)
from mbl_category_pagination_test import parse_listing, parse_pagination
from mbl_thread_post_test import parse_posts, parse_category

from bs4 import BeautifulSoup

OUTPUT_FILE = "mbl_sample_report.json"

SAMPLE_BOARD_IDS = [7, 8, 2]      # Billing, Coding, Insurance Payments
THREADS_PER_BOARD = 2
POSTS_PER_THREAD = 2

# Every field the brief asked about, mapped to where it comes from.
REQUESTED_FIELDS = [
    ("thread_title", "board listing + thread page"),
    ("thread_url", "board listing"),
    ("post_url_or_id", "thread page"),
    ("author_name", "board listing + thread page"),
    ("author_profile_url", "thread page (registered posters only)"),
    ("date_time", "board listing (last post) + thread page (per post)"),
    ("post_text", "thread page"),
    ("category", "board listing + thread breadcrumb"),
    ("reply_count", "board listing"),
    ("location", "not rendered by this install"),
]


def load(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def year_of(date_string):
    match = re.search(r",\s*(\d{4}),", date_string or "")
    if match:
        return int(match.group(1))
    match = re.search(r"(\d{4})", date_string or "")
    return int(match.group(1)) if match else None


def board_recency():
    """Last-post year for page 1 of every RCM board.

    Page 1 is sorted by last activity, so this says how live each board is
    without touching the archive.
    """

    rows = []

    for board in [b for b in BOARDS if b["rcm"]]:

        status, text = fetch(board_url(board["id"], 0))

        if status != 200:
            rows.append({
                "board_id": board["id"],
                "board_name": board["name"],
                "status": status,
                "error": "fetch failed",
            })
            continue

        listing = parse_listing(text)
        pagination = parse_pagination(text)

        years = [
            year_of(r["last_post_date"]) for r in listing
            if r["last_post_date"]
        ]
        years = [y for y in years if y]

        rows.append({
            "board_id": board["id"],
            "board_name": board["name"],
            "status": status,
            "topics_on_page1": len(listing),
            "last_page": pagination["last_page_number"],
            "topics_estimated": (
                pagination["last_page_number"] * pagination["items_per_page"]
                if pagination["last_page_number"] else None
            ),
            "newest_activity_year": max(years) if years else None,
            "page1_year_spread": dict(sorted(Counter(years).items(), reverse=True)),
        })

        print("  board", str(board["id"]).ljust(3),
              board["name"][:30].ljust(32),
              "pages=" + str(rows[-1]["last_page"]).ljust(5),
              "newest=" + str(rows[-1]["newest_activity_year"]))

        time.sleep(1.0)

    return rows


def sample_records():
    """A handful of real thread+post records, exactly as the source gives them."""

    samples = []

    for board_id in SAMPLE_BOARD_IDS:

        board = next(b for b in BOARDS if b["id"] == board_id)

        status, text = fetch(board_url(board_id, 0))

        if status != 200:
            continue

        listing = parse_listing(text)

        # Prefer threads that actually have replies - a discussion, not a
        # drive-by post - but do not filter on anything about the content.
        with_replies = [r for r in listing if (r["reply_count"] or 0) > 0]
        chosen = (with_replies or listing)[:THREADS_PER_BOARD]

        for row in chosen:

            time.sleep(1.0)

            t_status, t_text = fetch(topic_url(row["thread_id"], 0))

            if t_status != 200:
                continue

            soup = BeautifulSoup(t_text, "html.parser")
            category, breadcrumb = parse_category(soup)
            posts = parse_posts(t_text, row["thread_id"], category)

            samples.append({
                # --- from the board listing ---
                "thread_title": row["thread_title"],
                "thread_url": row["thread_url"],
                "category": category or board["name"],
                "reply_count": row["reply_count"],
                "view_count": row["view_count"],
                "thread_author_name": row["author_name"],
                "thread_author_profile_url": row["author_profile_url"],
                "last_post_date": row["last_post_date"],
                # --- from the thread page ---
                "breadcrumb": breadcrumb,
                "posts_on_page1": len(posts),
                "posts": [
                    {
                        "post_id": p["post_id"],
                        "post_url": p["post_url"],
                        "author_name": p["author_name"],
                        "author_type": p["author_type"],
                        "author_profile_url": p["author_profile_url"],
                        "date": p["date"],
                        "location": p["location"],
                        "post_text": p["post_text"],
                    }
                    for p in posts[:POSTS_PER_THREAD]
                ],
            })

            print("  sampled:", str(row["thread_title"])[:52].ljust(54),
                  "posts=" + str(len(posts)))

    return samples


def permalink_check(samples):
    """Does a single post's permalink resolve on its own?

    Posts are readable inside a thread page, but "individual posts are
    publicly accessible" only holds if the msg-level URL works standalone.
    SMF redirects it to the page holding that post, so the test is whether
    the target post is present in the response.
    """

    checks = []

    for entry in samples[:3]:

        for post in entry["posts"][:1]:

            if not post["post_url"]:
                continue

            status, text = fetch(post["post_url"])

            present = bool(post["post_id"]) and (
                'id="msg_' + post["post_id"] + '"' in text
            )

            checks.append({
                "post_url": post["post_url"],
                "post_id": post["post_id"],
                "status": status,
                "post_present_in_response": present,
                "resolves_standalone": status == 200 and present,
            })

            print("  ", str(status), "post", post["post_id"],
                  "present=" + str(present))

            time.sleep(1.0)

    return checks


def main():

    print("=" * 70)
    print("MEDICAL BILLING LIVE - STEP 5: CONSOLIDATED SAMPLE REPORT")
    print("=" * 70)

    access = load("mbl_access_report.json")
    category = load("mbl_category_report.json")
    thread = load("mbl_thread_report.json")
    feed = load("mbl_feed_report.json")

    missing = [
        name for name, data in [
            ("mbl_access_report.json", access),
            ("mbl_category_report.json", category),
            ("mbl_thread_report.json", thread),
            ("mbl_feed_report.json", feed),
        ] if data is None
    ]

    if missing:
        print("Missing step reports:", ", ".join(missing))
        print("Run steps 1-4 first.")
        return

    print("\n[recency across RCM boards]")
    recency = board_recency()

    print("\n[fresh sample]")
    samples = sample_records()

    print("\n[post permalink resolution]")
    permalinks = permalink_check(samples)

    # Field availability, decided by measurement rather than assumption.
    post_pool = [p for t in thread["threads"] for p in t.get("posts", [])]
    registered = [p for p in post_pool if p["author_type"] == "registered"]

    def covered(field, pool):
        return sum(1 for p in pool if p.get(field) not in (None, "", []))

    field_availability = {
        "thread_title": {
            "available": True, "coverage": "all threads",
            "source": "board listing td.subject anchor + thread <title>",
        },
        "thread_url": {
            "available": True, "coverage": "all threads",
            "source": "board listing anchor href",
            "note": "strip the rotating PHPSESSID to get a stable identifier",
        },
        "post_url_and_id": {
            "available": True,
            "coverage": str(covered("post_id", post_pool)) + "/" + str(len(post_pool)) + " posts",
            "source": "thread page h5 anchor (topic,<id>.msg<msgid>.html)",
        },
        "author_name": {
            "available": True,
            "coverage": str(covered("author_name", post_pool)) + "/" + str(len(post_pool)) + " posts",
            "source": "poster column h4",
        },
        "author_profile_url": {
            "available": True,
            "coverage": (
                str(covered("author_profile_url", registered)) + "/" +
                str(len(registered)) + " registered posts; "
                "guests have no profile by definition"
            ),
            "source": "poster column h4 anchor (action=profile;u=<id>)",
        },
        "date_time": {
            "available": True,
            "coverage": str(covered("date", post_pool)) + "/" + str(len(post_pool)) + " posts",
            "source": "thread page .keyinfo .smalltext",
            "format": "Month DD, YYYY, HH:MM:SS AM/PM (forum local time)",
        },
        "post_text": {
            "available": True,
            "coverage": str(covered("post_text", post_pool)) + "/" + str(len(post_pool)) + " posts",
            "source": "thread page .post .inner",
            "note": "full body, not truncated (unlike the feed)",
        },
        "category": {
            "available": True, "coverage": "all threads",
            "source": "board listing context + thread breadcrumb board link",
        },
        "reply_count": {
            "available": True, "coverage": "all threads",
            "source": "board listing td.stats ('N Replies', 'N Views')",
        },
        "location": {
            "available": False,
            "coverage": "0/" + str(len(post_pool)) + " posts",
            "source": None,
            "note": (
                "this install renders only membergroup, postgroup and "
                "postcount in the poster column; no location field is shown"
            ),
        },
    }

    live_boards = [
        r for r in recency if (r.get("newest_activity_year") or 0) >= 2025
    ]

    # A board page sorts by *last* post, so a 2026 timestamp can sit on a
    # thread opened years earlier. Comparing the two dates on the sampled
    # threads shows which is happening here, without judging any content.
    age_gaps = []

    for entry in samples:

        opened = year_of(entry["posts"][0]["date"]) if entry["posts"] else None
        touched = year_of(entry["last_post_date"])

        if opened and touched:
            age_gaps.append({
                "thread_title": entry["thread_title"],
                "opened": opened,
                "last_post": touched,
                "gap_years": touched - opened,
            })

    revived = [g for g in age_gaps if g["gap_years"] >= 5]

    report = {
        "source": "Medical Billing Live",
        "entry_point": FORUM,
        "investigated": "2026-09-21",
        "scope": "data-collection feasibility only; no classification, no collector",
        "platform": {
            "software": access["index"]["software"],
            "url_scheme": {
                "board": "/members/index.php/board,<board_id>.<offset>.html",
                "thread": "/members/index.php/topic,<topic_id>.<offset>.html",
                "post": "/members/index.php/topic,<topic_id>.msg<msg_id>.html#msg<msg_id>",
                "profile": "/members/index.php?action=profile;u=<user_id>",
            },
            "encoding": "declares ISO-8859-1, actually serves cp1252",
            "session_ids": "guest URLs carry a rotating PHPSESSID; strip before storing",
            "reliability": "intermittent 503 under sequential access; retry clears it",
        },

        "access": {
            "login_required": False,
            "boards_total": access["summary"]["boards_total"],
            "boards_public": access["summary"]["boards_public"],
            "robots_disallows_forum": access["robots"]["forum_path_disallowed"],
            "robots_rules": access["robots"]["disallow_rules"],
            "forum_totals": access["index"]["forum_totals"],
        },

        "categories": {
            "all": [
                {"board_id": b["id"], "name": b["name"], "rcm_relevant": b["rcm"]}
                for b in BOARDS
            ],
            "rcm_relevant": [b["name"] for b in BOARDS if b["rcm"]],
            "recency": recency,
        },

        "pagination": {
            "exists": category["pagination_verdict"]["pagination_exists"],
            "tested_on": category["category"],
            "scheme": "item offset in the URL, 20 topics per board page",
            "last_page_tested": category["pagination_verdict"]["last_page_number"],
            "pages_distinct": category["pagination_verdict"]["pages_are_distinct"],
            "archive_reachable": True,
            "oldest_seen": next(
                (p["oldest_last_post"] for p in category["pages"]
                 if "last" in p["label"]), None
            ),
            "in_thread_pagination": "15 posts per thread page",
        },

        "post_level_access": {
            "individual_posts_public": True,
            "each_post_has_stable_permalink": (
                all(c["resolves_standalone"] for c in permalinks)
                if permalinks else None
            ),
            "verified_on_threads": [t["topic_id"] for t in thread["threads"]],
            "posts_examined": len(post_pool),
            "permalink_checks": permalinks,
            "permalinks_resolve_standalone": (
                all(c["resolves_standalone"] for c in permalinks)
                if permalinks else None
            ),
        },

        "field_availability": field_availability,
        "requested_field_map": [
            {"field": f, "obtained_from": src} for f, src in REQUESTED_FIELDS
        ],

        "feed_api": {
            "feed_exists": feed["verdict"]["feed_exists"],
            "endpoint": FORUM + "?action=.xml&type=rss|rss2|atom",
            "board_scoping": feed["verdict"]["board_scoping_supported"],
            "max_items": feed["verdict"]["max_items_returned"],
            "bodies_truncated": feed["verdict"]["bodies_truncated"],
            "author_only_in": feed["verdict"].get("formats_carrying_author"),
            "real_forum_api": feed["verdict"]["real_api_found"],
            "api_note": feed["verdict"]["api_note"],
            "usable_as_sole_collector": False,
            "reason": feed["verdict"]["reason"],
        },

        "observations": {
            "archive_depth": (
                "Billing alone pages back to March 2008 across 97 pages; the "
                "full board index reports "
                + str(access["index"]["forum_totals"]["posts"]) + " posts in "
                + str(access["index"]["forum_totals"]["topics"]) + " topics."
            ),
            "recency": (
                str(len(live_boards)) + " of "
                + str(len([b for b in BOARDS if b['rcm']]))
                + " RCM boards carry a 2025-or-later timestamp on page 1. "
                "That measures last activity, not new discussion: of the "
                + str(len(age_gaps)) + " sampled threads, "
                + str(len(revived)) + " were opened five or more years "
                "before their most recent reply."
            ),
            "thread_age_gaps": age_gaps,
            "content_quality_flag": (
                "Page 1 of several boards carries off-topic link-spam threads "
                "(casino and sports posts) alongside genuine RCM questions, "
                "and some appear as replies inside real threads. Flagged as an "
                "observation for your review - nothing here is classified or "
                "filtered."
            ),
            "guest_posts": (
                "A meaningful share of posts are authored by guests, which "
                "display a name but have no profile URL and no stable author id."
            ),
        },

        "sample_records": samples,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    print("\n" + "-" * 70)
    print("SUMMARY")
    print("-" * 70)
    print("Login required          :", report["access"]["login_required"])
    print("Public boards           :",
          report["access"]["boards_public"], "/", report["access"]["boards_total"])
    print("RCM boards              :", len(report["categories"]["rcm_relevant"]))
    print("Pagination              :", report["pagination"]["exists"],
          "- up to page", report["pagination"]["last_page_tested"],
          "reaching", report["pagination"]["oldest_seen"])
    print("Individual posts public :", report["post_level_access"]["individual_posts_public"])
    print("Feed exists             :", report["feed_api"]["feed_exists"],
          "(truncated bodies:", str(report["feed_api"]["bodies_truncated"]) + ")")
    print("Real forum API          :", report["feed_api"]["real_forum_api"])

    obtainable = [k for k, v in field_availability.items() if v["available"]]
    unavailable = [k for k, v in field_availability.items() if not v["available"]]

    print("\nFields obtainable       :", ", ".join(obtainable))
    print("Fields NOT obtainable   :", ", ".join(unavailable) or "none")
    print("\nSample records captured :", len(samples))
    print("Saved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
