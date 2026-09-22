"""Step 1 - is the forum readable without an account, and what is on it?

Every request here is made logged out, with no cookie jar carried between
calls, so whatever comes back is what an anonymous visitor sees.
"""

import json
import re
import time
from bs4 import BeautifulSoup

from mbl_common import (
    SITE, FORUM, BOARDS, fetch, clean_url, squash, board_url
)

OUTPUT_FILE = "mbl_access_report.json"


def check_robots():

    status, text = fetch(SITE + "/robots.txt")

    disallowed = re.findall(r"(?im)^\s*Disallow:\s*(\S+)", text)

    return {
        "url": SITE + "/robots.txt",
        "status": status,
        "body": text.strip(),
        "disallow_rules": disallowed,
        "forum_path_disallowed": any(
            d.rstrip("/") in ("/members", "/members/index.php")
            for d in disallowed
        )
    }


def check_index():
    """Board index: confirms guest read access and lists the boards."""

    status, text = fetch(FORUM)

    soup = BeautifulSoup(text, "html.parser")

    # A guest sees the login/register links; a logged-in user would not.
    page_text = soup.get_text(" ", strip=True)

    boards_seen = []

    for link in soup.select('a[href*="board,"]'):

        label = squash(link.get_text(" ", strip=True))

        if not label:
            continue

        match = re.search(r"board,(\d+)\.0", link["href"])

        if not match:
            continue

        boards_seen.append({
            "board_id": int(match.group(1)),
            "name": label,
            "url": clean_url(link["href"])
        })

    # The index prints "N Posts" / "N Topics" per board, in board order.
    counts = re.findall(r"(\d+)\s+Posts\s+(\d+)\s+Topics", squash(page_text))

    for board, (posts, topics) in zip(boards_seen, counts):
        board["posts"] = int(posts)
        board["topics"] = int(topics)

    totals = re.search(
        r"(\d+)\s+Posts in\s+(\d+)\s+Topics by\s+(\d+)\s+Members",
        squash(page_text)
    )

    return {
        "url": FORUM,
        "status": status,
        "software": squash(
            (soup.select_one('a[href*="action=credits"]') or soup.new_tag("a")
             ).get_text(strip=True)
        ) or None,
        "readable_without_login": status == 200 and len(boards_seen) > 0,
        "guest_state_confirmed": (
            "login" in page_text.lower() and "register" in page_text.lower()
        ),
        "boards_visible": boards_seen,
        "forum_totals": {
            "posts": int(totals.group(1)) if totals else None,
            "topics": int(totals.group(2)) if totals else None,
            "members": int(totals.group(3)) if totals else None,
        } if totals else None
    }


def spot_check_boards():
    """Open each board logged out and confirm it serves topics, not a login wall."""

    results = []

    for board in BOARDS:

        url = board_url(board["id"], 0)
        status, text = fetch(url)

        soup = BeautifulSoup(text, "html.parser")

        topic_links = [
            a for a in soup.select('a[href*="topic,"]')
            if squash(a.get_text())
        ]

        blocked = bool(
            re.search(
                r"you (?:are not allowed|cannot)|please login|not allowed to access",
                text, re.I
            )
        )

        entry = {
            "board_id": board["id"],
            "name": board["name"],
            "rcm_relevant": board["rcm"],
            "url": url,
            "status": status,
            "topic_links_found": len(topic_links),
            "login_wall": blocked,
            "public": status == 200 and len(topic_links) > 0 and not blocked
        }

        print(
            f"  board={board['id']:<3} {board['name'][:44]:<46} "
            f"{status}  topics={len(topic_links):<4} public={entry['public']}"
        )

        results.append(entry)
        time.sleep(1.0)

    return results


def main():

    print("=" * 70)
    print("MEDICAL BILLING LIVE - STEP 1: PUBLIC ACCESS + BOARD MAP")
    print("=" * 70)

    print("\n[robots.txt]")
    robots = check_robots()
    print("  status:", robots["status"])
    print("  disallow:", robots["disallow_rules"])
    print("  forum path disallowed:", robots["forum_path_disallowed"])

    print("\n[board index]")
    index = check_index()
    print("  status:", index["status"])
    print("  software:", index["software"])
    print("  readable without login:", index["readable_without_login"])
    print("  guest (login/register links present):", index["guest_state_confirmed"])
    print("  totals:", index["forum_totals"])

    print("\n[per-board guest access]")
    boards = spot_check_boards()

    report = {
        "source": "Medical Billing Live",
        "entry_point": FORUM,
        "step": "1-access",
        "robots": robots,
        "index": index,
        "boards": boards,
        "summary": {
            "boards_total": len(boards),
            "boards_public": sum(1 for b in boards if b["public"]),
            "boards_rcm_relevant": sum(1 for b in boards if b["rcm_relevant"]),
            "login_required_anywhere": any(b["login_wall"] for b in boards),
        }
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    print("\n" + "-" * 70)
    print("Boards public:", report["summary"]["boards_public"],
          "/", report["summary"]["boards_total"])
    print("Login required anywhere:", report["summary"]["login_required_anywhere"])
    print("Saved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
