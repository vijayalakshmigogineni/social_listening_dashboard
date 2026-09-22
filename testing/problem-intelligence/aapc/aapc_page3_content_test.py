import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin


BASE_URL = "https://www.aapc.com"
FORUM_PAGE = "https://www.aapc.com/discuss/forums/billing-reimbursement.583/page-3"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_thread_links():
    response = requests.get(
        FORUM_PAGE,
        headers=HEADERS,
        timeout=30
    )

    print("Forum page status:", response.status_code)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    threads = []

    for link in soup.find_all("a", href=True):

        href = link["href"]

        if "/discuss/threads/" not in href:
            continue

        title = link.get_text(" ", strip=True)

        if not title:
            continue

        full_url = urljoin(BASE_URL, href)

        # Avoid duplicate thread links
        if any(t["url"] == full_url for t in threads):
            continue

        threads.append({
            "title": title,
            "url": full_url
        })

    return threads


def get_thread_posts(thread):
    response = requests.get(
        thread["url"],
        headers=HEADERS,
        timeout=30
    )

    print("  Status:", response.status_code)

    if response.status_code != 200:
        return {
            **thread,
            "post_count": 0,
            "posts": []
        }

    soup = BeautifulSoup(response.text, "html.parser")

    posts = []

    # Actual AAPC forum posts
    post_elements = soup.select(
        "article.message.message--post"
    )

    for post in post_elements:

        post_id = post.get("id")

        # Author
        author_element = post.select_one(
            ".message-name a"
        )

        author_name = (
            author_element.get_text(" ", strip=True)
            if author_element
            else None
        )

        # Post text
        text_element = post.select_one(
            ".message-body"
        )

        text = (
            text_element.get_text(
                " ",
                strip=True
            )
            if text_element
            else None
        )

        # Date/time
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
            "created_at": created_at,
            "text": text
        })

    return {
        **thread,
        "post_count": len(posts),
        "posts": posts
    }


def main():

    print("=" * 40)
    print("AAPC PAGE 3 CONTENT TEST")
    print("=" * 40)

    # --------------------------------
    # Step 1: Get thread list
    # --------------------------------

    threads = get_thread_links()

    print("\nThreads discovered:", len(threads))

    # We only want the first 50 actual threads
    threads = threads[:50]

    print("Threads selected:", len(threads))

    # --------------------------------
    # Step 2: Fetch each thread
    # --------------------------------

    results = []

    for index, thread in enumerate(threads, start=1):

        print("\n--------------------------------")
        print(f"[{index}/{len(threads)}] {thread['title']}")
        print(thread["url"])

        result = get_thread_posts(thread)

        print("  Posts found:", result["post_count"])

        results.append(result)

        # Small delay between requests
        time.sleep(0.5)

    # --------------------------------
    # Step 3: Save
    # --------------------------------

    output_file = "aapc_page3_threads.json"

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

    # --------------------------------
    # Step 4: Summary
    # --------------------------------

    total_posts = sum(
        item["post_count"]
        for item in results
    )

    successful_threads = sum(
        1
        for item in results
        if item["post_count"] > 0
    )

    print("\n")
    print("=" * 40)
    print("FINAL RESULT")
    print("=" * 40)

    print("Threads processed:", len(results))
    print("Threads with posts:", successful_threads)
    print("Total posts collected:", total_posts)

    print("\nSaved to:", output_file)

    print("\nFirst 5 threads:")

    for item in results[:5]:

        print(
            f"- {item['title']} "
            f"({item['post_count']} posts)"
        )


if __name__ == "__main__":
    main()