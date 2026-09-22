import json
import requests
from bs4 import BeautifulSoup

RSS_FILE = "aapc_rss_threads.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# These are the 3 threads we want to test
TARGET_IDS = {
    "236506",  # Aetna denials - recent
    "203155",  # UHC denying all claims as OON
    "236010",  # Horizon NJ Health Downcoding Claims
}


def extract_posts(url):
    print(f"\nFetching: {url}")

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    print("Status:", response.status_code)

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    posts = []

    # Actual AAPC post containers
    post_elements = soup.select(
        "article.message.message--post.js-post"
    )

    print("Posts found:", len(post_elements))

    for post in post_elements:

        post_id = post.get("id")

        # Author
        author_element = post.select_one(
            ".message-name a"
        )

        author_name = (
            author_element.get_text(strip=True)
            if author_element
            else None
        )

        author_profile_url = (
            author_element.get("href")
            if author_element
            else None
        )

        # Location
        location_element = post.select_one(
            ".message-userExtras a[href*='location-info']"
        )

        location = (
            location_element.get_text(strip=True)
            if location_element
            else None
        )

        # Post text
        text_element = post.select_one(
            ".bbWrapper"
        )

        text = (
            text_element.get_text(
                "\n",
                strip=True
            )
            if text_element
            else None
        )

        # Timestamp
        time_element = post.select_one(
            "time"
        )

        created_at = (
            time_element.get("datetime")
            if time_element
            else None
        )

        posts.append({
            "post_id": post_id,
            "author_name": author_name,
            "author_profile_url": author_profile_url,
            "location": location,
            "created_at": created_at,
            "text": text
        })

    return posts


def main():

    # Load RSS results
    with open(
        RSS_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        rss_threads = json.load(f)

    selected_threads = [
        thread
        for thread in rss_threads
        if thread["source_item_id"] in TARGET_IDS
    ]

    print(
        f"Selected threads: {len(selected_threads)}"
    )

    results = []

    for thread in selected_threads:

        posts = extract_posts(
            thread["url"]
        )

        result = {
            "source": thread["source"],
            "source_item_id": thread["source_item_id"],
            "title": thread["title"],
            "url": thread["url"],
            "published_at": thread["published_at"],
            "post_count": len(posts),
            "posts": posts
        }

        results.append(result)

    output_file = "aapc_test_threads.json"

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            results,
            f,
            indent=2,
            ensure_ascii=False
        )

    print("\n================================")
    print("Finished!")
    print("================================")
    print(f"Threads processed: {len(results)}")
    print(f"Saved to: {output_file}")

    print("\nSummary:")

    for thread in results:
        print(
            f"- {thread['title']}"
        )
        print(
            f"  Posts: {thread['post_count']}"
        )


if __name__ == "__main__":
    main()