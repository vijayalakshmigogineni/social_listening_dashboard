import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

URL = "https://www.aapc.com/discuss/threads/87798-billing-multiple-units.162540/"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(URL, headers=headers, timeout=30)

print("Status:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")


# --------------------------------------------------
# THREAD INFORMATION
# --------------------------------------------------

title_element = soup.select_one("h1")

title = (
    title_element.get_text(" ", strip=True)
    if title_element
    else None
)

# Extract thread ID from URL
thread_id = URL.rstrip("/").split(".")[-1]

print("\n==============================")
print("THREAD")
print("==============================")

print("Thread ID:", thread_id)
print("Title:", title)
print("URL:", URL)


# --------------------------------------------------
# POSTS
# --------------------------------------------------

posts = soup.select("article.message.message--post")

print("\nNumber of posts:", len(posts))


for index, post in enumerate(posts, start=1):

    print("\n==============================")
    print(f"POST {index}")
    print("==============================")

    # Post ID
    post_id = post.get("data-content")

    if post_id:
        post_id = post_id.replace("post-", "")

    print("Post ID:", post_id)


    # Author
    author_element = post.select_one(".message-name .username")

    author_name = (
        author_element.get_text(" ", strip=True)
        if author_element
        else None
    )

    print("Author:", author_name)


    # Author profile URL
    author_profile_url = None

    if author_element and author_element.get("href"):
        author_profile_url = urljoin(
            "https://www.aapc.com",
            author_element["href"]
        )

    print("Author Profile:", author_profile_url)


    # Author ID
    author_id = None

    if author_element:
        author_id = author_element.get("data-user-id")

    print("Author ID:", author_id)


    # User title / role
    role_element = post.select_one(".message-userTitle")

    author_role = (
        role_element.get_text(" ", strip=True)
        if role_element
        else None
    )

    print("Author Role:", author_role)


    # Location
    location = None

   

    location_element = post.select_one(
    ".message-userExtras a[href*='location-info']"
    )

    location = (
        location_element.get_text(" ", strip=True)
        if location_element
        else None
    )

    print("Location:", location)

    # Date / time
    time_element = post.select_one("time.u-dt")

    created_at = None
    timestamp = None

    if time_element:

        created_at = time_element.get("datetime")
        timestamp = time_element.get("data-timestamp")

    print("Created At:", created_at)
    print("Timestamp:", timestamp)


    # Post number
    post_number = None

    attribution = post.select_one(
        ".message-attribution-opposite"
    )

    if attribution:
        links = attribution.select("a")

        for link in links:
            text = link.get_text(strip=True)

            if text.startswith("#"):
                post_number = text
                break

    print("Post Number:", post_number)


    # Post URL
    post_url = None

    if post_id:
        post_url = (
            f"https://www.aapc.com"
            f"/discuss/threads/87798-billing-multiple-units.162540/"
            f"post-{post_id}"
        )

    print("Post URL:", post_url)


    # Actual message text
    message_element = post.select_one(
        ".message-body .bbWrapper"
    )

    text = (
        message_element.get_text(
            "\n",
            strip=True
        )
        if message_element
        else None
    )

    print("\nTEXT:")
    print(text)