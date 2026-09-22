import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re


URL = "https://dominoapps.palmettogba.com/palmetto/prior.nsf"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def main():

    print("=" * 70)
    print("PALMETTO GBA - PRIOR AUTHORIZATION EXTRACTION")
    print("=" * 70)

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30,
        verify=False
    )

    print()
    print("Status:", response.status_code)
    print("URL:", response.url)
    print("Content Length:", len(response.text))

    if response.status_code != 200:
        print("Could not fetch page.")
        return

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    title = ""

    if soup.title:
        title = clean_text(
            soup.title.get_text()
        )

    print()
    print("TITLE:")
    print(title)

    # -----------------------------------------------------
    # HEADINGS
    # -----------------------------------------------------

    print()
    print("HEADINGS:")
    print("-" * 70)

    headings = []

    for tag in soup.find_all([
        "h1",
        "h2",
        "h3",
        "h4"
    ]):

        text = clean_text(
            tag.get_text(" ", strip=True)
        )

        if text:
            headings.append(text)
            print(text)

    # -----------------------------------------------------
    # LINKS
    # -----------------------------------------------------

    print()
    print("LINKS:")
    print("-" * 70)

    links = []

    for a in soup.find_all(
        "a",
        href=True
    ):

        text = clean_text(
            a.get_text(" ", strip=True)
        )

        href = a.get("href")

        if not href:
            continue

        absolute_url = urljoin(
            URL,
            href
        )

        if text:

            link_data = {
                "text": text,
                "url": absolute_url
            }

            links.append(
                link_data
            )

            print(
                f"{text} -> {absolute_url}"
            )

    # -----------------------------------------------------
    # MAIN TEXT
    # -----------------------------------------------------

    for tag in soup([
        "script",
        "style",
        "noscript"
    ]):
        tag.decompose()

    body_text = clean_text(
        soup.get_text(" ", strip=True)
    )

    print()
    print("PAGE TEXT:")
    print("-" * 70)

    print(
        body_text[:5000]
    )

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    output = {

        "source": "Palmetto GBA",

        "source_type":
            "Medicare Administrative Contractor",

        "topic":
            "Prior Authorization",

        "url": URL,

        "title": title,

        "headings": headings,

        "links": links,

        "content": body_text
    }

    with open(
        "palmetto_prior_authorization_raw.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 70)
    print("Saved:")
    print("palmetto_prior_authorization_raw.json")
    print("=" * 70)


if __name__ == "__main__":
    main()