import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

URL = "https://www.uhcprovider.com/en/policies-protocols/commercial-policies/commercial-medical-drug-policies.html"

response = requests.get(URL, timeout=30)

print("HTTP Status:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))

soup = BeautifulSoup(response.text, "html.parser")

matches = []

for a in soup.find_all("a", href=True):
    text = a.get_text(" ", strip=True)
    href = urljoin(URL, a["href"])

    if "epidural" in text.lower() or "spinal pain" in text.lower():
        matches.append((text, href))

print("\nMATCHING LINKS:")
print("=" * 100)

for text, href in matches:
    print("TEXT:", text)
    print("URL :", href)
    print("-" * 100)

print("\nTOTAL MATCHES:", len(matches))