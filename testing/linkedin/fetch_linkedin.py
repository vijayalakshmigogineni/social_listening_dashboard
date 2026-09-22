import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv


# -----------------------------
# Load configuration
# -----------------------------

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
APIFY_RUN_ID = os.getenv("APIFY_RUN_ID")

if not APIFY_TOKEN:
    raise ValueError("APIFY_TOKEN is missing from .env")

if not APIFY_RUN_ID:
    raise ValueError("APIFY_RUN_ID is missing from .env")


# -----------------------------
# Apify API endpoint
# -----------------------------

url = (
    f"https://api.apify.com/v2/"
    f"actor-runs/{APIFY_RUN_ID}/dataset/items"
)

params = {
    "format": "json",
    "clean": "true"
}

headers = {
    "Authorization": f"Bearer {APIFY_TOKEN}"
}


# -----------------------------
# Fetch data
# -----------------------------

print("Fetching LinkedIn data from Apify...")

response = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=60
)

response.raise_for_status()

posts = response.json()


# -----------------------------
# Save raw data
# -----------------------------

output_dir = Path("data/raw")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "linkedin_posts.json"

with open(output_file, "w", encoding="utf-8") as file:
    json.dump(posts, file, indent=2, ensure_ascii=False)


# -----------------------------
# Print summary
# -----------------------------

print()
print("Fetch completed successfully!")
print(f"Posts fetched: {len(posts)}")
print(f"Saved to: {output_file}")


# -----------------------------
# Show important fields
# -----------------------------

for index, post in enumerate(posts, start=1):

    print()
    print(f"POST {index}")
    print("-" * 50)

    print("Author:", post.get("authorName"))
    print("Posted:", post.get("postedAtISO"))
    print("Text:", post.get("text", "")[:300])
    print("Likes:", post.get("numLikes"))
    print("Shares:", post.get("numShares"))