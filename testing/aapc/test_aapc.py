import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import time


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://www.aapc.com"

FORUM_URL = (
    "https://www.aapc.com/discuss/forums/"
    "billing-reimbursement.583/"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

OUTPUT_FILE = "aapc_threads_detailed.json"


# ============================================================
# HELPER FUNCTION
# ============================================================

def fetch_page(url):
    """
    Fetch a webpage and return BeautifulSoup object.
    """

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return BeautifulSoup(
        response.text,
        "html.parser"
    )


# ============================================================
# 1. FETCH FORUM PAGE
# ============================================================

print("\nFetching AAPC forum page...")

soup = fetch_page(FORUM_URL)

print("Forum page fetched successfully.")


# ============================================================
# 2. FIND ALL STRUCT ITEMS
# ============================================================

all_rows = soup.select(
    "div.structItem"
)

print(
    "Total structItem rows found:",
    len(all_rows)
)


# ============================================================
# 3. KEEP ONLY ACTUAL THREAD ROWS
# ============================================================

thread_rows = []

for row in all_rows:

    title_link = row.select_one(
        ".structItem-title a"
    )

    if not title_link:
        continue

    href = title_link.get(
        "href",
        ""
    )

    # Only keep actual thread URLs
    if "/discuss/threads/" not in href:
        continue

    thread_rows.append(row)


print(
    "Actual thread rows found:",
    len(thread_rows)
)


# ============================================================
# 4. EXTRACT THREADS
# ============================================================

threads = []


for index, row in enumerate(
    thread_rows,
    1
):

    print("\n")
    print("=" * 80)

    # --------------------------------------------------------
    # TITLE + URL
    # --------------------------------------------------------

    title_link = row.select_one(
        ".structItem-title a"
    )

    title = title_link.get_text(
        " ",
        strip=True
    )

    thread_url = urljoin(
        BASE_URL,
        title_link.get("href")
    )


    print(
        f"[{index}/{len(thread_rows)}] Fetching:"
    )

    print(title)


    # --------------------------------------------------------
    # THREAD ID
    # --------------------------------------------------------

    thread_id = None

    href = title_link.get(
        "href",
        ""
    )

    # Example:
    # /discuss/threads/example.236380/

    if "." in href:

        try:

            thread_part = href.rstrip(
                "/"
            ).split(".")[-1]

            if thread_part.isdigit():

                thread_id = thread_part

        except Exception:

            thread_id = None


    # --------------------------------------------------------
    # AUTHOR
    # --------------------------------------------------------

    author_element = row.select_one(
        ".structItem-parts .username"
    )

    author = (
        author_element.get_text(
            " ",
            strip=True
        )
        if author_element
        else None
    )

    author_id = (
        author_element.get(
            "data-user-id"
        )
        if author_element
        else None
    )


    # --------------------------------------------------------
    # ORIGINAL DATE
    # --------------------------------------------------------

    date_element = row.select_one(
        ".structItem-startDate time"
    )

    published_date = (
        date_element.get(
            "datetime"
        )
        if date_element
        else None
    )

    published_timestamp = (
        date_element.get(
            "data-timestamp"
        )
        if date_element
        else None
    )

    published_display = (
        date_element.get_text(
            " ",
            strip=True
        )
        if date_element
        else None
    )


    # --------------------------------------------------------
    # REPLIES + VIEWS
    # --------------------------------------------------------

    meta = row.select_one(
        ".structItem-cell--meta"
    )

    replies = None

    views = None


    if meta:

        values = meta.select(
            "dl"
        )

        for item in values:

            label = item.select_one(
                "dt"
            )

            value = item.select_one(
                "dd"
            )

            if not label or not value:
                continue

            label_text = label.get_text(
                " ",
                strip=True
            )

            value_text = value.get_text(
                " ",
                strip=True
            )


            if label_text == "Replies":

                replies = value_text


            elif label_text == "Views":

                views = value_text


    # --------------------------------------------------------
    # LATEST ACTIVITY
    # --------------------------------------------------------

    latest_element = row.select_one(
        ".structItem-latestDate"
    )

    latest_activity = (
        latest_element.get(
            "datetime"
        )
        if latest_element
        else None
    )

    latest_timestamp = (
        latest_element.get(
            "data-timestamp"
        )
        if latest_element
        else None
    )

    latest_display = (
        latest_element.get_text(
            " ",
            strip=True
        )
        if latest_element
        else None
    )


    # --------------------------------------------------------
    # LATEST AUTHOR
    # --------------------------------------------------------

    latest_author_element = row.select_one(
        ".structItem-cell--latest .username"
    )

    latest_author = (
        latest_author_element.get_text(
            " ",
            strip=True
        )
        if latest_author_element
        else None
    )

    latest_author_id = (
        latest_author_element.get(
            "data-user-id"
        )
        if latest_author_element
        else None
    )


    # ========================================================
    # BASIC THREAD RECORD
    # ========================================================

    thread = {

        # Source information
        "source": "AAPC",

        "source_type": "professional_forum",

        "forum": "Billing/Reimbursement",


        # Thread identification
        "thread_id": thread_id,

        "title": title,

        "url": thread_url,


        # Original author
        "author": author,

        "author_id": author_id,


        # Original publication
        "published_date": published_date,

        "published_display": published_display,

        "published_timestamp": published_timestamp,


        # Engagement
        "replies": replies,

        "views": views,


        # Latest activity
        "latest_activity": latest_activity,

        "latest_display": latest_display,

        "latest_timestamp": latest_timestamp,

        "latest_author": latest_author,

        "latest_author_id": latest_author_id,


        # Detailed thread information
        "thread_details": {}

    }


    # ========================================================
    # 5. FETCH ACTUAL THREAD PAGE
    # ========================================================

    try:

        thread_soup = fetch_page(
            thread_url
        )


        # ----------------------------------------------------
        # PAGE TITLE
        # ----------------------------------------------------

        page_title = (
            thread_soup.title.get_text(
                " ",
                strip=True
            )
            if thread_soup.title
            else None
        )


        # ----------------------------------------------------
        # FIND POSTS
        # ----------------------------------------------------

        posts = thread_soup.select(
            "article.message"
        )


        print(
            "Posts found:",
            len(posts)
        )


        detailed_posts = []


        # ====================================================
        # 6. EXTRACT EVERY POST
        # ====================================================

        for post_index, post in enumerate(
            posts,
            1
        ):


            # ------------------------------------------------
            # POST ID
            # ------------------------------------------------

            post_id = post.get(
                "id"
            )


            # ------------------------------------------------
            # POST AUTHOR
            # ------------------------------------------------

            post_author_element = post.select_one(
                ".username"
            )

            post_author = (
                post_author_element.get_text(
                    " ",
                    strip=True
                )
                if post_author_element
                else None
            )

            post_author_id = (
                post_author_element.get(
                    "data-user-id"
                )
                if post_author_element
                else None
            )


            # ------------------------------------------------
            # POST DATE / TIME
            # ------------------------------------------------

            post_time_element = post.select_one(
                "time"
            )

            post_datetime = (
                post_time_element.get(
                    "datetime"
                )
                if post_time_element
                else None
            )

            post_timestamp = (
                post_time_element.get(
                    "data-timestamp"
                )
                if post_time_element
                else None
            )

            post_display_date = (
                post_time_element.get_text(
                    " ",
                    strip=True
                )
                if post_time_element
                else None
            )


            # ------------------------------------------------
            # POST CONTENT
            # ------------------------------------------------

            content_element = post.select_one(
                ".bbWrapper"
            )

            post_content = (
                content_element.get_text(
                    "\n",
                    strip=True
                )
                if content_element
                else None
            )


            # ------------------------------------------------
            # POST CONTENT HTML
            # ------------------------------------------------

            post_content_html = (
                str(content_element)
                if content_element
                else None
            )


            # ------------------------------------------------
            # POST NUMBER / DATA ATTRIBUTES
            # ------------------------------------------------

            post_number_attribute = post.get(
                "data-content"
            )

            post_user_id = post.get(
                "data-author"
            )


            # =================================================
            # POST RECORD
            # =================================================

            detailed_post = {

                "post_number": post_index,

                "post_id": post_id,

                "post_number_attribute":
                    post_number_attribute,

                "author": post_author,

                "author_id": post_author_id,

                "post_user_id":
                    post_user_id,

                "datetime": post_datetime,

                "display_date":
                    post_display_date,

                "timestamp":
                    post_timestamp,

                "content":
                    post_content,

                "content_html":
                    post_content_html,

                # Temporary debugging field
                "raw_html":
                    str(post)

            }


            detailed_posts.append(
                detailed_post
            )


        # ====================================================
        # 7. THREAD DETAILS
        # ====================================================

        thread["thread_details"] = {

            "page_title":
                page_title,

            "post_count":
                len(detailed_posts),

            "posts":
                detailed_posts,

            # Temporary debugging field
            "raw_html":
                str(thread_soup)

        }


    except Exception as e:

        print(
            "ERROR fetching thread:"
        )

        print(e)


        thread["thread_details"] = {

            "error":
                str(e),

            "post_count":
                0,

            "posts":
                []

        }


    # ========================================================
    # 8. ADD THREAD TO FINAL LIST
    # ========================================================

    threads.append(
        thread
    )


    # --------------------------------------------------------
    # Small delay between requests
    # --------------------------------------------------------

    time.sleep(1)


# ============================================================
# 9. FINAL SUMMARY
# ============================================================

print("\n")
print("=" * 80)

print(
    "TOTAL THREADS EXTRACTED:",
    len(threads)
)


# ============================================================
# 10. SAVE JSON
# ============================================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        threads,
        file,
        indent=2,
        ensure_ascii=False
    )


print(
    "\nSaved to:",
    OUTPUT_FILE
)


# ============================================================
# 11. DISPLAY SAMPLE RESULTS
# ============================================================

print("\n")
print("=" * 80)

print("SAMPLE RESULTS")

print("=" * 80)


for thread in threads[:5]:

    print("\n")
    print("-" * 70)

    print(
        "Thread ID:",
        thread["thread_id"]
    )

    print(
        "Title:",
        thread["title"]
    )

    print(
        "Author:",
        thread["author"]
    )

    print(
        "Author ID:",
        thread["author_id"]
    )

    print(
        "Published:",
        thread["published_date"]
    )

    print(
        "Replies:",
        thread["replies"]
    )

    print(
        "Views:",
        thread["views"]
    )

    print(
        "Latest Activity:",
        thread["latest_activity"]
    )

    print(
        "Latest Author:",
        thread["latest_author"]
    )

    print(
        "URL:",
        thread["url"]
    )


    details = thread.get(
        "thread_details",
        {}
    )

    posts = details.get(
        "posts",
        []
    )


    print(
        "Posts:",
        len(posts)
    )


    for post in posts:

        print(
            "\n  POST",
            post["post_number"]
        )

        print(
            "  Author:",
            post["author"]
        )

        print(
            "  Date:",
            post["datetime"]
        )

        print(
            "  Content:"
        )

        print(
            "  ",
            post["content"]
        )