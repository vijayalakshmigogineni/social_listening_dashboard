import requests
from bs4 import BeautifulSoup

URL = "https://www.aapc.com/discuss/threads/87798-billing-multiple-units.162540/"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(URL, headers=headers, timeout=30)

print("Status:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")

# Get the first actual forum post
post = soup.select_one("article.message.message--post")

if not post:
    print("No post found")
    exit()

print("\n==============================")
print("POST ID")
print("==============================")
print(post.get("id"))

print("\n==============================")
print("POST HTML")
print("==============================")
print(post.prettify()[:15000])