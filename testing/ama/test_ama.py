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

BASE_URL = "https://www.ama-assn.org"

SOURCE_NAME = "AMA"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    )
}

START_URLS = [
    "https://www.ama-assn.org/",
    "https://www.ama-assn.org/practice-management/prior-authorization",
]


# ============================================================
# FETCH
# ============================================================

def fetch_page(url):

    print(f"\nFetching: {url}")

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        print("Status:", response.status_code)
        print("Final URL:", response.url)

        if response.status_code != 200:
            return None

        return response.text

    except Exception as e:

        print("ERROR:", e)
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
# DATE EXTRACTION
# ============================================================

def extract_date(soup):

    # First look for <time>
    for tag in soup.find_all("time"):

        value = (
            tag.get("datetime")
            or tag.get_text(" ", strip=True)
        )

        if value:
            return clean_text(value)

    # Look for common date patterns in page text
    text = soup.get_text(" ", strip=True)

    patterns = [
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}",
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b"
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
# CLASSIFY CONTENT
# ============================================================

def classify_content(title, url):

    text = f"{title} {url}".lower()

    if "prior-authorization" in text:
        return "prior_authorization"

    if "advocacy" in text:
        return "advocacy"

    if "policy" in text:
        return "policy"

    if "practice-management" in text:
        return "practice_management"

    if "news" in text:
        return "news"

    if "article" in text:
        return "article"

    return "other"


# ============================================================
# EXTRACT LINKS
# ============================================================

def extract_links(html, page_url):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    links = []
    seen = set()

    for a in soup.find_all("a", href=True):

        href = a.get("href", "").strip()

        if not href:
            continue

        full_url = urljoin(
            page_url,
            href
        )

        # Keep AMA links only
        if not full_url.startswith(BASE_URL):
            continue

        title = clean_text(
            a.get_text(" ", strip=True)
        )

        if not title:
            continue

        key = (
            title.lower(),
            full_url
        )

        if key in seen:
            continue

        seen.add(key)

        links.append({
            "title": title,
            "url": full_url,
            "content_type": classify_content(
                title,
                full_url
            ),
            "source_page": page_url
        })

    return links


# ============================================================
# EXTRACT HEADINGS
# ============================================================

def extract_headings(soup):

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

    return headings


# ============================================================
# EXTRACT MAIN CONTENT
# ============================================================

def extract_content(html, url):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # Save title before removing elements
    title = ""

    if soup.title:
        title = clean_text(
            soup.title.get_text()
        )

    date = extract_date(soup)

    headings = extract_headings(soup)

    # Remove unnecessary page elements
    for tag in soup([
        "script",
        "style",
        "noscript",
        "svg",
        "nav",
        "footer"
    ]):

        tag.decompose()

    # Try common article/content containers first
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.body
    )

    if main:

        text = main.get_text(
            "\n",
            strip=True
        )

    else:

        text = soup.get_text(
            "\n",
            strip=True
        )

    lines = []

    for line in text.splitlines():

        line = clean_text(line)

        if line:
            lines.append(line)

    return {
        "title": title,
        "url": url,
        "published_date": date,
        "headings": headings,
        "content": "\n".join(lines)
    }


# ============================================================
# TOPIC DETECTION
# ============================================================

def detect_topics(text):

    text_lower = text.lower()

    topic_keywords = {

        "prior_authorization": [
            "prior authorization",
            "prior auth",
            "authorization"
        ],

        "documentation": [
            "documentation",
            "medical records"
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

        "medical_necessity": [
            "medical necessity",
            "medical-necessity"
        ],

        "coverage_policy": [
            "coverage",
            "coverage policy",
            "medical policy"
        ],

        "reimbursement": [
            "reimbursement",
            "payment",
            "payment rate",
            "fee schedule"
        ],

        "coding": [
            "coding",
            "cpt",
            "modifier",
            "billing"
        ],

        "payer_burden": [
            "payer burden",
            "administrative burden",
            "insurance burden"
        ],

        "health_policy": [
            "health policy",
            "policy change",
            "regulation"
        ],

        "telehealth": [
            "telehealth",
            "telemedicine"
        ],

        "medicare": [
            "medicare",
            "cms"
        ],

        "medicaid": [
            "medicaid"
        ]
    }

    found = []

    for topic, keywords in topic_keywords.items():

        for keyword in keywords:

            if keyword in text_lower:

                found.append(topic)
                break

    return found


# ============================================================
# PAYER DETECTION
# ============================================================

def detect_payers(text):

    text_lower = text.lower()

    payer_keywords = {

        "CMS": [
            "cms"
        ],

        "Medicare": [
            "medicare"
        ],

        "Medicare Advantage": [
            "medicare advantage"
        ],

        "Medicaid": [
            "medicaid"
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

    found = []

    for payer, keywords in payer_keywords.items():

        for keyword in keywords:

            if keyword in text_lower:

                found.append(payer)
                break

    return found


# ============================================================
# PROCEDURE DETECTION
# ============================================================

def detect_procedures(text):

    text_lower = text.lower()

    procedure_keywords = {

        "Facet Joint": [
            "facet joint",
            "facet"
        ],

        "Epidural": [
            "epidural"
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
        ]
    }

    found = []

    for procedure, keywords in procedure_keywords.items():

        for keyword in keywords:

            if keyword in text_lower:

                found.append(procedure)
                break

    return found


# ============================================================
# BUILD STRUCTURED RECORD
# ============================================================

def build_record(page_data):

    content = page_data["content"]

    return {

        "source": SOURCE_NAME,

        "source_type": "medical_professional_organization",

        "content_type": classify_content(
            page_data["title"],
            page_data["url"]
        ),

        "title": page_data["title"],

        "url": page_data["url"],

        "published_date": page_data[
            "published_date"
        ],

        "topics": detect_topics(
            content
        ),

        "payer_mentions": detect_payers(
            content
        ),

        "procedure_mentions": detect_procedures(
            content
        ),

        "headings": page_data[
            "headings"
        ],

        "content": content
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("AMA STRUCTURED TEST SCRAPER")
    print("=" * 70)

    all_links = []
    page_records = []

    # --------------------------------------------------------
    # FETCH STARTING PAGES
    # --------------------------------------------------------

    for url in START_URLS:

        html = fetch_page(url)

        if not html:
            continue

        page_data = extract_content(
            html,
            url
        )

        page_records.append(
            page_data
        )

        links = extract_links(
            html,
            url
        )

        all_links.extend(
            links
        )

        print(
            f"Links found: {len(links)}"
        )

        time.sleep(1)

    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    unique_links = {}

    for link in all_links:

        unique_links[
            link["url"]
        ] = link

    all_links = list(
        unique_links.values()
    )

    # --------------------------------------------------------
    # DISPLAY USEFUL LINKS
    # --------------------------------------------------------

    print("\n" + "=" * 70)

    print(
        "USEFUL AMA LINKS"
    )

    print("=" * 70)

    for link in all_links[:50]:

        print(
            f"\n[{link['content_type']}]"
        )

        print(
            f"Title: {link['title']}"
        )

        print(
            f"URL: {link['url']}"
        )

    # --------------------------------------------------------
    # BUILD STRUCTURED DATA
    # --------------------------------------------------------

    records = []

    for page in page_records:

        records.append(
            build_record(page)
        )

    # --------------------------------------------------------
    # FINAL OUTPUT
    # --------------------------------------------------------

    output = {

        "source": SOURCE_NAME,

        "source_url": BASE_URL,

        "scraped_at": datetime.utcnow().isoformat(),

        "pages_checked": len(
            START_URLS
        ),

        "pages_fetched": len(
            page_records
        ),

        "total_unique_links": len(
            all_links
        ),

        "records": records,

        "link_inventory": all_links
    }

    # --------------------------------------------------------
    # SAVE JSON
    # --------------------------------------------------------

    with open(
        "ama_structured_output.json",
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
        "\nSaved:"
    )

    print(
        "ama_structured_output.json"
    )


if __name__ == "__main__":
    main()