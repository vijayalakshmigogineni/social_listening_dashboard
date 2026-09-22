import requests
from bs4 import BeautifulSoup

URLS = [
    "https://www.ngsmedicare.com/",
    "https://ngsmedicare.com/",
]

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

for url in URLS:

    print("=" * 70)
    print("TESTING:", url)
    print("=" * 70)

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=90,
            verify=False
        )

        print("STATUS:", response.status_code)
        print("FINAL URL:", response.url)
        print("CONTENT TYPE:", response.headers.get("content-type"))
        print("CONTENT LENGTH:", len(response.content))

        soup = BeautifulSoup(response.text, "html.parser")

        print("\nTITLE:")
        print(soup.title.get_text(strip=True) if soup.title else None)

        print("\nHEADINGS:")
        headings = soup.find_all(["h1", "h2", "h3"])

        for h in headings[:30]:
            text = h.get_text(" ", strip=True)
            if text:
                print("-", text)

        print("\nLINK COUNT:")
        print(len(soup.find_all("a")))

        print("\nFIRST 30 LINKS:")
        for a in soup.find_all("a")[:30]:
            text = a.get_text(" ", strip=True)
            href = a.get("href")

            if text or href:
                print(
                    f"TEXT: {text[:100]} | "
                    f"HREF: {href}"
                )

        filename = (
            "ngs_raw.html"
            if "www." in url
            else "ngs_nonwww_raw.html"
        )

        with open(filename, "w", encoding="utf-8") as f:
            f.write(response.text)

        print("\nSAVED:", filename)

    except Exception as e:
        print("ERROR:", repr(e))