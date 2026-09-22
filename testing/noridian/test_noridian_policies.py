import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


URL = "https://med.noridianmedicare.com/web/jfb/policies"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

PAIN_KEYWORDS = [
    "pain",
    "spinal",
    "spine",
    "epidural",
    "facet",
    "nerve",
    "radiofrequency",
    "ablation",
    "stimulator",
    "stimulation",
    "sacroiliac",
    "sacroiliac",
    "denervation",
    "kyphoplasty",
    "injection",
]


print("=" * 100)
print("NORIDIAN JF PART B — POLICY PAGE TEST")
print("=" * 100)

print("\nURL:")
print(URL)

try:

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30,
        allow_redirects=True
    )

    print("\nHTTP STATUS:")
    print(response.status_code)

    print("\nFINAL URL:")
    print(response.url)

    print("\nCONTENT TYPE:")
    print(response.headers.get("Content-Type"))

    print("\nRESPONSE SIZE:")
    print(len(response.content), "bytes")

    if response.status_code != 200:
        print("\nFAILED")
        print(response.text[:1000])
        raise SystemExit

    soup = BeautifulSoup(response.text, "html.parser")

    print("\nPAGE TITLE:")
    print(
        soup.title.get_text(strip=True)
        if soup.title
        else "NO TITLE"
    )

    # ---------------------------------------------------------
    # ALL LINKS
    # ---------------------------------------------------------

    links = soup.find_all("a")

    print("\nTOTAL LINKS:")
    print(len(links))

    # ---------------------------------------------------------
    # FIND POLICY / COVERAGE LINKS
    # ---------------------------------------------------------

    policy_links = []
    pain_links = []

    seen = set()

    for link in links:

        text = link.get_text(" ", strip=True)
        href = link.get("href")

        if not href:
            continue

        full_url = urljoin(response.url, href)

        if full_url in seen:
            continue

        seen.add(full_url)

        combined = (text + " " + full_url).lower()

        # General policy-related links
        if any(
            keyword in combined
            for keyword in [
                "lcd",
                "billing",
                "coding",
                "coverage",
                "policy",
                "article",
                "mcd"
            ]
        ):
            policy_links.append(
                (text, full_url)
            )

        # Pain-related links
        if any(
            keyword in combined
            for keyword in PAIN_KEYWORDS
        ):
            pain_links.append(
                (text, full_url)
            )

    # ---------------------------------------------------------
    # PRINT POLICY LINKS
    # ---------------------------------------------------------

    print("\n" + "=" * 100)
    print("POLICY / COVERAGE RELATED LINKS")
    print("=" * 100)

    print(
        "Number of policy-related links:",
        len(policy_links)
    )

    for text, url in policy_links[:80]:

        print("\nTEXT:")
        print(text if text else "(no link text)")

        print("URL:")
        print(url)

    # ---------------------------------------------------------
    # PRINT PAIN RELATED LINKS
    # ---------------------------------------------------------

    print("\n" + "=" * 100)
    print("PAIN-MANAGEMENT RELATED LINKS")
    print("=" * 100)

    print(
        "Number of pain-related links:",
        len(pain_links)
    )

    for text, url in pain_links[:80]:

        print("\nTEXT:")
        print(text if text else "(no link text)")

        print("URL:")
        print(url)

    # ---------------------------------------------------------
    # PAGE TEXT SAMPLE
    # ---------------------------------------------------------

    print("\n" + "=" * 100)
    print("PAGE TEXT SAMPLE")
    print("=" * 100)

    page_text = soup.get_text(
        "\n",
        strip=True
    )

    print(page_text[:5000])

except Exception as e:

    print("\nERROR:")
    print(type(e).__name__, str(e))