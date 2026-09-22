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

        print("\nContent-Length:")
        print(response.headers.get("Content-Length"))

        print("\nResponse Size:")
        print(len(response.content), "bytes")

        print("\nFirst 500 characters:")
        print(response.text[:500])

        soup = BeautifulSoup(response.text, "html.parser")

        print("\nPage Title:")
        print(soup.title.get_text(strip=True) if soup.title else "NO TITLE")

        links = soup.find_all("a")

        print("\nNumber of links found:")
        print(len(links))

        print("\nFirst 20 links:")

        for link in links[:20]:
            text = link.get_text(" ", strip=True)
            href = link.get("href")

            if href:
                full_url = urljoin(response.url, href)
                print("-", text[:100])
                print("  ", full_url)

    except Exception as e:
        print("\nERROR:")
        print(type(e).__name__, str(e))