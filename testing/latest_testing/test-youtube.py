import requests
import csv
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    raise ValueError("YOUTUBE_API_KEY not found in .env file")


# ============================================================
# SLD SEARCH QUERIES
# ============================================================

SEARCH_QUERIES = [
    # Authorization / Utilization Management
    "pain management prior authorization",
    "pain management prior auth",
    "pain medicine prior authorization",
    "pain procedure prior authorization",
    "pain clinic prior authorization",

    # Denials / Claims Friction
    "pain management denials",
    "pain management billing denials",
    "pain medicine claim denials",
    "pain clinic insurance denials",
    "pain management denied claims",

    # Appeals
    "pain management insurance appeals",
    "pain management denial appeals",
    "pain medicine claim appeal",

    # Documentation / Medical Necessity
    "pain management medical necessity",
    "pain procedure medical necessity",
    "pain management documentation insurance",

    # Reimbursement / Payment
    "pain management reimbursement",
    "pain medicine reimbursement",
    "pain management insurance payment",
    "pain clinic billing reimbursement",

    # Claims / Payer
    "pain management insurance claims",
    "pain management payer problems",
    "pain management insurance problems",
    "pain clinic insurance problems",

    # Procedure / Device Access
    "SCS insurance prior authorization",
    "spinal cord stimulation insurance",
    "PNS prior authorization pain",
    "radiofrequency ablation insurance pain",
    "RFA prior authorization pain",
    "Intracept insurance coverage",
    "Intracept prior authorization",
    "SI joint injection insurance",
    "kyphoplasty insurance prior authorization",
    "epidural injection prior authorization",
]


# ============================================================
# DATE RANGE - LAST 30 DAYS
# ============================================================

now = datetime.now(timezone.utc)
one_month_ago = now - timedelta(days=30)

published_after = one_month_ago.strftime("%Y-%m-%dT%H:%M:%SZ")
published_before = now.strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================
# SETTINGS
# ============================================================

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

# IMPORTANT:
# Start with ONE page per query for validation.
# You can increase this later.
MAX_PAGES_PER_QUERY = 1


# ============================================================
# STORAGE
# ============================================================

all_videos = {}


print("=" * 80)
print("YOUTUBE SLD SOURCE VALIDATION")
print("=" * 80)

print(f"Date range:")
print(f"FROM : {published_after}")
print(f"UNTIL: {published_before}")

print(f"\nQueries: {len(SEARCH_QUERIES)}")
print(f"Pages per query: {MAX_PAGES_PER_QUERY}")

print("=" * 80)


# ============================================================
# SEARCH
# ============================================================

for query_number, query in enumerate(SEARCH_QUERIES, start=1):

    print("\n")
    print("#" * 80)
    print(f"[{query_number}/{len(SEARCH_QUERIES)}]")
    print(f"QUERY: {query}")
    print("#" * 80)

    next_page_token = None

    for page_number in range(1, MAX_PAGES_PER_QUERY + 1):

        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 50,
            "publishedAfter": published_after,
            "publishedBefore": published_before,
            "order": "relevance",
            "regionCode": "US",
            "relevanceLanguage": "en",
            "key": API_KEY,
        }

        if next_page_token:
            params["pageToken"] = next_page_token

        response = requests.get(
            SEARCH_URL,
            params=params,
            timeout=30
        )

        print(f"\nPage {page_number} | Status: {response.status_code}")

        if response.status_code != 200:
            print("ERROR:")
            print(response.text)
            break

        data = response.json()

        items = data.get("items", [])

        print(f"Results returned: {len(items)}")

        # ----------------------------------------------------
        # PROCESS RESULTS
        # ----------------------------------------------------

        for item in items:

            video_id = item.get("id", {}).get("videoId")

            if not video_id:
                continue

            snippet = item.get("snippet", {})

            title = snippet.get("title", "")
            channel = snippet.get("channelTitle", "")
            published_at = snippet.get("publishedAt", "")
            description = snippet.get("description", "")

            url = f"https://www.youtube.com/watch?v={video_id}"

            # ------------------------------------------------
            # DEDUPLICATE
            # ------------------------------------------------

            if video_id not in all_videos:

                all_videos[video_id] = {
                    "video_id": video_id,
                    "title": title,
                    "channel_title": channel,
                    "published_at": published_at,
                    "url": url,
                    "description": description,
                    "matched_queries": [query],
                }

            else:

                if query not in all_videos[video_id]["matched_queries"]:
                    all_videos[video_id]["matched_queries"].append(query)

        next_page_token = data.get("nextPageToken")

        if not next_page_token:
            break


# ============================================================
# DISPLAY RESULTS
# ============================================================

print("\n\n")
print("=" * 80)
print("SEARCH COMPLETE")
print("=" * 80)

print(f"TOTAL UNIQUE VIDEOS: {len(all_videos)}")

print("\n")
print("=" * 80)
print("VIDEOS FOR MANUAL VALIDATION")
print("=" * 80)


for number, video in enumerate(all_videos.values(), start=1):

    print("\n" + "-" * 80)

    print(f"{number}. {video['title']}")

    print(f"Channel    : {video['channel_title']}")

    print(f"Published  : {video['published_at']}")

    print(f"Matched by : {', '.join(video['matched_queries'])}")

    print(f"LINK       : {video['url']}")


# ============================================================
# SAVE CSV
# ============================================================

output_file = "youtube_sld_last_30_days.csv"

with open(
    output_file,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    fieldnames = [
        "video_id",
        "title",
        "channel_title",
        "published_at",
        "url",
        "description",
        "matched_queries",
    ]

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()

    for video in all_videos.values():

        row = video.copy()

        row["matched_queries"] = " | ".join(
            row["matched_queries"]
        )

        writer.writerow(row)


print("\n")
print("=" * 80)
print(f"CSV SAVED: {output_file}")
print("=" * 80)