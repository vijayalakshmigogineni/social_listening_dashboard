import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re
import time


# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://www.mgma.com"
LISTING_URL = "https://www.mgma.com/mgma-stat"

OUTPUT_FILE = "mgma_stat_articles_structured.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}


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

        response.raise_for_status()

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

    return re.sub(r"\s+", " ", text).strip()


# ============================================================
# GET ARTICLE LINKS
# ============================================================

def get_article_links(html):

    soup = BeautifulSoup(html, "html.parser")

    links = []

    # Try normal HTML links
    for a in soup.find_all("a", href=True):

        href = a["href"]

        if "/mgma-stat/" in href:

            url = urljoin(BASE_URL, href)

            if url not in links:
                links.append(url)

    # If MGMA does not expose links in normal HTML,
    # search the raw HTML
    if not links:

        matches = re.findall(
            r'https?://www\.mgma\.com/mgma-stat/[^"\']+',
            html
        )

        for url in matches:

            url = url.split("?")[0]

            if url not in links:
                links.append(url)

    return links


# ============================================================
# EXTRACT ARTICLE
# ============================================================

def extract_article(url, html):

    soup = BeautifulSoup(html, "html.parser")

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    h1 = soup.find("h1")

    title = clean_text(
        h1.get_text(" ", strip=True)
    ) if h1 else None


    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    published_date = None

    date_tag = soup.select_one(
        "time.article-header__date"
    )

    if date_tag:

        published_date = date_tag.get("datetime")

        if published_date:

            match = re.search(
                r"\d{4}-\d{2}-\d{2}",
                published_date
            )

            if match:
                published_date = match.group(0)

        else:
            published_date = clean_text(
                date_tag.get_text(" ", strip=True)
            )


    # --------------------------------------------------------
    # AUTHOR
    # --------------------------------------------------------

    author = None

    written_by = soup.find(
        string=re.compile(
            "Written By",
            re.IGNORECASE
        )
    )

    if written_by:

        parent = written_by.parent

        link = parent.find_next("a")

        if link:

            author = clean_text(
                link.get_text(" ", strip=True)
            )

    # Fallback
    if not author:

        if "MGMA Revenue Cycle Insights" in soup.get_text():

            author = "MGMA Revenue Cycle Insights"


    # --------------------------------------------------------
    # DESCRIPTION
    # --------------------------------------------------------

    description = None

    meta = soup.find(
        "meta",
        attrs={"name": "description"}
    )

    if meta:

        description = clean_text(
            meta.get("content", "")
        )


    # --------------------------------------------------------
    # MAIN ARTICLE
    # --------------------------------------------------------

    main = soup.find("main")

    if not main:
        main = soup

    # Remove unwanted elements
    for tag in main.find_all(
        ["script", "style", "nav", "footer", "header"]
    ):
        tag.decompose()


    # --------------------------------------------------------
    # ARTICLE TEXT
    # --------------------------------------------------------

    paragraphs = []

    for element in main.find_all(
        ["p", "li"]
    ):

        text = clean_text(
            element.get_text(" ", strip=True)
        )

        if text and text not in paragraphs:

            paragraphs.append(text)

    article_text = "\n".join(paragraphs)


    # --------------------------------------------------------
    # HEADINGS
    # --------------------------------------------------------

    headings = []

    for tag in main.find_all(
        ["h1", "h2", "h3"]
    ):

        text = clean_text(
            tag.get_text(" ", strip=True)
        )

        if text:

            headings.append(text)


    # --------------------------------------------------------
    # POLL INFORMATION
    # --------------------------------------------------------

    poll = extract_poll(article_text)


    # --------------------------------------------------------
    # PAYER MENTIONS
    # --------------------------------------------------------

    payers = [
        "Aetna",
        "Cigna",
        "UnitedHealthcare",
        "UHC",
        "Humana",
        "Medicare",
        "Medicaid",
        "Medicare Advantage",
        "Blue Cross Blue Shield",
        "BCBS",
        "Anthem",
        "Elevance",
        "Molina",
        "Centene",
        "Kaiser Permanente"
    ]

    payer_mentions = []

    for payer in payers:

        if payer.lower() in article_text.lower():

            if payer not in payer_mentions:
                payer_mentions.append(payer)


    # --------------------------------------------------------
    # OPERATIONAL TOPICS
    # --------------------------------------------------------

    topic_keywords = {

        "prior_authorization": [
            "prior authorization",
            "prior auth"
        ],

        "denials": [
            "denial",
            "denials",
            "denied"
        ],

        "appeals": [
            "appeal",
            "appeals"
        ],

        "documentation": [
            "documentation",
            "document"
        ],

        "peer_to_peer": [
            "peer-to-peer",
            "peer to peer"
        ],

        "payer_portals": [
            "payer portal",
            "payer portals"
        ],

        "eligibility": [
            "eligibility"
        ],

        "reimbursement": [
            "reimbursement",
            "payment",
            "payments"
        ],

        "accounts_receivable": [
            "a/r",
            "accounts receivable"
        ],

        "coding": [
            "coding",
            "cpt",
            "modifier"
        ],

        "medical_necessity": [
            "medical necessity"
        ],

        "workflow": [
            "workflow",
            "workflows"
        ],

        "staff_workload": [
            "workload",
            "staffing"
        ]
    }

    operational_topics = []

    article_lower = article_text.lower()

    for topic, keywords in topic_keywords.items():

        for keyword in keywords:

            if keyword.lower() in article_lower:

                operational_topics.append(topic)
                break


    # --------------------------------------------------------
    # RELATED ARTICLES
    # --------------------------------------------------------

    related_articles = []

    for a in soup.find_all("a", href=True):

        href = a["href"]

        if "/mgma-stat/" not in href:
            continue

        related_url = urljoin(
            BASE_URL,
            href
        )

        if related_url == url:
            continue

        related_title = clean_text(
            a.get_text(" ", strip=True)
        )

        if not related_title:
            continue

        item = {
            "title": related_title,
            "url": related_url
        }

        if item not in related_articles:

            related_articles.append(item)


    # --------------------------------------------------------
    # FINAL ARTICLE OBJECT
    # --------------------------------------------------------

    return {

        "source": "MGMA",

        "source_type": "MGMA Stat",

        "title": title,

        "url": url,

        "published_date": published_date,

        "author": author,

        "description": description,

        "poll": poll,

        "payer_mentions": payer_mentions,

        "operational_topics": operational_topics,

        "headings": headings,

        "article_text": article_text,

        "related_articles": related_articles
    }


# ============================================================
# POLL EXTRACTION
# ============================================================

def extract_poll(text):

    result = {
        "detected": False,
        "poll_date": None,
        "respondents": None,
        "results": []
    }

    if not text:
        return result


    # Check whether article contains poll information

    poll_words = [
        "MGMA Stat poll",
        "MGMA poll",
        "poll",
        "respondents",
        "applicable responses"
    ]

    lower_text = text.lower()

    if not any(
        word.lower() in lower_text
        for word in poll_words
    ):
        return result


    result["detected"] = True


    # --------------------------------------------------------
    # POLL DATE
    # --------------------------------------------------------

    date_pattern = re.compile(
        r"(?:poll|MGMA Stat poll).*?"
        r"("
        r"(?:January|February|March|April|May|June|"
        r"July|August|September|October|November|December)"
        r"\s+\d{1,2},\s+\d{4}"
        r")",
        re.IGNORECASE
    )

    match = date_pattern.search(text)

    if match:

        result["poll_date"] = match.group(1)


    # --------------------------------------------------------
    # RESPONDENTS
    # --------------------------------------------------------

    respondent_patterns = [
        r"(\d[\d,]*)\s+applicable responses",
        r"(\d[\d,]*)\s+respondents",
        r"(\d[\d,]*)\s+responses"
    ]

    for pattern in respondent_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            result["respondents"] = int(
                match.group(1).replace(",", "")
            )

            break


    # --------------------------------------------------------
    # PERCENTAGES
    # --------------------------------------------------------

    percentage_pattern = re.compile(
        r"(\d{1,3})%\s+"
        r"([^.;\n]{1,80})",
        re.IGNORECASE
    )

    matches = percentage_pattern.findall(text)

    seen = set()

    for percentage, answer in matches:

        answer = clean_text(answer)

        key = (
            int(percentage),
            answer.lower()
        )

        if key in seen:
            continue

        seen.add(key)

        result["results"].append({

            "percentage": int(percentage),

            "answer": answer
        })


    return result


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("MGMA STAT SCRAPER")
    print("=" * 60)


    # --------------------------------------------------------
    # GET LISTING PAGE
    # --------------------------------------------------------

    listing_html = fetch_page(
        LISTING_URL
    )

    if not listing_html:

        print("Could not fetch MGMA page.")
        return


    # --------------------------------------------------------
    # GET ARTICLE LINKS
    # --------------------------------------------------------

    article_links = get_article_links(
        listing_html
    )


    # --------------------------------------------------------
    # IMPORTANT FALLBACK
    # --------------------------------------------------------
    # If MGMA does not expose article links to requests,
    # use these current MGMA Stat article URLs.
    # --------------------------------------------------------

    if not article_links:

        print(
            "MGMA listing did not expose article links."
        )

        print(
            "Using current MGMA Stat article URLs..."
        )

        article_links = [

            "https://www.mgma.com/mgma-stat/fewer-than-1-in-10-see-prior-auth-turnarounds-faster",

            "https://www.mgma.com/mgma-stat/most-medical-groups-have-gone-years-without-a-commercial-payer-rate-increase",

            "https://www.mgma.com/mgma-stat/beyond-backfills-more-than-half-of-practices-adding-net-new-app-roles",

            "https://www.mgma.com/mgma-stat/about-1-in-3-medical-groups-see-higher-no-shows-in-2026-as-patients-face-higher-costs",

            "https://www.mgma.com/mgma-stat/as-ai-use-expands-medical-practice-leaders-shift-attention-to-measurement",

            "https://www.mgma.com/mgma-stat/days-in-a-r-holds-steady-for-most-practices-but-payer-pressure-persists-in-2026"
        ]


    print(
        f"\nTotal articles to fetch: "
        f"{len(article_links)}"
    )


    # --------------------------------------------------------
    # FETCH ARTICLES
    # --------------------------------------------------------

    articles = []


    for i, url in enumerate(
        article_links,
        start=1
    ):

        print("\n" + "-" * 60)

        print(
            f"[{i}/{len(article_links)}]"
        )

        html = fetch_page(url)

        if not html:

            print("Skipping...")
            continue


        try:

            article = extract_article(
                url,
                html
            )

            articles.append(article)


            print(
                "Title:",
                article["title"]
            )

            print(
                "Date:",
                article["published_date"]
            )

            print(
                "Author:",
                article["author"]
            )

            print(
                "Poll detected:",
                article["poll"]["detected"]
            )

            print(
                "Topics:",
                article["operational_topics"]
            )


        except Exception as e:

            print(
                "Extraction error:",
                e
            )


        time.sleep(1)


    # --------------------------------------------------------
    # SAVE JSON
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            articles,
            f,
            indent=2,
            ensure_ascii=False
        )


    print("\n" + "=" * 60)

    print(
        f"Total articles extracted: {len(articles)}"
    )

    print(
        f"Saved to: {OUTPUT_FILE}"
    )

    print("=" * 60)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()