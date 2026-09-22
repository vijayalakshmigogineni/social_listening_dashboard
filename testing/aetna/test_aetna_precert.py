import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

URLS = {
    "precertification_lists":
        "https://www.aetna.com/health-care-professionals/precertification/precertification-lists.html",

    "precertification_overview":
        "https://www.aetna.com/health-care-professionals/precertification.html",
}

headers = {
    "User-Agent": "Mozilla/5.0"
}

for name, url in URLS.items():

    print("\n" + "=" * 90)
    print(name.upper())
    print("=" * 90)

    try:
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)

        print("Requested URL:", url)
        print("Final URL:    ", response.url)
        print("HTTP Status:  ", response.status_code)
        print("Content-Type: ", response.headers.get("Content-Type"))
        print("Size:         ", len(response.content), "bytes")

        if response.status_code != 200:
            print("FAILED")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        print("Page Title:   ", soup.title.get_text(strip=True) if soup.title else "NO TITLE")

        pdf_links = []
        other_links = []
        for a in soup.find_all("a"):
            href = a.get("href")
            text = a.get_text(" ", strip=True)
            if not href:
                continue
            full_url = urljoin(response.url, href)
            if ".pdf" in full_url.lower():
                pdf_links.append((text, full_url))
            elif any(k in (text + full_url).lower() for k in ["precert", "cpt", "code", "lookup", "search"]):
                other_links.append((text, full_url))

        print(f"\nPDF links found: {len(pdf_links)}")
        for text, u in pdf_links[:20]:
            print("  -", text[:80], "->", u)

        print(f"\nPrecert/CPT/lookup-related links found: {len(other_links)}")
        for text, u in other_links[:20]:
            print("  -", text[:80], "->", u)

        # Look for a form/search box that might hit a CPT lookup API
        forms = soup.find_all("form")
        print(f"\nForms found: {len(forms)}")
        for f in forms:
            action = f.get("action")
            endpoint = f.get("data-endpoint")
            if action or endpoint:
                print("  - action:", action, " data-endpoint:", endpoint)

    except Exception as e:
        print("\nERROR:", type(e).__name__, str(e))
