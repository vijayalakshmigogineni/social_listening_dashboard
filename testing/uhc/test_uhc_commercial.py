import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

URLS = {
    "commercial_medical": "https://www.uhcprovider.com/en/policies-protocols/commercial-policies/commercial-medical-drug-policies.html",

    "monthly_updates": "https://www.uhcprovider.com/en/resource-library/news/2026/mpub-updates-sep-2026.html",

    "commercial_reimbursement": "https://www.uhcprovider.com/en/policies-protocols/commercial-policies/commercial-reimbursement-policies.html",

    "medicare_advantage": "https://www.uhcprovider.com/en/policies-protocols/medicare-advantage-policies/medicare-advantage-medical-policies.html",
}

headers = {
    "User-Agent": "Mozilla/5.0"
}

for name, url in URLS.items():

    print("\n" + "=" * 100)
    print(name.upper())
    print("=" * 100)

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    print("STATUS:", response.status_code)

    soup = BeautifulSoup(response.text, "html.parser")

    print("\nPAGE TITLE:")
    print(soup.title.get_text(" ", strip=True) if soup.title else "NO TITLE")

    print("\nUSEFUL LINKS:")
    print("-" * 100)

    found = 0

    for a in soup.find_all("a"):

        text = a.get_text(" ", strip=True)
        href = a.get("href")

        if not href:
            continue

        full_url = urljoin(response.url, href)

        text_lower = text.lower()
        url_lower = full_url.lower()

        useful = (
            ".pdf" in url_lower
            or "bulletin" in text_lower
            or "policy" in text_lower
            or "medical" in text_lower
            or "reimbursement" in text_lower
            or "archive" in text_lower
            or "updated" in text_lower
            or "revised" in text_lower
            or "retired" in text_lower
        )

        if useful:

            found += 1

            print(f"\n[{found}] TEXT:")
            print(text[:200])

            print("URL:")
            print(full_url)

    print("\nTOTAL USEFUL LINKS FOUND:", found)