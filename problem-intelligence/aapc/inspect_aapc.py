import requests
from bs4 import BeautifulSoup

URL = "https://www.aapc.com/discuss/threads/87798-billing-multiple-units.162540/"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(URL, headers=headers, timeout=30)

print("Status:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")

print("\n--- POSSIBLE POST CONTAINERS ---")

articles = soup.select("article")

print("Number of <article> elements:", len(articles))

for i, article in enumerate(articles[:10], start=1):
    print(f"\nARTICLE {i}")
    print("Class:", article.get("class"))
    print("ID:", article.get("id"))

print("\n--- POSSIBLE MESSAGE ELEMENTS ---")

messages = soup.select(".message")

print("Number of .message elements:", len(messages))

for i, message in enumerate(messages[:10], start=1):
    print(f"\nMESSAGE {i}")
    print("Class:", message.get("class"))
    print("ID:", message.get("id"))

print("\n--- TITLE ELEMENTS ---")

titles = soup.select("h1")

for title in titles:
    print("H1:", title.get_text(" ", strip=True))