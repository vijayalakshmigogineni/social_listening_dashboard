import json
import re
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

DAYS_BACK = 30
REQUEST_TIMEOUT = 60

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

OUTPUT_FILE = "mac_signals.json"


# ============================================================
# SOURCE CONFIGURATION
# ============================================================

SOURCES = {

    "Palmetto": {
        "source_type": "Medicare Administrative Contractor",
        "start_urls": [
            "https://palmettogba.com/prior",
            "https://palmettogba.com/jmb/news",
        ],
        "jurisdictions": [
            "Jurisdiction J",
            "Jurisdiction M",
        ],
    },

    "CGS": {
        "source_type": "Medicare Administrative Contractor",
        "start_urls": [
            "https://www.cgsmedicare.com/parta/pubs/news/index.html",
            "https://www.cgsmedicare.com/partb/pubs/news/index.html",
            "https://www.cgsmedicare.com/dme/news/index.html",
        ],
        "jurisdictions": [
            "J15",
            "DME MAC B",
            "DME MAC C",
        ],
    },

    "WPS": {
        "source_type": "Medicare Administrative Contractor",
        "start_urls": [
            "https://www.wpsgha.com/",
        ],
        "jurisdictions": [],
    },
}


# ============================================================
# KEYWORD DICTIONARIES
# ============================================================

SIGNAL_KEYWORDS = {

    "Authorization / Utilization Management": {
        "PA requirement": [
            "prior authorization",
            "prior-authorization",
            "prior auth",
            "authorization required",
            "authorization requirement",
        ],
        "PA documentation": [
            "prior authorization documentation",
            "documentation required",
            "required documentation",
            "documentation requirements",
        ],
        "PA turnaround": [
            "turnaround",
            "review timeframe",
            "decision timeframe",
            "processing time",
        ],
        "Additional information": [
            "additional information",
            "additional documentation",
            "request for information",
        ],
        "Peer-to-peer": [
            "peer-to-peer",
            "peer to peer",
        ],
        "Frequency restriction": [
            "frequency limit",
            "frequency limitation",
            "frequency restriction",
        ],
    },

    "Denials / Claims Friction": {
        "New denial reason": [
            "denial reason",
            "new denial",
            "denials",
        ],
        "Documentation denial": [
            "documentation denial",
            "missing documentation",
            "insufficient documentation",
        ],
        "Coding denial": [
            "coding error",
            "coding denial",
            "incorrect coding",
            "coding requirement",
        ],
        "No-auth denial": [
            "authorization denial",
            "no authorization",
            "without authorization",
            "missing authorization",
        ],
        "Claim rework": [
            "correct and resubmit",
            "resubmit the claim",
            "claim correction",
            "claims rejected",
            "claim rejected",
        ],
    },

    "Coverage / Policy": {
        "Coverage change": [
            "coverage change",
            "coverage update",
            "coverage policy",
        ],
        "Coverage restriction": [
            "coverage restriction",
            "coverage limitation",
            "limitations",
        ],
        "Policy revision": [
            "policy revision",
            "policy update",
            "policy changes",
            "updated policy",
        ],
        "LCD/NCD change": [
            "lcd",
            "ncd",
            "local coverage determination",
            "national coverage determination",
        ],
        "Effective-date change": [
            "effective date",
            "effective ",
            "effective on",
        ],
    },

    "Documentation / Medical Necessity": {
        "Documentation requirement": [
            "documentation requirement",
            "documentation requirements",
            "medical documentation",
        ],
        "Clinical criteria": [
            "clinical criteria",
            "coverage criteria",
        ],
        "Medical-necessity tightening": [
            "medical necessity",
            "reasonable and necessary",
            "medical necessity criteria",
        ],
    },

    "Reimbursement / Payment": {
        "Rate change": [
            "rate change",
            "payment rate",
            "reimbursement rate",
        ],
        "Fee schedule": [
            "fee schedule",
            "fee schedules",
        ],
        "Payment rule": [
            "payment rule",
            "payment update",
            "payment changes",
        ],
        "Underpayment": [
            "underpayment",
            "underpaid",
        ],
        "Payment delay": [
            "payment delay",
            "payment delayed",
        ],
        "Modifier payment": [
            "modifier",
            "modifier payment",
        ],
    },

    "Procedure / Device Access": {
        "Procedure coverage": [
            "procedure coverage",
            "covered procedure",
        ],
        "Procedure PA": [
            "procedure prior authorization",
            "procedure authorization",
        ],
        "Procedure documentation": [
            "procedure documentation",
        ],
        "Device coverage": [
            "device coverage",
            "medical device coverage",
        ],
        "Device authorization": [
            "device authorization",
            "device prior authorization",
        ],
    },
}


PAYER_KEYWORDS = {
    "Medicare": [
        "medicare",
        "cms",
    ],
    "Medicare Advantage": [
        "medicare advantage",
        "ma plan",
        "medicare advantage plan",
    ],
    "Medicaid": [
        "medicaid",
    ],
    "UnitedHealthcare": [
        "unitedhealthcare",
        "united healthcare",
        "uhc",
    ],
    "Aetna": [
        "aetna",
    ],
    "BCBS": [
        "blue cross",
        "blue shield",
        "bcbs",
    ],
    "Cigna": [
        "cigna",
    ],
    "Humana": [
        "humana",
    ],
}


PROCEDURE_KEYWORDS = {
    "RFA": [
        "radiofrequency ablation",
        "rfa",
        "radiofrequency",
    ],
    "Facet Joint": [
        "facet joint",
        "facet intervention",
        "medial branch block",
    ],
    "Epidural": [
        "epidural",
        "epidural steroid injection",
        "esi",
    ],
    "Spinal Cord Stimulation": [
        "spinal cord stimulation",
        "spinal cord stimulator",
        "scs",
    ],
    "Peripheral Nerve Stimulation": [
        "peripheral nerve stimulation",
        "peripheral nerve stimulator",
        "pns",
    ],
    "SI Joint": [
        "si joint",
        "sacroiliac",
    ],
    "Kyphoplasty": [
        "kyphoplasty",
    ],
    "Intracept": [
        "intracept",
        "basivertebral",
    ],
}


# ============================================================
# HTTP
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


def fetch(url):
    """
    Fetch a webpage.

    verify=False is intentionally used only because some Medicare
    contractor environments can have certificate-chain problems.

    Production:
        FIX THE CERTIFICATE / CA TRUST
        instead of disabling TLS verification.
    """

    try:
        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            verify=False,
        )

        response.raise_for_status()

        return response.text, response.url

    except Exception as exc:
        print(f"[ERROR] {url}")
        print(f"        {exc}")
        return None, url


# ============================================================
# DATE PARSING
# ============================================================

DATE_PATTERNS = [
    r"\b\d{1,2}/\d{1,2}/\d{4}\b",
    r"\b\d{1,2}-\d{1,2}-\d{4}\b",
    r"\b\d{1,2}\.\d{1,2}\.\d{4}\b",

    r"\b(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|"
    r"Jul|July|Aug|August|Sep|September|Oct|October|Nov|November|"
    r"Dec|December)\s+\d{1,2},\s+\d{4}\b",
]


def parse_date(text):
    if not text:
        return None

    text = " ".join(text.split())

    for pattern in DATE_PATTERNS:

        match = re.search(pattern, text, re.IGNORECASE)

        if not match:
            continue

        value = match.group(0)

        formats = [
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%m.%d.%Y",
            "%B %d, %Y",
            "%b %d, %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                pass

    return None


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):
    if not text:
        return ""

    return " ".join(text.split())


# ============================================================
# PAGE PARSING
# ============================================================

def extract_page_title(soup):
    if soup.title:
        return clean_text(soup.title.get_text(" ", strip=True))

    return None


def extract_main_text(soup):
    """
    Try to get meaningful visible text without navigation clutter.
    """

    for tag in soup([
        "script",
        "style",
        "noscript",
        "svg",
        "header",
        "footer",
        "nav",
    ]):
        tag.decompose()

    return clean_text(
        soup.get_text(" ", strip=True)
    )


# ============================================================
# LINK DISCOVERY
# ============================================================

def discover_links(base_url, html):
    soup = BeautifulSoup(html, "html.parser")

    links = []

    for anchor in soup.find_all("a", href=True):

        href = anchor.get("href", "").strip()

        if not href:
            continue

        url = urljoin(base_url, href)

        title = clean_text(
            anchor.get_text(" ", strip=True)
        )

        links.append({
            "title": title,
            "url": url,
        })

    return links


# ============================================================
# DATE + ARTICLE DETECTION
# ============================================================

def is_probable_article(title, url, surrounding_text=""):
    combined = " ".join([
        title or "",
        url or "",
        surrounding_text or "",
    ]).lower()

    article_words = [
        "news",
        "update",
        "alert",
        "notice",
        "article",
        "policy",
        "prior authorization",
        "claims",
        "billing",
        "coverage",
        "fee schedule",
        "lcd",
        "ncd",
        "reimbursement",
        "modifier",
        "documentation",
    ]

    return any(word in combined for word in article_words)


def discover_dated_items(source_name, page_url, html):
    """
    Generic dated-link discovery.

    This intentionally does NOT assume that every source has the
    same HTML structure.
    """

    soup = BeautifulSoup(html, "html.parser")

    results = []

    for element in soup.find_all(["a", "li", "div", "article"]):

        text = clean_text(
            element.get_text(" ", strip=True)
        )

        if not text:
            continue

        date_value = parse_date(text)

        if not date_value:
            continue

        anchor = element.find("a", href=True)

        if not anchor:
            continue

        href = anchor.get("href", "").strip()

        if not href:
            continue

        url = urljoin(page_url, href)

        title = clean_text(
            anchor.get_text(" ", strip=True)
        )

        if len(title) < 5:
            continue

        if not is_probable_article(title, url, text):
            continue

        results.append({
            "source": source_name,
            "title": title,
            "url": url,
            "published_date": date_value,
        })

    return deduplicate_items(results)


def deduplicate_items(items):
    seen = set()
    output = []

    for item in items:

        key = (
            item.get("url", "").strip(),
            item.get("title", "").strip().lower(),
            item.get("published_date"),
        )

        if key in seen:
            continue

        seen.add(key)
        output.append(item)

    return output


# ============================================================
# SOURCE-SPECIFIC DISCOVERY
# ============================================================

def discover_palmetto():
    print("\n======================================")
    print("PALMETTO")
    print("======================================")

    results = []

    for url in SOURCES["Palmetto"]["start_urls"]:

        print(f"\n[FETCH] {url}")

        html, final_url = fetch(url)

        if not html:
            continue

        items = discover_dated_items(
            "Palmetto",
            final_url,
            html,
        )

        print(f"[FOUND] {len(items)} dated items")

        results.extend(items)

    return deduplicate_items(results)


def discover_cgs():
    print("\n======================================")
    print("CGS")
    print("======================================")

    results = []

    for url in SOURCES["CGS"]["start_urls"]:

        print(f"\n[FETCH] {url}")

        html, final_url = fetch(url)

        if not html:
            continue

        items = discover_dated_items(
            "CGS",
            final_url,
            html,
        )

        print(f"[FOUND] {len(items)} dated items")

        results.extend(items)

    return deduplicate_items(results)


def discover_wps():
    print("\n======================================")
    print("WPS")
    print("======================================")

    results = []

    for url in SOURCES["WPS"]["start_urls"]:

        print(f"\n[FETCH] {url}")

        html, final_url = fetch(url)

        if not html:
            continue

        items = discover_dated_items(
            "WPS",
            final_url,
            html,
        )

        print(f"[FOUND] {len(items)} dated items")

        results.extend(items)

    return deduplicate_items(results)


# ============================================================
# DATE FILTER
# ============================================================

def filter_recent(items):
    cutoff = datetime.now().date() - timedelta(days=DAYS_BACK)

    recent = []

    for item in items:

        date_string = item.get("published_date")

        if not date_string:
            continue

        try:
            item_date = datetime.strptime(
                date_string,
                "%Y-%m-%d"
            ).date()

        except ValueError:
            continue

        if item_date >= cutoff:
            recent.append(item)

    return recent


# ============================================================
# ARTICLE FETCHING
# ============================================================

def fetch_article(item):
    print(
        f"    [ARTICLE] "
        f"{item['title'][:90]}"
    )

    html, final_url = fetch(item["url"])

    if not html:
        return item

    soup = BeautifulSoup(html, "html.parser")

    title = extract_page_title(soup)

    text = extract_main_text(soup)

    item["final_url"] = final_url
    item["page_title"] = title
    item["content"] = text[:15000]

    # Sometimes the article page contains a more accurate date.
    article_date = parse_date(text)

    if article_date:
        item["article_date_detected"] = article_date

    return item


# ============================================================
# KEYWORD MATCHING
# ============================================================

def find_matches(text, dictionary):
    text_lower = text.lower()

    matches = []

    for name, keywords in dictionary.items():

        for keyword in keywords:

            if keyword.lower() in text_lower:
                matches.append(name)
                break

    return list(dict.fromkeys(matches))


def classify_signal(text):
    """
    Return the first strong matching bucket/type.

    Later this can be replaced with a scoring model so one item
    can belong to multiple buckets.
    """

    text_lower = text.lower()

    candidates = []

    for bucket, signal_types in SIGNAL_KEYWORDS.items():

        for signal_type, keywords in signal_types.items():

            hits = 0

            for keyword in keywords:

                if keyword.lower() in text_lower:
                    hits += 1

            if hits > 0:

                candidates.append({
                    "bucket": bucket,
                    "signal_type": signal_type,
                    "hits": hits,
                })

    if not candidates:
        return None, None

    candidates.sort(
        key=lambda x: x["hits"],
        reverse=True,
    )

    best = candidates[0]

    return (
        best["bucket"],
        best["signal_type"],
    )


# ============================================================
# EFFECTIVE DATE DETECTION
# ============================================================

def extract_effective_date(text):
    patterns = [
        r"effective\s+(?:date\s+)?(?:on\s+)?"
        r"([A-Z][a-z]+\s+\d{1,2},\s+\d{4})",

        r"effective\s+(?:date\s+)?(?:on\s+)?"
        r"(\d{1,2}/\d{1,2}/\d{4})",

        r"effective\s+(?:date\s+)?(?:on\s+)?"
        r"(\d{1,2}-\d{1,2}-\d{4})",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:

            value = match.group(1)

            parsed = parse_date(value)

            if parsed:
                return parsed

    return None


# ============================================================
# SIGNAL EXTRACTION
# ============================================================

def extract_signal(item):
    title = item.get("title", "")
    content = item.get("content", "")

    combined = f"{title}. {content}"

    bucket, signal_type = classify_signal(
        combined
    )

    payers = find_matches(
        combined,
        PAYER_KEYWORDS,
    )

    procedures = find_matches(
        combined,
        PROCEDURE_KEYWORDS,
    )

    effective_date = extract_effective_date(
        combined
    )

    if bucket:

        confidence = "Medium"

        # Stronger confidence for explicit operational
        # changes / requirements.
        strong_phrases = [
            "effective",
            "required",
            "new codes",
            "updated",
            "change",
            "denied",
            "rejected",
            "prior authorization",
        ]

        strong_hits = sum(
            phrase in combined.lower()
            for phrase in strong_phrases
        )

        if strong_hits >= 2:
            confidence = "High"

    else:

        confidence = "Low"

    item["signal"] = {
        "status": "candidate" if bucket else "unclassified",
        "bucket": bucket,
        "signal_type": signal_type,
        "payer": payers,
        "procedures": procedures,
        "effective_date": effective_date,
        "confidence": confidence,
    }

    return item


# ============================================================
# MAIN CRAWLER
# ============================================================

def run():

    print("\n")
    print("==============================================")
    print("        SLD MAC CRAWLER")
    print("==============================================")
    print(
        f"Looking back {DAYS_BACK} days"
    )

    all_items = []

    # --------------------------------------------------------
    # DISCOVERY
    # --------------------------------------------------------

    all_items.extend(
        discover_palmetto()
    )

    all_items.extend(
        discover_cgs()
    )

    all_items.extend(
        discover_wps()
    )

    all_items = deduplicate_items(
        all_items
    )

    print("\n======================================")
    print("TOTAL DISCOVERED")
    print("======================================")

    print(
        f"Total dated items: {len(all_items)}"
    )

    # --------------------------------------------------------
    # DATE FILTER
    # --------------------------------------------------------

    recent_items = filter_recent(
        all_items
    )

    print(
        f"Recent items: {len(recent_items)}"
    )

    # --------------------------------------------------------
    # ARTICLE FETCH + SIGNAL EXTRACTION
    # --------------------------------------------------------

    processed = []

    for index, item in enumerate(
        recent_items,
        start=1,
    ):

        print(
            f"\n[{index}/{len(recent_items)}]"
        )

        item = fetch_article(item)

        item = extract_signal(item)

        processed.append(item)

        # Be polite to source servers.
        time.sleep(0.5)

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    processed.sort(
        key=lambda x: (
            x.get("published_date") or "",
            x.get("source") or "",
        ),
        reverse=True,
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    output = {
        "generated_at": datetime.now().isoformat(),
        "days_back": DAYS_BACK,
        "total_discovered": len(all_items),
        "total_recent": len(recent_items),
        "items": processed,
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    candidate_count = sum(
        1
        for item in processed
        if item.get("signal", {}).get("status")
        == "candidate"
    )

    print("\n")
    print("==============================================")
    print("              CRAWL COMPLETE")
    print("==============================================")

    print(
        f"Discovered : {len(all_items)}"
    )

    print(
        f"Recent     : {len(recent_items)}"
    )

    print(
        f"Candidates : {candidate_count}"
    )

    print(
        f"Output     : {OUTPUT_FILE}"
    )

    print("==============================================")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run()