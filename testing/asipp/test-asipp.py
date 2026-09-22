import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import json
import re
import time


# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://asipp.org"

SOURCE_NAME = "ASIPP"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    )
}

# Pages we want to inspect
START_URLS = [
    "https://asipp.org/",
    "https://asipp.org/news/",
    "https://asipp.org/advocacy/",
    "https://asipp.org/advocacy-news/",
    "https://asipp.org/health-policy-lettersarticles/",
    "https://asipp.org/guidelines/",
    "https://asipp.org/asipp_library/",
]


# ============================================================
# FETCH PAGE
# ============================================================

def fetch_page(url):

    print(f"Fetching: {url}")

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        print(
            f"Status: {response.status_code} | "
            f"Final URL: {response.url}"
        )

        if response.status_code != 200:
            return None

        return response.text

    except Exception as e:

        print(f"ERROR: {e}")
        return None


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# EXTRACT DATE
# ============================================================

def extract_date(element):

    if not element:
        return None

    text = element.get_text(" ", strip=True)

    # Common date patterns
    patterns = [

        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
        r"\s+\d{1,2},\s+\d{4}",

        r"\b\d{1,2}/\d{1,2}/\d{4}\b",

        r"\b\d{4}-\d{2}-\d{2}\b",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(0)

    return None


# ============================================================
# CLASSIFY LINK
# ============================================================

def classify_link(title, url):

    text = f"{title} {url}".lower()

    if ".pdf" in text:
        return "document"

    if any(
        word in text
        for word in [
            "guideline",
            "guidelines"
        ]
    ):
        return "guideline"

    if any(
        word in text
        for word in [
            "advocacy",
            "policy",
            "cms",
            "medicare",
            "payment",
            "reimbursement"
        ]
    ):
        return "policy"

    if any(
        word in text
        for word in [
            "news",
            "update",
            "announcement"
        ]
    ):
        return "news"

    if any(
        word in text
        for word in [
            "library",
            "article",
            "publication"
        ]
    ):
        return "publication"

    return "other"


# ============================================================
# EXTRACT ALL LINKS
# ============================================================

def extract_links(html, page_url):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    records = []

    seen = set()

    for a in soup.find_all("a", href=True):

        href = a.get("href", "").strip()

        if not href:
            continue

        full_url = urljoin(
            page_url,
            href
        )

        # Only ASIPP content
        if not full_url.startswith(BASE_URL):
            continue

        title = clean_text(
            a.get_text(" ", strip=True)
        )

        # Ignore empty links
        if not title:
            continue

        key = (
            title.lower(),
            full_url
        )

        if key in seen:
            continue

        seen.add(key)

        category = classify_link(
            title,
            full_url
        )

        records.append({
            "title": title,
            "url": full_url,
            "category": category,
            "source_page": page_url
        })

    return records


# ============================================================
# EXTRACT PAGE CONTENT
# ============================================================

def extract_page_content(
    html,
    url
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # Remove unnecessary elements
    for tag in soup([
        "script",
        "style",
        "noscript",
        "svg",
        "nav",
        "footer"
    ]):

        tag.decompose()

    # Title
    title = ""

    if soup.title:
        title = clean_text(
            soup.title.get_text()
        )

    # Headings
    headings = []

    for tag in soup.find_all([
        "h1",
        "h2",
        "h3",
        "h4"
    ]):

        text = clean_text(
            tag.get_text(" ", strip=True)
        )

        if text:
            headings.append({
                "level": tag.name,
                "text": text
            })

    # Main text
    text = soup.get_text(
        "\n",
        strip=True
    )

    lines = []

    for line in text.splitlines():

        line = clean_text(line)

        if line:
            lines.append(line)

    page_text = "\n".join(lines)

    # Date
    date = None

    for tag in soup.find_all(
        ["time", "span", "div", "p"]
    ):

        possible_date = extract_date(tag)

        if possible_date:

            date = possible_date
            break

    return {
        "title": title,
        "url": url,
        "date": date,
        "headings": headings,
        "text": page_text
    }


# ============================================================
# EXTRACT SIGNAL TOPICS
# ============================================================

def detect_topics(text):

    text_lower = text.lower()

    topics = []

    topic_keywords = {

        "prior_authorization": [
            "prior authorization",
            "prior auth",
            "authorization"
        ],

        "coverage_policy": [
            "coverage",
            "coverage policy",
            "medical policy"
        ],

        "medical_necessity": [
            "medical necessity",
            "medical-necessity"
        ],

        "documentation": [
            "documentation",
            "medical records",
            "records requirement"
        ],

        "reimbursement": [
            "reimbursement",
            "payment",
            "payment rate",
            "conversion factor",
            "fee schedule"
        ],

        "coding": [
            "coding",
            "cpt",
            "modifier",
            "billing"
        ],

        "medicare": [
            "medicare",
            "cms"
        ],

        "medicare_advantage": [
            "medicare advantage",
            "ma plan"
        ],

        "denials": [
            "denial",
            "denials",
            "claim denial"
        ],

        "appeals": [
            "appeal",
            "appeals"
        ],

        "pain_procedures": [
            "facet",
            "epidural",
            "radiofrequency",
            "rfa",
            "spinal cord stimulation",
            "peripheral nerve stimulation",
            "pns",
            "pain procedure"
        ],

        "quality_programs": [
            "mips",
            "quality payment program",
            "qpp"
        ]
    }

    for topic, keywords in topic_keywords.items():

        for keyword in keywords:

            if keyword in text_lower:

                topics.append(topic)
                break

    return topics


# ============================================================
# EXTRACT PAYER MENTIONS
# ============================================================

def detect_payers(text):

    text_lower = text.lower()

    payer_keywords = {

        "CMS": [
            "cms",
            "centers for medicare"
        ],

        "Medicare": [
            "medicare"
        ],

        "Medicare Advantage": [
            "medicare advantage"
        ],

        "UnitedHealthcare": [
            "unitedhealthcare",
            "united healthcare",
            "uhc"
        ],

        "Aetna": [
            "aetna"
        ],

        "BCBS": [
            "blue cross",
            "blue shield",
            "bcbs"
        ],

        "Cigna": [
            "cigna"
        ],

        "Humana": [
            "humana"
        ]
    }

    payers = []

    for payer, keywords in payer_keywords.items():

        for keyword in keywords:

            if keyword in text_lower:

                payers.append(payer)
                break

    return payers


# ============================================================
# EXTRACT PROCEDURE TERMS
# ============================================================

def detect_procedures(text):

    text_lower = text.lower()

    procedures = {

        "Facet Joint": [
            "facet joint",
            "facet"
        ],

        "Epidural": [
            "epidural",
            "esi"
        ],

        "Radiofrequency Ablation": [
            "radiofrequency",
            "rfa"
        ],

        "Spinal Cord Stimulation": [
            "spinal cord stimulation",
            "scs"
        ],

        "Peripheral Nerve Stimulation": [
            "peripheral nerve stimulation",
            "pns"
        ],

        "Injections": [
            "injection",
            "injections"
        ]
    }

    found = []

    for procedure, keywords in procedures.items():

        for keyword in keywords:

            if keyword in text_lower:

                found.append(procedure)
                break

    return found


# ============================================================
# BUILD STRUCTURED RECORD
# ============================================================

def build_record(
    page_data,
    category
):

    text = page_data["text"]

    return {

        "source": SOURCE_NAME,

        "source_type": "professional_pain_specialty",

        "content_type": category,

        "title": page_data["title"],

        "url": page_data["url"],

        "published_date": page_data["date"],

        "topics": detect_topics(text),

        "payer_mentions": detect_payers(text),

        "procedure_mentions": detect_procedures(text),

        "headings": page_data["headings"],

        "content": text

    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("ASIPP STRUCTURED SCRAPER")
    print("=" * 70)

    all_links = []
    pages = []

    # --------------------------------------------------------
    # STEP 1: Fetch starting pages
    # --------------------------------------------------------

    for url in START_URLS:

        html = fetch_page(url)

        if not html:
            continue

        page_data = extract_page_content(
            html,
            url
        )

        pages.append(page_data)

        links = extract_links(
            html,
            url
        )

        all_links.extend(links)

        print(
            f"Found {len(links)} ASIPP links"
        )

        time.sleep(1)

    # --------------------------------------------------------
    # Remove duplicate links
    # --------------------------------------------------------

    unique_links = {}

    for link in all_links:

        unique_links[link["url"]] = link

    all_links = list(
        unique_links.values()
    )

    print("\n" + "=" * 70)

    print(
        f"Total unique ASIPP links found: "
        f"{len(all_links)}"
    )

    # --------------------------------------------------------
    # STEP 2: Display useful links
    # --------------------------------------------------------

    print("\nPotential useful ASIPP content:")

    useful_links = []

    for link in all_links:

        if link["category"] in [
            "news",
            "policy",
            "guideline",
            "document",
            "publication"
        ]:

            useful_links.append(link)

    for link in useful_links[:50]:

        print(
            f"\n[{link['category']}]"
        )

        print(
            f"Title: {link['title']}"
        )

        print(
            f"URL: {link['url']}"
        )

    # --------------------------------------------------------
    # STEP 3: Save link inventory
    # --------------------------------------------------------

    with open(
        "asipp_link_inventory.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            all_links,
            f,
            indent=2,
            ensure_ascii=False
        )

    # --------------------------------------------------------
    # STEP 4: Build structured records
    # --------------------------------------------------------

    structured_records = []

    for page in pages:

        # Determine page category
        category = classify_link(
            page["title"],
            page["url"]
        )

        record = build_record(
            page,
            category
        )

        structured_records.append(
            record
        )

    # --------------------------------------------------------
    # STEP 5: Save structured output
    # --------------------------------------------------------

    output = {

        "source": SOURCE_NAME,

        "source_url": BASE_URL,

        "scraped_at": datetime.utcnow().isoformat(),

        "pages_checked": len(
            START_URLS
        ),

        "pages_successfully_fetched": len(
            pages
        ),

        "total_links_found": len(
            all_links
        ),

        "records": structured_records
    }

    with open(
        "asipp_structured_output.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )

    print("\n" + "=" * 70)

    print("DONE")

    print("=" * 70)

    print(
        "\nCreated:"
    )

    print(
        "1. asipp_link_inventory.json"
    )

    print(
        "2. asipp_structured_output.json"
    )


if __name__ == "__main__":
    main()