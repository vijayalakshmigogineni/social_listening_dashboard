"""Step 3 - one representative thread, down to the individual post.

Two threads are opened:

  topic 6999  "Working Reports: Open Claims/Patient Responsibility"
              a genuine RCM thread, 8 replies, fits on one page.
  topic 1706  "DMERC", 20 replies - 21 posts total, so it spills past the
              15-posts-per-page boundary and shows in-thread paging.

Only fields the page itself prints are recorded. Nothing is inferred and
nothing is classified. `location` is probed for explicitly so its absence is
recorded as a measured fact rather than an omission.
"""

import json
import re
import time
from bs4 import BeautifulSoup

from mbl_common import (
    fetch, clean_url, squash, topic_url, parse_msg_id, parse_user_id
)

THREADS = [
    {"topic_id": 6999, "note": "genuine RCM thread, single page"},
    {"topic_id": 1706, "note": "21 posts, spans 2 in-thread pages"},
]

POSTS_PER_PAGE = 15
OUTPUT_FILE = "mbl_thread_report.json"

# SMF renders optional profile fields as <li class="...">Label: value</li>.
# Location is the one we were asked about; capture the whole block so we can
# report exactly which fields this install actually exposes.
PROFILE_FIELD_CLASSES = (
    "postgroup", "stars", "postcount", "membergroup",
    "blurb", "gender", "location", "im_icons", "profile",
)


def parse_category(soup):
    """Board name from the breadcrumb.

    The breadcrumb reads Forum > Category > Board > (Moderators) > Thread,
    and moderator names are plain anchors too, so position is unreliable.
    The board is the one crumb whose href is a board URL.
    """

    nav = soup.select_one(".navigate_section")

    if not nav:
        return None, None

    board = None

    board_link = nav.select_one('a[href*="board,"]')

    if board_link:
        board = squash(board_link.get_text())

    # The template renders the breadcrumb twice (above and below the posts).
    crumb = []

    for link in nav.select("a"):
        label = squash(link.get_text())
        if label and label not in crumb:
            crumb.append(label)

    return board, " > ".join(crumb)


def parse_posts(text, topic_id, category):
    """One record per post block on the page."""

    soup = BeautifulSoup(text, "html.parser")

    posts = []

    for wrapper in soup.select("div.post_wrapper"):

        poster = wrapper.select_one(".poster")
        area = wrapper.select_one(".postarea")

        if not poster or not area:
            continue

        # Post identity: the subject anchor carries the canonical permalink.
        subject_link = area.select_one('h5 a[href*="msg"]')
        body = area.select_one(".post .inner")

        post_id = None

        if body and body.get("id"):
            post_id = body["id"].replace("msg_", "")

        if not post_id and subject_link:
            post_id = parse_msg_id(subject_link["href"])

        # Author
        author_link = poster.select_one('h4 a[href*="action=profile"]')
        author_name = squash(author_link.get_text()) if author_link else None

        # An unregistered/deleted poster renders as plain text, no link.
        if not author_name:
            author_name = squash(poster.select_one("h4").get_text()) if \
                poster.select_one("h4") else None

        # Date: the ".smalltext" next to the subject holds "on: <date>".
        date_block = area.select_one(".keyinfo .smalltext")
        date_text = squash(date_block.get_text(" ", strip=True)) if date_block else None
        date_value = None

        if date_text:
            match = re.search(
                r"([A-Z][a-z]+ \d{1,2}, \d{4}, \d{2}:\d{2}:\d{2} [AP]M)",
                date_text
            )
            date_value = match.group(1) if match else None

        # Every optional field this install renders in the poster column.
        poster_fields = {}

        for item in poster.select("li"):
            classes = item.get("class") or []
            value = squash(item.get_text(" ", strip=True))
            if not value:
                continue
            key = classes[0] if classes else "unclassed"
            poster_fields.setdefault(key, value)

        # Location is only real if the install prints it.
        location = poster_fields.get("location")

        if location and ":" in location:
            location = squash(location.split(":", 1)[1])

        # Guests post under a display name with no account behind it, so no
        # profile URL exists for them. That is a property of the source, not
        # a parsing gap, so record which kind of author each post has. The
        # "Guest" label lands in membergroup here, not postgroup.
        is_guest = "Guest" in (
            poster_fields.get("membergroup"),
            poster_fields.get("postgroup"),
        )

        author_type = (
            "guest" if is_guest
            else ("registered" if author_link else "unknown")
        )

        posts.append({
            "thread_id": str(topic_id),
            "category": category,
            "post_id": post_id,
            "post_url": (
                clean_url(subject_link["href"]) if subject_link else None
            ),
            "author_name": author_name,
            "author_type": author_type,
            "author_id": parse_user_id(author_link["href"]) if author_link else None,
            "author_profile_url": (
                clean_url(author_link["href"]) if author_link else None
            ),
            "date": date_value,
            "date_raw": date_text,
            "post_text": squash(body.get_text(" ", strip=True)) if body else None,
            "post_text_chars": len(squash(body.get_text(" ", strip=True)) or "")
            if body else 0,
            "location": location,
            "poster_fields_present": sorted(poster_fields),
        })

    return posts


def parse_thread_pagination(text):

    soup = BeautifulSoup(text, "html.parser")

    offsets = set()

    for link in soup.select('.pagelinks a[href*="topic,"]'):
        match = re.search(r"topic,\d+\.(\d+)\.html", link["href"])
        if match:
            offsets.add(int(match.group(1)))

    block = soup.select_one(".pagelinks")

    return {
        "in_thread_pagination": bool(offsets),
        "raw_label": squash(block.get_text(" ", strip=True)) if block else None,
        "offsets_linked": sorted(offsets),
        "posts_per_page": POSTS_PER_PAGE,
    }


def collect_thread(topic_id, note):

    print("\n" + "=" * 70)
    print("THREAD", topic_id, "-", note)
    print("=" * 70)

    url = topic_url(topic_id, 0)
    status, text = fetch(url)

    if status != 200:
        print("  FAILED:", status)
        return {"topic_id": topic_id, "status": status, "error": "fetch failed"}

    soup = BeautifulSoup(text, "html.parser")

    title = squash(soup.title.get_text()) if soup.title else None
    category, breadcrumb = parse_category(soup)
    nav = parse_thread_pagination(text)

    posts = parse_posts(text, topic_id, category)

    print("  title:      ", title)
    print("  category:   ", category)
    print("  breadcrumb: ", breadcrumb)
    print("  status:     ", status)
    print("  posts on page 1:", len(posts))
    print("  in-thread pagination:", nav["in_thread_pagination"],
          nav["raw_label"] or "")

    # Pull page 2 when the thread has one, to confirm replies keep coming.
    page2_posts = []

    if nav["offsets_linked"]:

        next_offset = min(o for o in nav["offsets_linked"] if o > 0)
        time.sleep(1.0)

        url2 = topic_url(topic_id, next_offset)
        status2, text2 = fetch(url2)

        if status2 == 200:
            page2_posts = parse_posts(text2, topic_id, category)
            print("  page 2 (offset " + str(next_offset) + "):",
                  len(page2_posts), "more posts")

    all_posts = posts + page2_posts

    filled = {}

    for field in ("post_id", "post_url", "author_name", "author_profile_url",
                  "date", "post_text", "category", "location"):
        filled[field] = sum(
            1 for p in all_posts if p.get(field) not in (None, "", [])
        )

    guests = sum(1 for p in all_posts if p.get("author_type") == "guest")
    registered = len(all_posts) - guests

    print("\n  field coverage over", len(all_posts), "posts",
          "(" + str(registered), "registered,", guests, "guest):")

    for field, count in filled.items():

        # Only registered posters can have a profile URL at all.
        denominator = registered if field == "author_profile_url" else len(all_posts)

        mark = "yes" if count == denominator else (
            "none" if count == 0 else "partial")

        note = " (registered only)" if field == "author_profile_url" else ""

        print("    " + field.ljust(20), str(count) + "/" + str(denominator),
              "  " + mark + note)

    filled["_registered_posts"] = registered
    filled["_guest_posts"] = guests

    print("\n  first post preview:")
    if all_posts:
        first = all_posts[0]
        print("    author:", first["author_name"], "| date:", first["date"])
        print("    text:  ", (first["post_text"] or "")[:180])

    return {
        "topic_id": topic_id,
        "note": note,
        "url": clean_url(url),
        "status": status,
        "thread_title": title,
        "category": category,
        "breadcrumb": breadcrumb,
        "pagination": nav,
        "posts_page1": len(posts),
        "posts_page2": len(page2_posts),
        "posts_total_collected": len(all_posts),
        "field_coverage": filled,
        "posts": all_posts,
    }


def main():

    print("=" * 70)
    print("MEDICAL BILLING LIVE - STEP 3: THREAD + INDIVIDUAL POSTS")
    print("=" * 70)

    report = {
        "source": "Medical Billing Live",
        "step": "3-thread-posts",
        "posts_per_page": POSTS_PER_PAGE,
        "threads": [],
    }

    for thread in THREADS:
        report["threads"].append(
            collect_thread(thread["topic_id"], thread["note"])
        )
        time.sleep(1.5)

    # Roll the location probe up: it is the one requested field we expect to
    # be absent, so state it from the measurement.
    all_posts = [
        p for t in report["threads"] for p in t.get("posts", [])
    ]

    location_values = [p["location"] for p in all_posts if p.get("location")]

    field_classes = sorted({
        c for p in all_posts for c in p.get("poster_fields_present", [])
    })

    report["location_probe"] = {
        "posts_examined": len(all_posts),
        "posts_with_location": len(location_values),
        "distinct_values": sorted(set(location_values)),
        "poster_field_classes_seen": field_classes,
        "conclusion": (
            "location not displayed on posts in this install"
            if not location_values else "location displayed on some posts"
        ),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    print("\n" + "-" * 70)
    print("Posts examined:", report["location_probe"]["posts_examined"])
    print("Posts with a displayed location:",
          report["location_probe"]["posts_with_location"])
    print("Poster-column fields this install renders:",
          ", ".join(field_classes))
    print("Saved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
