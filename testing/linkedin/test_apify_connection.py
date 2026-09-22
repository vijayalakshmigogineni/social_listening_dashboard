import os
import requests

TOKEN = os.getenv("APIFY_TOKEN")

if not TOKEN:
    raise RuntimeError("APIFY_TOKEN is not set")

url = "https://api.apify.com/v2/users/me"

response = requests.get(
    url,
    headers={
        "Authorization": f"Bearer {TOKEN}"
    },
    timeout=30
)

print("=" * 70)
print("APIFY CONNECTION TEST")
print("=" * 70)

print("HTTP status:", response.status_code)

if response.ok:
    data = response.json()

    print("Apify connection: SUCCESS")
    print("Username:", data.get("username"))
    print("User ID:", data.get("id"))
else:
    print("Apify connection: FAILED")
    print(response.text[:1000])