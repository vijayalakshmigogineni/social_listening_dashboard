import requests
from bs4 import BeautifulSoup

url = "https://mcp.humana.com/tad/tad_new/home.aspx?type=provider"

print("=" * 80)
print("HUMANA MEDICAL & PHARMACY COVERAGE POLICIES")
print("=" * 80)

response = requests.get(url, timeout=30)

print("\nURL:")
print(url)

print("\nSTATUS:")
print(response.status_code)

print("\nCONTENT TYPE:")
print(response.headers.get("content-type"))

print("\nFINAL URL:")
print(response.url)

print("\nPAGE TITLE:")

soup = BeautifulSoup(response.text, "html.parser")
print(soup.title.get_text(strip=True) if soup.title else "No title")

print("\nPAGE TEXT SAMPLE:")
text = soup.get_text("\n", strip=True)

print(text[:5000])