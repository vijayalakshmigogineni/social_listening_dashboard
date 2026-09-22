"""Step 2 - one category page in full, then whether pagination works.

Billing (board 7) is the test category: it is the largest RCM board on the
index. SMF pages a board by *item offset*, not page number, so page 2 is
board,7.20.html and the "97" link points at board,7.1920.html.

Every listing field recorded here is one the board page prints itself.
"""

import json
import re
import time
from bs4 import BeautifulSoup

from mbl_common import (
    BOARDS, TOPICS_PER_PAGE, fetch, clean_url, squash,
    board_url, parse_topic_id, parse_user_id
)

TEST_BOARD_ID = 7
OUTPUT_FILE = "mbl_category_report.json"


def parse_listing(text):
    """Topic rows from a board page. Only source-printed fields."""

    soup = BeautifulSoup(text, "html.parser")

    rows = []

    for cell in soup.select("td.subject"):

        link = cell.select_one('a[href*="topic,"]')

        if not link:
            continue

        row = cell.find_parent("tr")

        starter = cell.select_one('a[href*="action=profile"]')
        stats = row.select_one("td.stats")
        lastpost = row.select_one("td.lastpost")

        replies = views = None

        if stats:
            stats_text = squash(stats.get_text(" ", strip=True))
            match = re.search(r"(\d+)\s+Replies", stats_text)
            replies = int(match.group(1)) if match else None
            match = re.search(r"(\d+)\s+Views", stats_text)
            views = int(match.group(1)) if match else None

        last_date = last_author = None

        if lastpost:
            last_text = squash(lastpost.get_text(" ", strip=True))
            match = re.search(
                r"([A-Z][a-z]+ \d{1,2}, \d{4}, \d{2}:\d{2}:\d{2} [AP]M)",
                last_text
            )
            last_date = match.group(1) if match else None
            author_link = lastpost.select_one('a[href*="action=profile"]')
            last_author = squash(author_link.get_text()) if author_link else None

        rows.append({
            "thread_id": parse_topic_id(link["href"]),
            "thread_title": squash(link.get_text(" ", strip=True)),
            "thread_url": clean_url(link["href"]),
            "author_name": squash(starter.get_text()) if starter else None,
            "author_profile_url": clean_url(starter["href"]) if starter else None,
            "author_id": parse_user_id(starter["href"]) if starter else None,
            "reply_count": replies,
            "view_count": views,
            "last_post_date": last_date,
            "last_post_author": last_author,
            "is_sticky": "stickybg" in " ".join(row.get("class") or []),
        })

    return rows


def parse_pagination(text):
    """What the board page itself advertises about paging."""

    soup = BeautifulSoup(text, "html.parser")

    block = soup.select_one(".pagelinks")

    offsets = set()

    for link in soup.select('.pagelinks a[href*="board,"]'):
        match = re.search(r"board,\d+\.(\d+)\.html", link["href"])
        if match:
            offsets.add(int(match.group(1)))

    labels = [
        squash(a.get_text())
        for a in soup.select('.pagelinks a[href*="board,"]')
    ]

    numeric = [int(n) for n in labels if n and n.isdigit()]

    return {
        "pagination_block_present": block is not None,
        "raw_label": squash(block.get_text(" ", strip=True)) if block else None,
        "page_labels": labels,
        "offsets_linked": sorted(offsets),
        "last_page_number": max(numeric) if numeric else None,
        "max_offset_linked": max(offsets) if offsets else None,
        "items_per_page": TOPICS_PER_PAGE,
    }


def fetch_board_page(board_id, start):

    url = board_url(board_id, start)
    status, text = fetch(url)

    if status != 200:
        return {"url": url, "status": status, "rows": [], "pagination": None}

    return {
        "url": url,
        "status": status,
        "rows": parse_listing(text),
        "pagination": parse_pagination(text),
    }


def main():

    board = next(b for b in BOARDS if b["id"] == TEST_BOARD_ID)

    print("=" * 70)
    print("MEDICAL BILLING LIVE - STEP 2: CATEGORY PAGE + PAGINATION")
    print("Category under test:", board["name"], "(board", str(board["id"]) + ")")
    print("=" * 70)

    report = {
        "source": "Medical Billing Live",
        "step": "2-category-pagination",
        "category": board["name"],
        "board_id": board["id"],
        "url_scheme": "/members/index.php/board,<board_id>.<item_offset>.html",
        "pages": [],
    }

    # Page 1 in full, to show every field the listing yields.
    first = fetch_board_page(board["id"], 0)

    print("\n[page 1]", first["url"], "->", first["status"])
    print("  topic rows parsed:", len(first["rows"]))
    print("  pagination:", first["pagination"]["raw_label"])

    last_page = first["pagination"]["last_page_number"]
    max_offset = first["pagination"]["max_offset_linked"]

    report["pagination"] = first["pagination"]
    report["sample_rows_page1"] = first["rows"][:5]

    print("\n  first 5 rows:")
    for row in first["rows"][:5]:
        print("    -", (row["thread_title"] or "")[:52].ljust(54),
              "by", str(row["author_name"])[:16].ljust(18),
              "replies=" + str(row["reply_count"]))

    # Walk pages 1-3 plus the advertised last page and confirm each is
    # distinct - that is what proves paging actually advances.
    probes = [("page 1", 0), ("page 2", 20), ("page 3", 40)]

    if max_offset:
        probes.append(("page " + str(last_page) + " (last)", max_offset))

    seen_ids = {}

    for label, offset in probes:

        page = first if offset == 0 else fetch_board_page(board["id"], offset)

        ids = [r["thread_id"] for r in page["rows"]]

        dates = [r["last_post_date"] for r in page["rows"] if r["last_post_date"]]

        entry = {
            "label": label,
            "offset": offset,
            "url": page["url"],
            "status": page["status"],
            "rows": len(page["rows"]),
            "thread_ids": ids,
            "newest_last_post": dates[0] if dates else None,
            "oldest_last_post": dates[-1] if dates else None,
        }

        report["pages"].append(entry)
        seen_ids[label] = set(ids)

        print("\n[" + label + "] offset=" + str(offset),
              "->", page["status"], " rows=" + str(len(page["rows"])))
        print("  last-post dates on page:",
              entry["newest_last_post"], " .. ", entry["oldest_last_post"])

        if offset != 0:
            time.sleep(1.0)

    # Distinctness: pagination is only real if pages do not repeat content.
    labels = list(seen_ids)
    overlaps = {}

    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            shared = seen_ids[labels[i]] & seen_ids[labels[j]]
            overlaps[labels[i] + " vs " + labels[j]] = len(shared)

    all_ids = [i for s in seen_ids.values() for i in s]

    report["pagination_verdict"] = {
        "pagination_exists": bool(last_page and last_page > 1),
        "last_page_number": last_page,
        "max_offset": max_offset,
        "pages_are_distinct": all(v == 0 for v in overlaps.values()),
        "pairwise_overlap": overlaps,
        "unique_threads_across_probed_pages": len(set(all_ids)),
        "estimated_total_topics_from_paging": (
            (last_page * TOPICS_PER_PAGE) if last_page else None
        ),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    print("\n" + "-" * 70)
    verdict = report["pagination_verdict"]
    print("Pagination exists:", verdict["pagination_exists"])
    print("Last page:", verdict["last_page_number"],
          "(max offset", str(verdict["max_offset"]) + ")")
    print("Pages distinct (no overlap):", verdict["pages_are_distinct"])
    print("Pairwise overlap:", verdict["pairwise_overlap"])
    print("Saved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
