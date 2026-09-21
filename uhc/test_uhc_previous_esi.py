import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

URL = "https://www.uhcprovider.com/en/policies-protocols/commercial-policies/commercial-medical-drug-policies.html"

TARGET = "2026T0616N"

response = requests.get(URL, timeout=30)

print("=" * 100)
print("SEARCHING FOR PREVIOUS UHC ESI POLICY VERSION")
print("=" * 100)

print("HTTP Status:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))

soup = BeautifulSoup(response.text, "html.parser")

matches = []

# Search visible link text + href
for a in soup.find_all("a", href=True):

    text = a.get_text(" ", strip=True)
    href = urljoin(URL, a["href"])

    combined = text + " " + href

    if TARGET.lower() in combined.lower():
        matches.append((text, href))

print("\nDIRECT LINK MATCHES:")
print("-" * 100)

for text, href in matches:
    print("TEXT:", text)
    print("URL :", href)
    print("-" * 100)

print("TOTAL DIRECT LINK MATCHES:", len(matches))


# Also search the raw HTML itself
print("\n" + "=" * 100)
print("RAW HTML SEARCH")
print("=" * 100)

html_lower = response.text.lower()

if TARGET.lower() in html_lower:
    print("FOUND 2026T0616N somewhere in the page HTML.")
    
    index = html_lower.find(TARGET.lower())

    print("\nCONTEXT:")
    print(response.text[max(0, index - 1000):index + 2000])

else:
    print("2026T0616N was NOT found in the page HTML.")