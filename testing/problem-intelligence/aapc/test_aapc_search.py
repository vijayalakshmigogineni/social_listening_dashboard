import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

URL = "https://www.aapc.com/discuss/search/"

params = {
    "q": "prior authorization"
}

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(
    URL,
    params=params,
    headers=headers,
    timeout=30
)

print("Status:", response.status_code)
print("Final URL:", response.url)

soup = BeautifulSoup(response.text, "html.parser")

print("\nPAGE TITLE:")
print(
    soup.title.get_text(" ", strip=True)
    if soup.title
    else "No title"
)

print("\nPAGE TEXT PREVIEW:")
text = soup.get_text("\n", strip=True)

print(text[:5000])

print("\nTHREAD LINKS:")

links = soup.select("a[href*='/discuss/threads/']")

seen = set()

for link in links:

    href = link.get("href")

    title = link.get_text(" ", strip=True)

    if not href:
        continue

    full_url = urljoin(
        "https://www.aapc.com",
        href
    )

    if full_url not in seen:

        seen.add(full_url)

        print(
            f"- {title} -> {full_url}"
        )
        