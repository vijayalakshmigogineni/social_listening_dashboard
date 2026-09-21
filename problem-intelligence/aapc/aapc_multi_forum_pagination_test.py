import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

SITE = "https://www.aapc.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

FORUMS = [
    ("Practice Management", "general-discussion.582"),
    ("Medicare Regulations", "medicare-regulations.479"),
    ("Modifiers", "modifiers.483"),
    ("Anesthesia", "anesthesia.440"),
    ("Orthopaedics", "orthopaedics.427"),
    ("Interventional Radiology", "interventional-radiology.480"),
    ("Payer / Health Plan", "payer-health-plan.661"),
]

OUTPUT_FILE = "aapc_pagination_report.json"


def canonical_thread_urls(soup):
    """Unique canonical thread URLs on one forum page, /latest excluded."""

    urls = []
    seen = set()

    for link in soup.select('a[href*="/threads/"]'):

        href = link.get("href")

        if not href:
            continue

        # Exclude the /latest duplicate link
        if href.rstrip("/").endswith("/latest"):
            continue

        full = urljoin(SITE, href)

        # Canonical forms: .../threads/<slug>.<id>/  and  .../threads/<id>/
        match = re.match(
            r"^(https://www\.aapc\.com/discuss/threads/"
            r"(?:[^/]+\.)?(\d+))/?$",
            full
        )

        if not match:
            continue

        canonical = match.group(1) + "/"

        if canonical in seen:
            continue

        seen.add(canonical)

        urls.append({
            "thread_id": match.group(2),
            "url": canonical
        })

    return urls


def pagination_info(soup):
    """Pagination links present? Last page number if determinable."""

    page_numbers = set()
    next_link = None

    for link in soup.select("a[href]"):

        href = link["href"]

        match = re.search(r"/page-(\d+)", href)

        if match:
            page_numbers.add(int(match.group(1)))

        classes = link.get("class") or []

        if "pageNav-jump--next" in classes:
            next_link = urljoin(SITE, href)

    has_nav = soup.select_one(".pageNavWrapper, .pageNav") is not None

    return {
        "pagination_links_found": has_nav or bool(page_numbers),
        "next_link": next_link,
        "page_numbers_seen": sorted(page_numbers),
        "last_page": max(page_numbers) if page_numbers else None
    }


def fetch_page(base_url, page_number):

    if page_number == 1:
        url = base_url
    else:
        url = base_url + "page-" + str(page_number)

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    print("  Page", page_number, "->", response.status_code, url)

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    threads = canonical_thread_urls(soup)

    return url, response.status_code, threads, pagination_info(soup)


def test_forum(name, slug):

    print("\n" + "=" * 60)
    print(name.upper())
    print("=" * 60)

    base_url = SITE + "/discuss/forums/" + slug + "/"

    result = {
        "forum": name,
        "slug": slug,
        "base_url": base_url,
        "pages": [],
        "pagination_links_found": False,
        "last_page": None,
        "unique_threads_across_pages": 0,
        "overlap_between_pages": 0,
        "last_page_check": None,
        "error": None
    }

    all_ids = []

    try:
        for page_number in (1, 2, 3):

            url, status, threads, nav = fetch_page(base_url, page_number)

            result["pages"].append({
                "page": page_number,
                "url": url,
                "status": status,
                "unique_threads": len(threads),
                "thread_ids": [t["thread_id"] for t in threads],
                "sample_urls": [t["url"] for t in threads[:3]]
            })

            all_ids.extend(t["thread_id"] for t in threads)

            if nav["pagination_links_found"]:
                result["pagination_links_found"] = True

            if nav["last_page"] is not None:
                result["last_page"] = max(
                    result["last_page"] or 0,
                    nav["last_page"]
                )

    except Exception as exc:
        result["error"] = str(exc)
        print("  ERROR:", exc)

    result["unique_threads_across_pages"] = len(set(all_ids))
    result["overlap_between_pages"] = len(all_ids) - len(set(all_ids))

    # Confirm the advertised last page actually serves threads
    if result["last_page"]:

        try:
            url, status, threads, _ = fetch_page(
                base_url,
                result["last_page"]
            )

            result["last_page_check"] = {
                "url": url,
                "status": status,
                "unique_threads": len(threads),
                "reachable": status == 200 and len(threads) > 0
            }

        except Exception as exc:
            result["last_page_check"] = {
                "reachable": False,
                "error": str(exc)
            }

    print("\n  Unique threads per page:", [
        p["unique_threads"] for p in result["pages"]
    ])
    print("  Pagination links found:", result["pagination_links_found"])
    print("  Last available page:", result["last_page"])
    print("  Unique across 3 pages:", result["unique_threads_across_pages"])
    print("  Duplicate overlap:", result["overlap_between_pages"])

    return result


def main():

    print("=" * 60)
    print("AAPC MULTI-FORUM PAGINATION TEST")
    print("=" * 60)

    report = {
        "source": "AAPC",
        "test": "pagination",
        "pages_tested": [1, 2, 3],
        "forums": []
    }

    for name, slug in FORUMS:
        report["forums"].append(test_forum(name, slug))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(
        f"\n{'Forum':<26}{'P1':<5}{'P2':<5}{'P3':<5}"
        f"{'Nav':<6}{'Last':<7}{'Unique':<8}{'Overlap':<9}{'LastPageOK'}"
    )
    print("-" * 82)

    for forum in report["forums"]:

        counts = [p["unique_threads"] for p in forum["pages"]]

        while len(counts) < 3:
            counts.append(0)

        print(
            f"{forum['forum']:<26}"
            f"{counts[0]:<5}{counts[1]:<5}{counts[2]:<5}"
            f"{str(forum['pagination_links_found']):<6}"
            f"{str(forum['last_page']):<7}"
            f"{forum['unique_threads_across_pages']:<8}"
            f"{forum['overlap_between_pages']:<9}"
            f"{(forum.get('last_page_check') or {}).get('reachable')}"
        )

    print("\nSaved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
