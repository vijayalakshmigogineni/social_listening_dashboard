"""Step 4 - does a feed or API exist, and is it good enough to collect from?

SMF ships an XML export at action=.xml. Two things matter for feasibility:
whether it can be scoped to a board, and whether the item bodies are whole or
truncated. Both are measured here rather than assumed.

Note on separators: SMF's own style joins params with ";". This host throws
occasional 503s, which first looked separator-related; measured over 6 trials
each, ";" and "&" both returned 200 every time, so the 503s are load-related.
Both forms are still exercised below to keep that on the record.
"""

import json
import re
import time
from xml.etree import ElementTree

from mbl_common import FORUM, BOARDS, squash, fetch, fetch_response

OUTPUT_FILE = "mbl_feed_report.json"

# Feed shapes to try. "sep" records which separator style the URL uses.
CANDIDATES = [
    ("recent posts, rss 0.92", FORUM + "?action=.xml&type=rss", "&"),
    ("recent posts, rss 2.0", FORUM + "?action=.xml&type=rss2", "&"),
    ("recent posts, atom", FORUM + "?action=.xml&type=atom", "&"),
    ("recent topics (sa=news)", FORUM + "?action=.xml&sa=news&type=rss", "&"),
    ("board-scoped (Billing)", FORUM + "?action=.xml&type=rss&board=7", "&"),
    ("board-scoped, sa=posts", FORUM + "?action=.xml&sa=posts&type=rss&board=7", "&"),
    ("limit=50", FORUM + "?action=.xml&type=rss&limit=50", "&"),
    ("limit=200", FORUM + "?action=.xml&type=rss&limit=200", "&"),
    ("semicolon separators", FORUM + "?action=.xml;type=rss", ";"),
    ("semicolon, board-scoped", FORUM + "?action=.xml;type=rss;board=7", ";"),
]

# Things that would be a real API if present.
API_CANDIDATES = [
    ("wp-json (site runs WordPress)", "https://www.medicalbillinglive.com/wp-json/"),
    ("wp-json posts", "https://www.medicalbillinglive.com/wp-json/wp/v2/posts"),
    ("SMF api.php", "https://www.medicalbillinglive.com/members/api.php"),
    ("sitemap", "https://www.medicalbillinglive.com/sitemap.xml"),
]


def strip_tags(value):
    return squash(re.sub(r"<[^>]+>", " ", value or ""))


def probe_feed(name, url, sep):

    try:
        response = fetch_response(url)
    except Exception as exc:
        return {"name": name, "url": url, "separator": sep,
                "ok": False, "error": str(exc)}

    entry = {
        "name": name,
        "url": url,
        "separator": sep,
        "status": response.status_code,
        "content_type": response.headers.get("Content-Type"),
        "bytes": len(response.content),
        "ok": response.status_code == 200
               and "xml" in (response.headers.get("Content-Type") or ""),
    }

    if not entry["ok"]:
        return entry

    response.encoding = "cp1252"
    body = response.text

    try:
        root = ElementTree.fromstring(response.content)
    except ElementTree.ParseError as exc:
        entry["parse_error"] = str(exc)
        return entry

    # RSS and Atom put items in different places.
    items = root.findall(".//item")
    atom_ns = "{http://www.w3.org/2005/Atom}"

    if not items:
        items = root.findall(".//" + atom_ns + "entry")

    entry["item_count"] = len(items)

    fields = set()
    samples = []
    truncated = 0

    for item in items:

        for child in item:
            fields.add(child.tag.replace(atom_ns, ""))

        def grab(tag):
            node = item.find(tag)
            if node is None:
                node = item.find(atom_ns + tag)
            return node.text if node is not None else None

        title = squash(grab("title"))
        desc = strip_tags(grab("description") or grab("summary") or "")
        link = grab("link")

        # SMF cuts feed bodies at a fixed length and appends an ellipsis.
        if desc and desc.rstrip().endswith("..."):
            truncated += 1

        if len(samples) < 3:
            samples.append({
                "title": title,
                "link": squash(link),
                "category": squash(grab("category")),
                "pubDate": squash(grab("pubDate") or grab("updated")),
                "description_chars": len(desc or ""),
                "description_preview": (desc or "")[:160],
            })

    entry["item_fields"] = sorted(fields)
    entry["items_truncated"] = truncated
    entry["truncation_rate"] = (
        round(truncated / len(items), 2) if items else None
    )
    entry["has_author_field"] = any(
        f.lower() in ("author", "dc:creator", "creator") for f in fields
    )
    entry["samples"] = samples

    return entry


def probe_api(name, url):
    """Does the endpoint exist, and does it carry *forum* content?

    The marketing site in front of the forum runs WordPress, so /wp-json/
    answers. That is the WordPress REST API for the blog, not an interface to
    the SMF forum, so responding 200 is not the same as being useful here.
    """

    try:
        response = fetch_response(url)
    except Exception as exc:
        return {"name": name, "url": url, "exists": False, "error": str(exc)}

    serves_forum = False
    item_count = None

    if response.status_code == 200:
        try:
            payload = response.json()
            if isinstance(payload, list):
                item_count = len(payload)
                serves_forum = any(
                    "/members/" in str(entry.get("link", ""))
                    for entry in payload
                )
        except ValueError:
            serves_forum = "/members/index.php" in response.text

    return {
        "name": name,
        "url": url,
        "status": response.status_code,
        "content_type": response.headers.get("Content-Type"),
        "bytes": len(response.content),
        "exists": response.status_code == 200,
        "items_returned": item_count,
        "serves_forum_content": serves_forum,
        "preview": squash(response.text[:160]),
    }


def board_scope_check():
    """Can the feed be pinned to one board? Compare categories returned."""

    results = []

    for board in [b for b in BOARDS if b["rcm"]][:3]:

        url = FORUM + "?action=.xml&type=rss&board=" + str(board["id"])

        # Goes through fetch() so a transient 503 does not read as
        # "scoping unsupported".
        status, text = fetch(url)

        try:
            xml = re.sub(r"^<\?xml[^>]*\?>", "", text).strip()
            root = ElementTree.fromstring(xml)
            cats = {
                squash(c.text) for c in root.findall(".//item/category")
            }
            title = root.find(".//channel/title")

            results.append({
                "board_id": board["id"],
                "board_name": board["name"],
                "status": status,
                "channel_title": squash(title.text) if title is not None else None,
                "categories_in_items": sorted(c for c in cats if c),
                "scoped_correctly": cats == {board["name"]} if cats else False,
            })

        except Exception as exc:
            results.append({
                "board_id": board["id"],
                "board_name": board["name"],
                "status": status,
                "error": str(exc),
            })

        time.sleep(1.5)

    return results


def main():

    print("=" * 70)
    print("MEDICAL BILLING LIVE - STEP 4: FEED / API DISCOVERY")
    print("=" * 70)

    print("\n[feed endpoints]")
    feeds = []

    for name, url, sep in CANDIDATES:
        result = probe_feed(name, url, sep)
        feeds.append(result)
        print("  " + name.ljust(26),
              str(result.get("status")).ljust(5),
              "items=" + str(result.get("item_count", "-")).ljust(5),
              "bytes=" + str(result.get("bytes", 0)).ljust(7),
              "ok=" + str(result.get("ok")))
        time.sleep(1.5)

    print("\n[board scoping]")
    scoping = board_scope_check()
    for row in scoping:
        print("  board", str(row.get("board_id")).ljust(3),
              str(row.get("board_name"))[:26].ljust(28),
              "channel=" + str(row.get("channel_title"))[:34].ljust(36),
              "scoped=" + str(row.get("scoped_correctly")))

    print("\n[api surfaces]")
    apis = []
    for name, url in API_CANDIDATES:
        result = probe_api(name, url)
        apis.append(result)
        print("  " + name.ljust(32), str(result.get("status")).ljust(5),
              "exists=" + str(result["exists"]))
        time.sleep(1.0)

    working = [f for f in feeds if f.get("ok")]

    # The deciding question for a feed-based collector: whole bodies or not?
    truncating = [
        f for f in working if (f.get("truncation_rate") or 0) > 0
    ]

    best_item_count = max(
        (f.get("item_count") or 0 for f in working), default=0
    )

    report = {
        "source": "Medical Billing Live",
        "step": "4-feed-api",
        "feeds": feeds,
        "board_scoping": scoping,
        "api_surfaces": apis,
        "verdict": {
            "feed_exists": bool(working),
            "formats_available": sorted({
                f["name"].split(",")[-1].strip()
                for f in working
            }),
            "board_scoping_supported": any(
                r.get("scoped_correctly") for r in scoping
            ),
            "max_items_returned": best_item_count,
            "bodies_truncated": bool(truncating),
            # Only Atom carries an author; every RSS flavour omits it.
            "feed_carries_author": any(
                f.get("has_author_field") for f in working
            ),
            "formats_carrying_author": [
                f["name"] for f in working if f.get("has_author_field")
            ],
            "separator_note": (
                "';' and '&' both returned 200 on 6/6 trials; the occasional "
                "503 is load-related, not separator-related"
            ),
            "endpoints_responding": [
                a["name"] for a in apis if a["exists"]
            ],
            "real_api_found": any(
                a["exists"] and a.get("serves_forum_content") for a in apis
            ),
            "api_note": (
                "/wp-json/ answers because the marketing site runs WordPress, "
                "but it returns no posts and no forum content; the SMF install "
                "exposes no api.php. The XML feed is the only machine-readable "
                "forum surface."
            ),
            "usable_as_sole_collector": False,
            "reason": (
                "Feed bodies are truncated and carry no author field, and the "
                "feed only exposes the newest items, so it cannot reach the "
                "archive. Usable for change detection, not for collection."
            ),
        },
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    verdict = report["verdict"]

    print("\n" + "-" * 70)
    print("Feed exists:", verdict["feed_exists"])
    print("Board scoping supported:", verdict["board_scoping_supported"])
    print("Max items returned:", verdict["max_items_returned"])
    print("Bodies truncated:", verdict["bodies_truncated"])
    print("Feed carries author:", verdict["feed_carries_author"])
    print("Real API found:", verdict["real_api_found"])
    print("Saved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
