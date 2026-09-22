import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.aapc.com/discuss/forums/billing-reimbursement.583/"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_threads(url):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    print("URL:", url)
    print("Status:", response.status_code)

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    threads = []

    for link in soup.select(
        'a[data-preview-url*="/threads/"]'
    ):

        title = link.get_text(" ", strip=True)
        href = link.get("href")

        if title and href:
            threads.append({
                "title": title,
                "url": href
            })

    return threads


def main():

    urls = [
        BASE_URL,
        BASE_URL + "page-2",
        BASE_URL + "page-3"
    ]

    for url in urls:

        print("\n==============================")

        threads = get_threads(url)

        print("Threads found:", len(threads))

        for thread in threads[:10]:

            print(
                "-",
                thread["title"]
            )

            print(
                " ",
                thread["url"]
            )


if __name__ == "__main__":
    main()