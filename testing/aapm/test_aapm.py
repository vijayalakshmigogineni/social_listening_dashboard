import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re
import time


BASE_URL = "https://painmed.org"
START_URL = "https://painmed.org/"

TOPIC = "prior authorization"

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
# EXTRACT PAGE
# ---------------------------------------------------------

def extract_page(url, html):

    soup = BeautifulSoup(html, "html.parser")

    title = ""

    if soup.title:
        title = clean_text(soup.title.get_text())

    # Remove unnecessary elements
    for tag in soup([
        "script",
        "style",
        "noscript",
        "svg"
    ]):
        tag.decompose()

    # Headings
    headings = []

    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = clean_text(tag.get_text(" ", strip=True))

        if text:
            headings.append(text)

    # Main text
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.body
    )

    content = ""

    if main:
        content = clean_text(
            main.get_text(" ", strip=True)
        )

    return {
        "title": title,
        "url": url,
        "headings": headings,
        "content": content
    }


# ---------------------------------------------------------
# CHECK PRIOR AUTHORIZATION RELEVANCE
# ---------------------------------------------------------

def is_prior_authorization_relevant(page):

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
        "preauthorization",
        "pre-authorization",
        "prior auth",
        "authorization requirement",
        "authorization requirements"
    ]

    matches = []

    for keyword in keywords:
        if keyword in text:
            matches.append(keyword)

    return list(set(matches))


# ---------------------------------------------------------
# EXTRACT RELEVANT SENTENCES
# ---------------------------------------------------------

def extract_evidence(content):

    sentences = re.split(
        r'(?<=[.!?])\s+',
        content
    )

    evidence = []

    keywords = [
        "prior authorization",
        "prior-authorization",
        "preauthorization",
        "pre-authorization",
        "prior auth",
        "authorization requirement",
        "authorization requirements"
    ]

    for sentence in sentences:

        sentence_lower = sentence.lower()

        if any(
            keyword in sentence_lower
            for keyword in keywords
        ):
            evidence.append(
                sentence.strip()
            )

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
        "Aetna",
        "Blue Cross Blue Shield",
        "BCBS",
        "Cigna",
        "Humana"
    ]

    found = []

    for payer in payer_keywords:

        if payer.lower() in text.lower():
            found.append(payer)

    return found


# ---------------------------------------------------------
# EXTRACT PROCEDURES
# ---------------------------------------------------------

def extract_procedures(text):

    procedure_keywords = [
        "facet joint",
        "epidural",
        "radiofrequency ablation",
        "spinal cord stimulation",
        "peripheral nerve stimulation",
        "nerve block",
        "injection",
        "injections"
    ]

    found = []

    for procedure in procedure_keywords:

        if procedure.lower() in text.lower():
            found.append(procedure)

    return found


# ---------------------------------------------------------
# CLASSIFY PA SIGNAL
# ---------------------------------------------------------

def classify_signal(text):

    text = text.lower()

    if any(
        x in text
        for x in [
            "new prior authorization",
            "new authorization requirement",
            "authorization now required",
            "requires prior authorization"
        ]
    ):
        return "PA requirement"

    if any(
        x in text
        for x in [
            "prior authorization delay",
            "authorization delay",
            "turnaround",
            "waiting for authorization"
        ]
    ):
        return "PA turnaround"

    if any(
        x in text
        for x in [
            "authorization denied",
            "prior authorization denial",
            "authorization denial"
        ]
    ):
        return "PA approval/denial"

    if any(
        x in text
        for x in [
            "documentation",
            "clinical documentation",
            "additional information"
        ]
    ):
        return "PA documentation"

    if any(
        x in text
        for x in [
            "peer-to-peer",
            "peer to peer"
        ]
    ):
        return "Peer-to-peer"

    return "PA-related discussion"


# ---------------------------------------------------------
# DISCOVER LINKS
# ---------------------------------------------------------

def discover_links(html, current_url):

    soup = BeautifulSoup(html, "html.parser")

    links = set()

    for a in soup.find_all("a", href=True):

        href = a["href"]

        absolute_url = urljoin(
            current_url,
            href
        )

        # Only keep AAPM pages
        if absolute_url.startswith(BASE_URL):

            # Remove fragments
            absolute_url = absolute_url.split("#")[0]

            links.add(absolute_url)

    return links


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("\nAAPM PRIOR AUTHORIZATION TEST")
    print("=" * 60)

    html = fetch_page(START_URL)

    if not html:
        print("Could not fetch AAPM homepage.")
        return

    links = discover_links(
        html,
        START_URL
    )

    print(f"\nDiscovered {len(links)} AAPM links.")

    results = []

    # Test discovered pages
    for index, url in enumerate(links):

        print(
            f"\n[{index + 1}/{len(links)}] Checking..."
        )

        page_html = fetch_page(url)

        if not page_html:
            continue

        page = extract_page(
            url,
            page_html
        )

        matches = is_prior_authorization_relevant(
            page
        )

        if not matches:
            continue

        print("  >>> PRIOR AUTHORIZATION MATCH")

        evidence = extract_evidence(
            page["content"]
        )

        signal_text = " ".join(evidence)

        record = {
            "source": "AAPM",
            "source_type": "pain_medicine_professional_organization",

            "topic": "Prior Authorization",

            "title": page["title"],
            "url": page["url"],

            "signal_type": classify_signal(
                signal_text
            ),

            "topic_matches": matches,

            "payer_mentions": extract_payers(
                page["content"]
            ),

            "procedure_mentions": extract_procedures(
                page["content"]
            ),

            "evidence": evidence,

            "headings": page["headings"],

            "content": page["content"]
        }

        results.append(record)

        # Don't overload the website
        time.sleep(1)

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    output_file = "aapm_prior_authorization.json"

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

    print("\n" + "=" * 60)

    print(
        f"Found {len(results)} Prior Authorization items."
    )

    print(
        f"Saved to: {output_file}"
    )


if __name__ == "__main__":
    main()