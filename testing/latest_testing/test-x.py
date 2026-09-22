import os
import requests
from dotenv import load_dotenv

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")

if not APIFY_TOKEN:
    raise ValueError("APIFY_TOKEN not found in .env")

RUN_ID = "ea9fNzsCdvdRrxqvk"
DATASET_ID = "7Fh3BSKGjQKcghJpl"


# --------------------------------------------------
# 1. Check run status
# --------------------------------------------------

run_url = f"https://api.apify.com/v2/actor-runs/{RUN_ID}"

response = requests.get(
    run_url,
    params={"token": APIFY_TOKEN},
    timeout=30
)

print("Run status request:", response.status_code)

run_data = response.json()["data"]

print("Status:", run_data["status"])


# --------------------------------------------------
# 2. If finished, get dataset results
# --------------------------------------------------

if run_data["status"] == "SUCCEEDED":

    dataset_url = (
        f"https://api.apify.com/v2/datasets/"
        f"{DATASET_ID}/items"
    )

    response = requests.get(
        dataset_url,
        params={
            "token": APIFY_TOKEN,
            "clean": "true"
        },
        timeout=30
    )

    print("Dataset request:", response.status_code)

    tweets = response.json()

    print("\nTOTAL POSTS:", len(tweets))

    for i, tweet in enumerate(tweets, start=1):

        print("\n" + "=" * 80)
        print(f"POST {i}")

        print("ID:", tweet.get("id"))
        print("URL:", tweet.get("url"))
        print("Created:", tweet.get("createdAt"))
        print("Text:", tweet.get("text"))

        author = tweet.get("author") or {}

        print("Author:", author.get("name"))
        print("Username:", author.get("username"))

        metrics = tweet.get("metrics") or {}

        print("Likes:", metrics.get("likeCount"))
        print("Replies:", metrics.get("replyCount"))
        print("Reposts:", metrics.get("retweetCount"))
        print("Views:", metrics.get("viewCount"))

else:

    print("\n⏳ Actor is not finished yet.")
    print("Run this script again in a few seconds.")