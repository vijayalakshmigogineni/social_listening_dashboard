import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re
import time


BASE_URL = "https://www.hfma.org"
START_URL = "https://www.hfma.org/"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# ---------------------------------------------------------
# FETCH PAGE
# ---------------------------------------------------------

def fetch_page(url):

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        print(f"{response.status_code} -> {url}")

        if response.status_code == 200:
            return response.text

    except Exception as e:
        print(f"ERROR: {url}")
        print(e)

    return None


# ---------------------------------------------------------
# CLEAN TEXT
# ---------------------------------------------------------

def clean_text(text):

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ---------------------------------------------------------
# EXTRACT PAGE CONTENT
# ---------------------------------------------------------

def extract_page(url, html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    title = ""

    if soup.title:
        title = clean_text(
            soup.title.get_text()
        )

    # Remove unnecessary elements
    for tag in soup([
        "script",
        "style",
        "noscript",
        "svg"
    ]):
        tag.decompose()

    # Extract headings
    headings = []

    for tag in soup.find_all([
        "h1",
        "h2",
        "h3"
    ]):

        text = clean_text(
            tag.get_text(" ", strip=True)
        )

        if text:
            headings.append(text)

    # Main content
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.body
    )

    content = ""

    if main:
        content = clean_text(
            main.get_text(
                " ",
                strip=True
            )
        )

    return {
        "title": title,
        "url": url,
        "headings": headings,
        "content": content
    }


# ---------------------------------------------------------
# PRIOR AUTHORIZATION KEYWORDS
# ---------------------------------------------------------

def find_pa_matches(page):

    text = (
        page["title"]
        + " "
        + " ".join(page["headings"])
        + " "
        + page["content"]
    ).lower()

    keywords = [

        "prior authorization",

        "prior-authorization",

        "prior auth",

        "preauthorization",

        "pre-authorization",

        "authorization requirement",

        "authorization requirements",

        "authorization process",

        "authorization delay",

        "authorization denial"
    ]

    matches = []

    for keyword in keywords:

        if keyword in text:
            matches.append(keyword)

    return list(set(matches))


# ---------------------------------------------------------
# EXTRACT PA EVIDENCE
# ---------------------------------------------------------

def extract_evidence(content):

    sentences = re.split(
        r'(?<=[.!?])\s+',
        content
    )

    keywords = [

        "prior authorization",

        "prior-authorization",

        "prior auth",

        "preauthorization",

        "pre-authorization",

        "authorization requirement",

        "authorization requirements",

        "authorization process",

        "authorization delay",

        "authorization denial"
    ]

    evidence = []

    for sentence in sentences:

        sentence_lower = sentence.lower()

        if any(
            keyword in sentence_lower
            for keyword in keywords
        ):

            sentence = sentence.strip()

            if sentence:
                evidence.append(sentence)

    return evidence[:10]


# ---------------------------------------------------------
# EXTRACT PAYERS
# ---------------------------------------------------------

def extract_payers(text):

    payer_keywords = [

        "Medicare",

        "Medicare Advantage",

        "Medicaid",

        "UnitedHealthcare",

        "United HealthCare",

        "Aetna",

        "Blue Cross Blue Shield",

        "BCBS",

        "Cigna",

        "Humana",

        "Anthem",

        "Centene",

        "Elevance"
    ]

    found = []

    text_lower = text.lower()

    for payer in payer_keywords:

        if payer.lower() in text_lower:
            found.append(payer)

    return list(set(found))


# ---------------------------------------------------------
# EXTRACT RCM / PA TOPICS
# ---------------------------------------------------------

def extract_topics(text):

    topic_keywords = {

        "prior_authorization":
            [
                "prior authorization",
                "prior auth"
            ],

        "documentation":
            [
                "documentation",
                "clinical documentation"
            ],

        "denials":
            [
                "denial",
                "denials"
            ],

        "appeals":
            [
                "appeal",
                "appeals"
            ],

        "medical_necessity":
            [
                "medical necessity",
                "medically necessary"
            ],

        "reimbursement":
            [
                "reimbursement",
                "payment",
                "underpayment"
            ],

        "claims":
            [
                "claim",
                "claims"
            ],

        "revenue_cycle":
            [
                "revenue cycle",
                "revenue cycle management",
                "RCM"
            ]
    }

    text_lower = text.lower()

    found = []

    for topic, keywords in topic_keywords.items():

        if any(
            keyword.lower() in text_lower
            for keyword in keywords
        ):
            found.append(topic)

    return found


# ---------------------------------------------------------
# CLASSIFY PA SIGNAL
# ---------------------------------------------------------

def classify_signal(text):

    text_lower = text.lower()

    if any(
        phrase in text_lower
        for phrase in [
            "new prior authorization",
            "new authorization requirement",
            "authorization now required",
            "requires prior authorization"
        ]
    ):
        return "PA requirement"

    if any(
        phrase in text_lower
        for phrase in [
            "authorization delay",
            "prior authorization delay",
            "turnaround",
            "waiting for authorization"
        ]
    ):
        return "PA turnaround"

    if any(
        phrase in text_lower
        for phrase in [
            "authorization denial",
            "prior authorization denial"
        ]
    ):
        return "PA approval/denial"

    if any(
        phrase in text_lower
        for phrase in [
            "documentation requirement",
            "documentation requirements",
            "additional information"
        ]
    ):
        return "PA documentation"

    if any(
        phrase in text_lower
        for phrase in [
            "peer-to-peer",
            "peer to peer"
        ]
    ):
        return "Peer-to-peer"

    return "PA-related discussion"


# ---------------------------------------------------------
# DISCOVER HFMA LINKS
# ---------------------------------------------------------

def discover_links(html, current_url):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    links = set()

    for a in soup.find_all(
        "a",
        href=True
    ):

        href = a["href"]

        absolute_url = urljoin(
            current_url,
            href
        )

        if absolute_url.startswith(
            BASE_URL
        ):

            absolute_url = absolute_url.split(
                "#"
            )[0]

            links.add(absolute_url)

    return links


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print()
    print("=" * 60)
    print("HFMA PRIOR AUTHORIZATION TEST")
    print("=" * 60)

    html = fetch_page(
        START_URL
    )

    if not html:

        print(
            "Could not fetch HFMA homepage."
        )

        return

    links = discover_links(
        html,
        START_URL
    )

    print()
    print(
        f"Discovered {len(links)} HFMA links."
    )

    results = []

    # Limit initial test
    test_links = list(links)[:100]

    for index, url in enumerate(
        test_links
    ):

        print(
            f"\n[{index + 1}/{len(test_links)}] Checking..."
        )

        page_html = fetch_page(
            url
        )

        if not page_html:
            continue

        page = extract_page(
            url,
            page_html
        )

        matches = find_pa_matches(
            page
        )

        if not matches:

            continue

        print(
            "  >>> PRIOR AUTHORIZATION MATCH"
        )

        evidence = extract_evidence(
            page["content"]
        )

        # Use only evidence for signal classification
        signal_text = " ".join(
            evidence
        )

        record = {

            "source": "HFMA",

            "source_type":
                "healthcare_financial_management_association",

            "topic":
                "Prior Authorization",

            "title":
                page["title"],

            "url":
                page["url"],

            "signal_type":
                classify_signal(
                    signal_text
                ),

            "topic_matches":
                matches,

            "topics":
                extract_topics(
                    page["content"]
                ),

            "payer_mentions":
                extract_payers(
                    page["content"]
                ),

            "evidence":
                evidence,

            "headings":
                page["headings"],

            "content":
                page["content"]
        }

        results.append(
            record
        )

        time.sleep(1)

    # -----------------------------------------------------
    # SAVE JSON
    # -----------------------------------------------------

    output_file = (
        "hfma_prior_authorization.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 60)

    print(
        f"Found {len(results)} Prior Authorization items."
    )

    print(
        f"Saved to: {output_file}"
    )


if __name__ == "__main__":
    main()