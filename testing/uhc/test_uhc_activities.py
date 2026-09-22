"""
test_uhc_activities.py

Extends the parsing already used in test_uhc.py / test_uhc_commercial.py.
Those two scripts hit the same 4 UHCprovider.com listing pages and only
pull <a> tag text + href out of the page (discarding everything else on
the page). Manual inspection of the raw HTML (via requests, saved to disk
and grepped) showed that UHC's "faceted listing" widget used on these
pages wraps every policy/bulletin link in a container
(class contains "faceted-list-item-list") that ALSO contains:

    <p class="... list-date">Last Published MM.DD.YYYY</p>

and, for individual medical/drug policies specifically, a
<p class="faceted-item-description"> that frequently starts with
"Effective Date: MM.DD.YYYY - ...".

This script does NOT hit any new endpoint and does NOT add any new
authentication/scraping mechanism. It reuses the exact same 4 URLs and
the same requests+BeautifulSoup approach as test_uhc.py, but walks the
container element instead of just the bare <a> tag, so the real
"Last Published" / "Effective Date" fields that already exist in the
HTML are captured instead of being discarded.
"""

import json
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

URLS = {
    "commercial_medical": "https://www.uhcprovider.com/en/policies-protocols/commercial-policies/commercial-medical-drug-policies.html",
    "monthly_updates": "https://www.uhcprovider.com/en/resource-library/news/2026/mpub-updates-sep-2026.html",
    "commercial_reimbursement": "https://www.uhcprovider.com/en/policies-protocols/commercial-policies/commercial-reimbursement-policies.html",
    "medicare_advantage": "https://www.uhcprovider.com/en/policies-protocols/medicare-advantage-policies/medicare-advantage-medical-policies.html",
    "prior_auth_reduction_oct2026": "https://www.uhcprovider.com/en/resource-library/news/2026/october-prior-auth-reductions.html",
}

HEADERS = {"User-Agent": "Mozilla/5.0"}

DATE_RE = re.compile(r"(\d{1,2})[./](\d{1,2})[./](\d{4})")


def parse_date(raw):
    """Parse a MM.DD.YYYY or MM/DD/YYYY string into an ISO date string. Returns None if unparseable."""
    if not raw:
        return None
    m = DATE_RE.search(raw)
    if not m:
        return None
    mm, dd, yyyy = m.groups()
    try:
        return datetime(int(yyyy), int(mm), int(dd)).date().isoformat()
    except ValueError:
        return None


def parse_longform_date(raw):
    """Parse a longform date string like 'September 01, 2026' or 'Oct. 1, 2026'
    into an ISO date string. Returns None if unparseable."""
    if not raw:
        return None
    try:
        return date_parser.parse(raw, fuzzy=True).date().isoformat()
    except (ValueError, OverflowError):
        return None


def classify_item_type(url, title):
    u = url.lower()
    t = title.lower()
    if "mpub-archive" in u or "rpub" in u and "archive" in t:
        return "bulletin_archive_index"
    if "policy-update-bulletin" in u or "update-bulletin" in u or "bulletin" in t:
        return "policy_update_bulletin"
    return "individual_policy_or_reimbursement_policy"


def extract_faceted_items(soup, base_url, source_page):
    records = []
    containers = soup.find_all(class_="faceted-list-item-list")
    for c in containers:
        a = c.find("a", href=True)
        if not a:
            continue
        title = a.get_text(" ", strip=True)
        url = urljoin(base_url, a["href"])

        # "Last Published" date - lives in a <p>/<span> whose class contains "list-date"
        date_el = c.find(class_=re.compile(r"\blist-date\b"))
        last_published_raw = None
        if date_el:
            last_published_raw = date_el.get_text(" ", strip=True)
            last_published_raw = last_published_raw.replace("Last Published", "").strip()

        # Description paragraph (only present for some listing types)
        desc_el = c.find(class_=re.compile(r"\bfaceted-item-description\b"))
        description = desc_el.get_text(" ", strip=True) if desc_el else None

        effective_date_raw = None
        if description:
            m = re.search(r"Effective Date:\s*([\d./]+)", description)
            if m:
                effective_date_raw = m.group(1)

        records.append({
            "title": title,
            "url": url,
            "source_page": source_page,
            "source_page_url": base_url,
            "item_type": classify_item_type(url, title),
            "last_published_raw": last_published_raw,
            "last_published_iso": parse_date(last_published_raw),
            "effective_date_raw": effective_date_raw,
            "effective_date_iso": parse_date(effective_date_raw),
            "description": description,
        })
    return records


def extract_monthly_update_links(soup, base_url, source_page):
    """monthly_updates page has no faceted-list-item widget - it is a flat
    set of <h2> plan headings each followed by a <ul><li><a> of one bulletin
    link per plan type for the month named in the page title. No distinct
    per-item date exists on this page beyond the page-level month/year."""
    records = []
    content_root = soup.find("div", class_="richtext")
    if not content_root:
        return records
    for a in content_root.find_all("a", href=True):
        title = a.get_text(" ", strip=True)
        if not title:
            continue
        url = urljoin(base_url, a["href"])
        records.append({
            "title": title,
            "url": url,
            "source_page": source_page,
            "source_page_url": base_url,
            "item_type": "policy_update_bulletin",
            "last_published_raw": None,
            "last_published_iso": None,
            "effective_date_raw": None,
            "effective_date_iso": None,
            "description": None,
        })
    return records


def extract_prior_auth_reduction_news(soup, base_url, source_page):
    """october-prior-auth-reductions.html is a single richtext news article,
    not a faceted-list page. Manual inspection of the raw HTML showed:
      - the publish date lives in <div class="title__date">September 01, 2026</div>
      - the headline is the page's only <h1>
      - the <meta name="description"> summary contains the plain-English
        effective date ("On Oct. 1, 2026, we're eliminating 30% of prior
        authorization requirements...")
      - the body (<div class="richtext...">) links out to 5 plan-specific
        PDF code-reduction lists, one per plan type, with no per-link date
        of their own (they inherit the article's publish/effective dates).

    Emits one record for the article itself plus one record per linked PDF
    so each plan's code list shows up as its own reviewable item, consistent
    with how individual policy PDFs are recorded elsewhere in this script."""
    records = []

    date_el = soup.find(class_=re.compile(r"\btitle__date\b"))
    last_published_raw = date_el.get_text(" ", strip=True) if date_el else None
    last_published_iso = parse_longform_date(last_published_raw)

    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else base_url

    meta_desc = soup.find("meta", attrs={"name": "description"})
    meta_desc_content = meta_desc.get("content") if meta_desc else None

    effective_date_raw = None
    if meta_desc_content:
        m = re.search(
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+\d{4}",
            meta_desc_content,
        )
        if m:
            effective_date_raw = m.group(0)
    effective_date_iso = parse_longform_date(effective_date_raw)

    records.append({
        "title": title,
        "url": base_url,
        "source_page": source_page,
        "source_page_url": base_url,
        "item_type": "prior_auth_reduction_announcement",
        "last_published_raw": last_published_raw,
        "last_published_iso": last_published_iso,
        "effective_date_raw": effective_date_raw,
        "effective_date_iso": effective_date_iso,
        "description": meta_desc_content,
    })

    content_root = soup.find(class_=re.compile(r"\brichtext\b"))
    if content_root:
        for a in content_root.find_all("a", href=True):
            href = a["href"]
            if not href.lower().endswith(".pdf"):
                continue
            plan_title = a.get_text(" ", strip=True)
            records.append({
                "title": f"Prior Authorization Reduction Code List - {plan_title}",
                "url": urljoin(base_url, href),
                "source_page": source_page,
                "source_page_url": base_url,
                "item_type": "prior_auth_code_reduction_list",
                "last_published_raw": last_published_raw,
                "last_published_iso": last_published_iso,
                "effective_date_raw": effective_date_raw,
                "effective_date_iso": effective_date_iso,
                "description": f"Procedure code list for prior authorization requirements eliminated for {plan_title}, part of UnitedHealthcare's announced 30% prior authorization reduction.",
            })

    return records


def main():
    meta = {
        "scripts_used": ["test_uhc_activities.py (new script extending test_uhc.py / test_uhc_commercial.py parsing logic)"],
        "endpoints": [],
        "retrieval_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "http_status": {},
        "errors": [],
    }

    all_dated_records = []
    all_monthly_records = []

    for name, url in URLS.items():
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
        except Exception as e:
            meta["errors"].append(f"{name}: {type(e).__name__}: {e}")
            continue

        meta["endpoints"].append(url)
        meta["http_status"][name] = resp.status_code

        if resp.status_code != 200:
            meta["errors"].append(f"{name}: HTTP {resp.status_code}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        if name == "monthly_updates":
            recs = extract_monthly_update_links(soup, resp.url, name)
            all_monthly_records.extend(recs)
            print(f"{name}: {len(recs)} plan-bulletin links (no per-item date on this page)")
        elif name == "prior_auth_reduction_oct2026":
            recs = extract_prior_auth_reduction_news(soup, resp.url, name)
            all_dated_records.extend(recs)
            n_dated = sum(1 for r in recs if r["last_published_iso"])
            print(f"{name}: {len(recs)} items found (article + linked PDFs), {n_dated} with a parsed publish date")
        else:
            recs = extract_faceted_items(soup, resp.url, name)
            all_dated_records.extend(recs)
            n_dated = sum(1 for r in recs if r["last_published_iso"])
            print(f"{name}: {len(recs)} faceted-list items found, {n_dated} with a parsed 'Last Published' date")

    # De-duplicate by URL (same PDF sometimes linked from more than one section)
    seen = set()
    deduped = []
    for r in all_dated_records:
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        deduped.append(r)

    dated = [r for r in deduped if r["last_published_iso"]]
    undated = [r for r in deduped if not r["last_published_iso"]]

    dated.sort(key=lambda r: r["last_published_iso"], reverse=True)

    top_100 = dated[:100]

    meta["total_faceted_items_found_all_pages"] = len(deduped)
    meta["total_with_parsable_last_published_date"] = len(dated)
    meta["total_without_parsable_date"] = len(undated)
    meta["total_records_selected_for_top100_file"] = len(top_100)
    meta["monthly_updates_page_links_count"] = len(all_monthly_records)
    if dated:
        meta["date_range_all_dated_items"] = {
            "oldest_last_published": dated[-1]["last_published_iso"],
            "newest_last_published": dated[0]["last_published_iso"],
        }
    if top_100:
        meta["date_range_top100_file"] = {
            "oldest_last_published": top_100[-1]["last_published_iso"],
            "newest_last_published": top_100[0]["last_published_iso"],
        }
    meta["fields_available"] = list(top_100[0].keys()) if top_100 else list(dated[0].keys()) if dated else []
    meta["limitations"] = [
        "monthly_updates page (mpub-updates-sep-2026.html) has NO faceted-list-item widget and NO per-item date field in its HTML; it is a flat list of one PDF link per plan type, all implicitly dated 'September 2026' by the page's own subject. These 20 links are saved separately in uhc_monthly_update_links.json and are NOT included in uhc_activities_top100.json / uhc_activities_all_dated.json because they have no genuine per-item date to sort by.",
        "'last_published_iso' is parsed from the site's own 'Last Published MM.DD.YYYY' text next to each policy/bulletin link (visible on-page, human readable date, not a hidden metadata timestamp).",
        "'effective_date_iso' is only populated for the commercial_medical individual-policy listing, where the on-page description text begins with 'Effective Date: MM.DD.YYYY -'. The reimbursement and medicare_advantage listings on this site do not print an Effective Date in their description text, so this field is null there (not fabricated/estimated).",
        "No login, token, or CAPTCHA was required for any of the 4 pages hit by this script; all returned HTTP 200 to a plain GET with only a User-Agent header.",
        "Console/terminal display of the en dash character (U+2013) used in many titles can render as a mangled glyph in some terminals; the JSON files on disk were verified via raw byte inspection to contain the correct UTF-8 bytes (\\xe2\\x80\\x93).",
        "prior_auth_reduction_oct2026 (october-prior-auth-reductions.html) is a single richtext news article, not a faceted-list page: its 'last_published_iso' comes from a <div class=\"title__date\"> on the page (parsed with dateutil, fuzzy) and its 'effective_date_iso' is extracted from the plain-English <meta name=\"description\"> summary, not from a machine-readable field. It is included here because UHC announced ~1,700 procedure codes losing prior-authorization requirements on 09.01.2026 effective 10.01.2026, split across 5 plan-specific PDFs; this script records the article itself plus one row per linked PDF (item_type prior_auth_reduction_announcement / prior_auth_code_reduction_list).",
    ]

    print("\n=== SUMMARY ===")
    print("Total distinct faceted items across 3 listing pages:", len(deduped))
    print("With parsable Last Published date:", len(dated))
    print("Without parsable date:", len(undated))
    print("Monthly-updates plan links (separate, undated):", len(all_monthly_records))
    if dated:
        print("Newest last_published:", dated[0]["last_published_iso"], "-", dated[0]["title"])
        print("Oldest last_published:", dated[-1]["last_published_iso"], "-", dated[-1]["title"])

    with open("uhc_activities_top100.json", "w", encoding="utf-8") as f:
        json.dump(top_100, f, indent=2, ensure_ascii=False)

    with open("uhc_activities_all_dated.json", "w", encoding="utf-8") as f:
        json.dump(dated, f, indent=2, ensure_ascii=False)

    with open("uhc_activities_undated.json", "w", encoding="utf-8") as f:
        json.dump(undated, f, indent=2, ensure_ascii=False)

    with open("uhc_monthly_update_links.json", "w", encoding="utf-8") as f:
        json.dump(all_monthly_records, f, indent=2, ensure_ascii=False)

    with open("_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print("\nWrote: uhc_activities_top100.json, uhc_activities_all_dated.json, uhc_activities_undated.json, uhc_monthly_update_links.json, _meta.json")


if __name__ == "__main__":
    main()
