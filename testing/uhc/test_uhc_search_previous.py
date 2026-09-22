import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

TARGET = "2026T0616N"

urls = [
    f"https://www.uhcprovider.com/en/search.html?q={quote(TARGET)}",
    f"https://www.uhcprovider.com/en/search.html?query={quote(TARGET)}",
]

for url in urls:

    print("\n" + "=" * 100)
    print("TEST URL")
    print("=" * 100)
    print(url)

    response = requests.get(url, timeout=30)

    print("HTTP Status:", response.status_code)
    print("Content-Type:", response.headers.get("Content-Type"))
    print("Size:", len(response.content))

    soup = BeautifulSoup(response.text, "html.parser")

    print("\nPAGE TITLE:")
    print(soup.title.get_text(strip=True) if soup.title else "No title")

    print("\nTEXT MATCHES:")

    text = soup.get_text(" ", strip=True)

    if TARGET.lower() in text.lower():
        index = text.lower().find(TARGET.lower())
        print(text[max(0, index - 500):index + 1500])
    else:
        print("Target policy number NOT found.")

    print("\nLINKS CONTAINING TARGET:")

    found = 0

    for a in soup.find_all("a", href=True):
        link_text = a.get_text(" ", strip=True)
        href = a["href"]

        if TARGET.lower() in (link_text + " " + href).lower():
            print("TEXT:", link_text)
            print("URL :", href)
            print("-" * 80)
            found += 1

    print("LINK MATCHES:", found)