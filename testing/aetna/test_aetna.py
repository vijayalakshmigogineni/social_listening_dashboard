import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

URLS = {
    "cpb_main_index":
        "https://www.aetna.com/health-care-professionals/clinical-policy-bulletins.html",

    "cpb_medical_index":
        "https://www.aetna.com/health-care-professionals/clinical-policy-bulletins/medical-clinical-policy-bulletins.html",
}

headers = {
    "User-Agent": "Mozilla/5.0"
}

PAIN_KEYWORDS = [
    "pain", "spine", "spinal", "epidural", "facet", "nerve", "ablation",
    "stimulator", "stimulation", "injection", "kyphoplasty", "sacroiliac",
    "si joint", "intracept", "basivertebral"
]

for name, url in URLS.items():

    print("\n" + "=" * 80)
    print(name.upper())
    print("=" * 80)

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30,
            allow_redirects=True
        )

        print("Requested URL:")
        print(url)

        print("\nFinal URL:")
        print(response.url)

        print("\nHTTP Status:")
        print(response.status_code)

        print("\nContent-Type:")
        print(response.headers.get("Content-Type"))

        print("\nResponse Size:")
        print(len(response.content), "bytes")

        if response.status_code != 200:
            print("\nFAILED - first 500 chars of body:")
            print(response.text[:500])
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        print("\nPage Title:")
        print(soup.title.get_text(strip=True) if soup.title else "NO TITLE")

        links = soup.find_all("a")
        print("\nTotal links found:", len(links))

        seen = set()
        pain_links = []

        for link in links:
            text = link.get_text(" ", strip=True)
            href = link.get("href")

            if not href:
                continue

            full_url = urljoin(response.url, href)

            if full_url in seen:
                continue
            seen.add(full_url)

            haystack = (text + " " + full_url).lower()

            if any(k in haystack for k in PAIN_KEYWORDS):
                pain_links.append((text, full_url))

        print("\nPain-management-related links found:", len(pain_links))
        print("-" * 80)

        for text, full_url in pain_links[:40]:
            print("-", text[:100] if text else "(no text)")
            print("  ", full_url)

    except Exception as e:
        print("\nERROR:")
        print(type(e).__name__, str(e))
