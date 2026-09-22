import os
import time
import json
import csv
import re
import requests

from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()



# ============================================================
# CONFIGURATION
# ============================================================



APIFY_TOKEN = os.getenv("APIFY_TOKEN")

if not APIFY_TOKEN:
    raise ValueError(
        "APIFY_TOKEN not found in .env"
    )


ACTOR_ID = "tweetapi~twitter-x-search-scraper"


# ------------------------------------------------------------
# X SEARCH QUERIES
# ------------------------------------------------------------

QUERIES = [
    '"pain management" "prior authorization" lang:en',
    '"pain practice" denial lang:en',
]


# ------------------------------------------------------------
# COLLECTION SETTINGS
# ------------------------------------------------------------

MAX_ITEMS = 50

MODE = "Latest"


# ------------------------------------------------------------
# OUTPUT DIRECTORY
# ------------------------------------------------------------

OUTPUT_DIR = "x_sld_test_results"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# 1. START APIFY ACTOR
# ============================================================

def start_actor(query):

    url = (
        f"https://api.apify.com/v2/actors/"
        f"{ACTOR_ID}/runs"
    )

    payload = {
        "query": query,
        "mode": MODE,
        "maxItems": MAX_ITEMS
    }

    headers = {
        "Authorization": f"Bearer {APIFY_TOKEN}",
        "Content-Type": "application/json"
    }

    print("\n" + "=" * 80)
    print("SEARCH:", query)
    print("=" * 80)

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=60
    )

    print(
        "Start status:",
        response.status_code
    )

    if response.status_code != 201:

        print("\nApify response:")
        print(response.text)

        raise RuntimeError(
            "Failed to start Apify Actor"
        )

    data = response.json()["data"]

    run_id = data["id"]

    dataset_id = data["defaultDatasetId"]

    print(
        "Run ID:",
        run_id
    )

    print(
        "Dataset ID:",
        dataset_id
    )

    return run_id, dataset_id


# ============================================================
# 2. WAIT FOR APIFY ACTOR
# ============================================================

def wait_for_actor(run_id):

    url = (
        f"https://api.apify.com/v2/"
        f"actor-runs/{run_id}"
    )

    while True:

        response = requests.get(
            url,
            params={
                "token": APIFY_TOKEN
            },
            timeout=30
        )

        if response.status_code != 200:

            print("\nApify response:")
            print(response.text)

            raise RuntimeError(
                "Could not check Apify Actor status"
            )

        data = response.json()["data"]

        status = data["status"]

        print(
            "Current status:",
            status
        )

        # ----------------------------------------------------
        # Actor finished
        # ----------------------------------------------------

        if status in [
            "SUCCEEDED",
            "FAILED",
            "ABORTED",
            "TIMED-OUT"
        ]:

            return data

        # ----------------------------------------------------
        # Still running
        # ----------------------------------------------------

        time.sleep(5)


# ============================================================
# 3. GET DATASET
# ============================================================

def get_dataset(dataset_id):

    url = (
        f"https://api.apify.com/v2/"
        f"datasets/{dataset_id}/items"
    )

    response = requests.get(
        url,
        params={
            "token": APIFY_TOKEN,
            "clean": "true"
        },
        timeout=60
    )

    if response.status_code != 200:

        print("\nApify response:")
        print(response.text)

        raise RuntimeError(
            "Could not retrieve Apify dataset"
        )

    return response.json()


# ============================================================
# 4. GET MEDIA TYPE
# ============================================================

def get_media_type(media):

    # --------------------------------------------------------
    # No media
    # --------------------------------------------------------

    if not media:

        return "text"


    media_types = set()


    # --------------------------------------------------------
    # Collect media types
    # --------------------------------------------------------

    for item in media:

        if not isinstance(
            item,
            dict
        ):

            continue

        media_type = item.get(
            "type"
        )

        if media_type:

            media_types.add(
                media_type
            )


    # --------------------------------------------------------
    # Media exists but type unavailable
    # --------------------------------------------------------

    if not media_types:

        return "text"


    # --------------------------------------------------------
    # One media type
    # --------------------------------------------------------

    if len(media_types) == 1:

        return next(
            iter(media_types)
        )


    # --------------------------------------------------------
    # Multiple media types
    # --------------------------------------------------------

    return "mixed"


# ============================================================
# 5. GET PARENT ID
# ============================================================

def get_parent_id(tweet):

    reply_to = tweet.get(
        "replyTo"
    )

    if not reply_to:

        return None


    # --------------------------------------------------------
    # replyTo may be a dictionary
    # --------------------------------------------------------

    if isinstance(
        reply_to,
        dict
    ):

        # Try the most likely actual ID fields
        return (
            reply_to.get("id")
            or reply_to.get("tweetId")
            or reply_to.get("sourceItemId")
        )


    # --------------------------------------------------------
    # If replyTo is directly an ID
    # --------------------------------------------------------

    if isinstance(
        reply_to,
        str
    ):

        return reply_to


    return None


# ============================================================
# 6. NORMALIZE X POST
# ============================================================

def normalize_x_post(
    tweet,
    collected_at
):

    # --------------------------------------------------------
    # Extract nested objects
    # --------------------------------------------------------

    author = tweet.get(
        "author"
    ) or {}

    metrics = tweet.get(
        "metrics"
    ) or {}

    media = tweet.get(
        "media"
    ) or []


    # --------------------------------------------------------
    # Parent / reply relationship
    # --------------------------------------------------------

    parent_id = get_parent_id(
        tweet
    )


    # --------------------------------------------------------
    # EXACT CANONICAL MODEL
    # --------------------------------------------------------

    normalized_record = {

        # ====================================================
        # SOURCE
        # ====================================================

        "source": "X",

        "source_item_id": tweet.get(
            "id"
        ),

        "url": tweet.get(
            "url"
        ),

        "title": None,

        "text": tweet.get(
            "text"
        ),


        # ====================================================
        # AUTHOR
        # ====================================================

        "author_id": author.get(
            "id"
        ),

        "author_name": author.get(
            "name"
        ),

        # IMPORTANT:
        # TweetAPI returns the profile URL as "url"
        # inside the author object.
        "author_profile_url": author.get(
            "url"
        ),

        # Not directly available from the tweet.
        "author_role": None,


        # ====================================================
        # ORGANIZATION
        # ====================================================

        # Do not guess these.
        "organization_name": None,

        "organization_url": None,


        # ====================================================
        # LOCATION
        # ====================================================

        # Do not infer location.
        "location": None,


        # ====================================================
        # DATES
        # ====================================================

        "created_at": tweet.get(
            "createdAt"
        ),

        "collected_at": collected_at,


        # ====================================================
        # ENGAGEMENT
        # ====================================================

        # IMPORTANT:
        # These field names match the ACTUAL Apify output:
        #
        # likes
        # replies
        # retweets
        # quotes
        # bookmarks
        #
        # If a metric is not provided by the Actor,
        # it remains None.
        "engagement": {

            "likes": metrics.get(
                "likes"
            ),

            "comments": metrics.get(
                "replies"
            ),

            "reposts": metrics.get(
                "retweets"
            ),

            "quotes": metrics.get(
                "quotes"
            ),

            "bookmarks": metrics.get(
                "bookmarks"
            ),

            "views": metrics.get(
                "views"
            )
        },


        # ====================================================
        # CONVERSATION
        # ====================================================

        "parent_id": parent_id,

        "conversation_id": tweet.get(
            "conversationId"
        ),


        # ====================================================
        # MEDIA
        # ====================================================

        "media_type": get_media_type(
            media
        ),


        # ====================================================
        # ORIGINAL RAW DATA
        # ====================================================

        # Keep the complete original Apify record.
        "raw_data": tweet,


        # ====================================================
        # SOURCE-SPECIFIC METADATA
        # ====================================================

        "source_metadata": {

            "lang": tweet.get(
                "lang"
            ),

            "type": tweet.get(
                "type"
            ),

            "entities": tweet.get(
                "entities"
            ),

            "media": media,

            "possibly_sensitive": tweet.get(
                "possiblySensitive"
            ),

            "quoted_tweet_id": tweet.get(
                "quotedTweetId"
            ),

            "retweeted_tweet_id": tweet.get(
                "retweetedTweetId"
            ),

            "author_username": author.get(
                "username"
            ),

            "author_avatar_url": author.get(
                "avatarUrl"
            ),

            "author_verified": author.get(
                "verified"
            ),

            "author_blue_verified": author.get(
                "isBlueVerified"
            )
        }
    }


    return normalized_record


# ============================================================
# 7. SAFE FILE NAME
# ============================================================

def safe_filename(query):

    name = re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        query
    )

    return name.strip(
        "_"
    )[:80]


# ============================================================
# 8. SAVE RAW JSON
# ============================================================

def save_raw_json(
    query,
    tweets
):

    filename = (
        f"{OUTPUT_DIR}/raw_"
        f"{safe_filename(query)}.json"
    )


    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            tweets,
            file,
            indent=2,
            ensure_ascii=False
        )


    print(
        "Raw JSON saved:",
        filename
    )


# ============================================================
# 9. SAVE NORMALIZED JSON
# ============================================================

def save_normalized_json(
    query,
    normalized_records
):

    filename = (
        f"{OUTPUT_DIR}/normalized_"
        f"{safe_filename(query)}.json"
    )


    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            normalized_records,
            file,
            indent=2,
            ensure_ascii=False
        )


    print(
        "Normalized JSON saved:",
        filename
    )


# ============================================================
# 10. SAVE NORMALIZED CSV
# ============================================================

def save_normalized_csv(
    query,
    normalized_records
):

    filename = (
        f"{OUTPUT_DIR}/normalized_"
        f"{safe_filename(query)}.csv"
    )


    if not normalized_records:

        print(
            "No normalized records to save."
        )

        return


    rows = []


    # --------------------------------------------------------
    # Convert each canonical record to one CSV row
    # --------------------------------------------------------

    for record in normalized_records:

        row = {

            "source":
                record["source"],

            "source_item_id":
                record["source_item_id"],

            "url":
                record["url"],

            "title":
                record["title"],

            "text":
                record["text"],

            "author_id":
                record["author_id"],

            "author_name":
                record["author_name"],

            "author_profile_url":
                record["author_profile_url"],

            "author_role":
                record["author_role"],

            "organization_name":
                record["organization_name"],

            "organization_url":
                record["organization_url"],

            "location":
                record["location"],

            "created_at":
                record["created_at"],

            "collected_at":
                record["collected_at"],

            # Nested objects are stored as JSON strings
            # inside the CSV.
            "engagement":
                json.dumps(
                    record["engagement"],
                    ensure_ascii=False
                ),

            "parent_id":
                record["parent_id"],

            "conversation_id":
                record["conversation_id"],

            "media_type":
                record["media_type"],

            "raw_data":
                json.dumps(
                    record["raw_data"],
                    ensure_ascii=False
                ),

            "source_metadata":
                json.dumps(
                    record["source_metadata"],
                    ensure_ascii=False
                )
        }


        rows.append(
            row
        )


    # --------------------------------------------------------
    # EXACT CANONICAL FIELD ORDER
    # --------------------------------------------------------

    fieldnames = [

        "source",

        "source_item_id",

        "url",

        "title",

        "text",

        "author_id",

        "author_name",

        "author_profile_url",

        "author_role",

        "organization_name",

        "organization_url",

        "location",

        "created_at",

        "collected_at",

        "engagement",

        "parent_id",

        "conversation_id",

        "media_type",

        "raw_data",

        "source_metadata"
    ]


    # --------------------------------------------------------
    # Write CSV
    # --------------------------------------------------------

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


    print(
        "Normalized CSV saved:",
        filename
    )


# ============================================================
# 11. MAIN COLLECTION PIPELINE
# ============================================================

def main():

    # --------------------------------------------------------
    # Combined result containers
    # --------------------------------------------------------

    all_raw_results = []

    all_normalized_results = []


    # --------------------------------------------------------
    # Process every search query
    # --------------------------------------------------------

    for query in QUERIES:


        # ====================================================
        # START ACTOR
        # ====================================================

        run_id, dataset_id = start_actor(
            query
        )


        # ====================================================
        # WAIT FOR ACTOR
        # ====================================================

        run_data = wait_for_actor(
            run_id
        )


        final_status = run_data[
            "status"
        ]


        print(
            "Final status:",
            final_status
        )


        # ====================================================
        # HANDLE FAILED RUN
        # ====================================================

        if final_status != "SUCCEEDED":

            print(
                "\nActor did not succeed."
            )

            print(
                "Run ID:",
                run_id
            )

            continue


        # ====================================================
        # GET DATASET
        # ====================================================

        tweets = get_dataset(
            dataset_id
        )


        print(
            "Posts collected:",
            len(tweets)
        )


        # ====================================================
        # COLLECTION TIMESTAMP
        # ====================================================

        collected_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )


        # ====================================================
        # SAVE RAW DATA
        # ====================================================

        save_raw_json(
            query,
            tweets
        )


        # ====================================================
        # NORMALIZE EACH POST
        # ====================================================

        normalized_records = []


        for tweet in tweets:

            normalized_record = (
                normalize_x_post(
                    tweet,
                    collected_at
                )
            )


            normalized_records.append(
                normalized_record
            )


        # ====================================================
        # SAVE NORMALIZED DATA
        # ====================================================

        save_normalized_json(
            query,
            normalized_records
        )


        save_normalized_csv(
            query,
            normalized_records
        )


        # ====================================================
        # ADD TO COMBINED RESULTS
        # ====================================================

        all_raw_results.extend(
            tweets
        )

        all_normalized_results.extend(
            normalized_records
        )


    # ========================================================
    # SAVE COMBINED RAW JSON
    # ========================================================

    combined_raw_file = (
        f"{OUTPUT_DIR}/"
        "all_x_raw_results.json"
    )


    with open(
        combined_raw_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            all_raw_results,
            file,
            indent=2,
            ensure_ascii=False
        )


    # ========================================================
    # SAVE COMBINED NORMALIZED JSON
    # ========================================================

    combined_normalized_file = (
        f"{OUTPUT_DIR}/"
        "all_x_normalized_results.json"
    )


    with open(
        combined_normalized_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            all_normalized_results,
            file,
            indent=2,
            ensure_ascii=False
        )


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n" + "=" * 80)

    print(
        "FINAL RESULT"
    )

    print("=" * 80)


    print(
        "Total raw posts:",
        len(all_raw_results)
    )


    print(
        "Total normalized posts:",
        len(all_normalized_results)
    )


    print(
        "\nRaw combined file:"
    )

    print(
        combined_raw_file
    )


    print(
        "\nNormalized combined file:"
    )

    print(
        combined_normalized_file
    )


    print(
        "\nCanonical fields:"
    )


    canonical_fields = [

        "source",
        "source_item_id",
        "url",
        "title",
        "text",
        "author_id",
        "author_name",
        "author_profile_url",
        "author_role",
        "organization_name",
        "organization_url",
        "location",
        "created_at",
        "collected_at",
        "engagement",
        "parent_id",
        "conversation_id",
        "media_type",
        "raw_data",
        "source_metadata"
    ]


    for field in canonical_fields:

        print(
            " -",
            field
        )


    print(
        "\nDone."
    )

    print("=" * 80)


# ============================================================
# 12. RUN PROGRAM
# ============================================================

if __name__ == "__main__":

    main()