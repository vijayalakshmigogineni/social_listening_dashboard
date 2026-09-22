import requests
from bs4 import BeautifulSoup

URL = "https://www.aapc.com/discuss/threads/87798-billing-multiple-units.162540/"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(URL, headers=headers, timeout=30)

print("Status:", response.status_code)
print("Final URL:", response.url)

soup = BeautifulSoup(response.text, "html.parser")

print("\nPAGE TITLE:")
print(soup.title.get_text(strip=True) if soup.title else "No title")

print("\nTEXT PREVIEW:")
text = soup.get_text("\n", strip=True)

print(text[:5000])