import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

url = "https://mcp.humana.com/tad/tad_new/Search.aspx?searchtype=beginswith&docbegin=E&policyType=medical"

print("=" * 80)
print("HUMANA - MEDICAL POLICY LISTING TEST")
print("=" * 80)

response = requests.get(url, timeout=30)

print("\nURL:")
print(url)

print("\nSTATUS:")
print(response.status_code)

print("\nFINAL URL:")
print(response.url)

print("\nCONTENT TYPE:")
print(response.headers.get("content-type"))

soup = BeautifulSoup(response.text, "html.parser")

print("\nPAGE TITLE:")
print(
    soup.title.get_text(strip=True)
    if soup.title
    else "No title"
)

print("\n" + "=" * 80)
print("PAGE TEXT")
print("=" * 80)

text = soup.get_text("\n", strip=True)

print(text[:10000])


print("\n" + "=" * 80)
print("LINKS TO POLICIES")
print("=" * 80)

count = 0

for link in soup.find_all("a", href=True):

    text = link.get_text(" ", strip=True)
    href = link.get("href")

    if text:

        print(
            "\nTEXT:",
            text,
            "\nURL:",
            urljoin(response.url, href)
        )

        count += 1

print("\nTotal links printed:", count)

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)