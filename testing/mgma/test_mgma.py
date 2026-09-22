import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

URL = "https://www.mgma.com/mgma-stat"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/153.0.0.0 Safari/537.36"
}

response = requests.get(URL, headers=headers, timeout=30)

print("Status:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")

print("Page title:", soup.title.get_text(strip=True))

print("\n--- PAGE TEXT PREVIEW ---\n")

text = soup.get_text("\n", strip=True)

print(text[:5000])

print("\n--- LINKS ---\n")

for a in soup.find_all("a", href=True):
    title = a.get_text(" ", strip=True)
    href = urljoin(URL, a["href"])

    if title:
        print(title, "=>", href)