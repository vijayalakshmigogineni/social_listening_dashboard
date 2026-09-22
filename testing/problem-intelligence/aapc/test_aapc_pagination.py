import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://www.aapc.com/discuss/forums/billing-reimbursement.583/"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(
    BASE_URL,
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

print("\nPAGINATION LINKS:")

for link in soup.select("a"):

    text = link.get_text(" ", strip=True)
    href = link.get("href")

    if not href:
        continue

    if text.lower() in ["next", "last"]:

        print(
            text,
            "->",
            urljoin(
                "https://www.aapc.com",
                href
            )
        )