"""Shared helpers for the Medical Billing Live feasibility probes.

The forum is SMF 2.0.19 at /members/. Three site quirks drive everything here:

  1. Guest URLs carry a PHPSESSID that rotates per request, so any URL used as
     an identifier has to be stripped before it is stored or compared.
  2. The host intermittently returns 503 under sequential access, regardless
     of query-string style. Measured over 6 trials each, ";" and "&" both
     returned 200 every time, so the 503s are load-related, not syntax-
     related. Everything therefore goes through fetch(), which retries.
  3. Pages declare ISO-8859-1 but actually carry cp1252 bytes (smart quotes,
     nbsp), so the declared charset decodes them wrongly.
"""

import re
import time
import requests

SITE = "https://www.medicalbillinglive.com"
FORUM = SITE + "/members/index.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# Pause between requests. The host 503s under fast sequential access.
DELAY_SECONDS = 2.0

# Boards as listed on the public index, with the post/topic counts the index
# itself prints. "rcm" marks the boards carrying revenue-cycle discussion.
BOARDS = [
    {"id": 13, "name": "New!", "rcm": False},
    {"id": 6, "name": "General Questions", "rcm": True},
    {"id": 5, "name": "NPI Numbers", "rcm": True},
    {"id": 8, "name": "Coding", "rcm": True},
    {"id": 7, "name": "Billing", "rcm": True},
    {"id": 4, "name": "Facility Billing", "rcm": True},
    {"id": 2, "name": "Insurance Payments", "rcm": True},
    {"id": 3, "name": "Patient Billing", "rcm": True},
    {"id": 9, "name": "HIPAA", "rcm": True},
    {"id": 10, "name": "Starting Your Own Medical Billing Business", "rcm": False},
    {"id": 14, "name": "Online Medical Billing Courses - Student Section", "rcm": False},
    {"id": 11, "name": "Medical Billing Software Reviews", "rcm": False},
    {"id": 12, "name": "Medical Billing Software Questions", "rcm": False},
]

TOPICS_PER_PAGE = 20


def clean_url(url):
    """Drop the rotating guest session id so a URL can serve as an identifier."""

    if not url:
        return url

    url = re.sub(r"[?&]PHPSESSID=[0-9a-f]+", "", url)

    # PHPSESSID is usually the *first* param, so removing it strands the
    # rest behind an "&" with no "?" in front. Promote that first "&".
    if "?" not in url and "&" in url:
        url = url.replace("&", "?", 1)

    url = url.replace("index.php?&", "index.php?")

    return url.rstrip("?&")


def fetch_response(url, attempts=4):
    """GET with retry, returning the response so headers stay available.

    A 503 here is transient load, so a retried request is the honest
    measurement of whether an endpoint exists.
    """

    response = None

    for attempt in range(attempts):

        if attempt:
            time.sleep(DELAY_SECONDS * (attempt + 1))

        response = requests.get(url, headers=HEADERS, timeout=30)

        if response.status_code == 200:
            # Declared ISO-8859-1, actually cp1252.
            response.encoding = "cp1252"
            return response

    return response


def fetch(url, attempts=4):
    """GET with retry. Returns (status_code, text) and decodes as cp1252."""

    response = fetch_response(url, attempts=attempts)

    if response is None:
        return None, ""

    if response.status_code == 200:
        return response.status_code, response.text

    return response.status_code, ""


def board_url(board_id, start=0):
    """Board page URL. SMF pages by item offset, not page number."""

    return f"{SITE}/members/index.php/board,{board_id}.{start}.html"


def topic_url(topic_id, start=0):
    return f"{SITE}/members/index.php/topic,{topic_id}.{start}.html"


def parse_topic_id(url):
    match = re.search(r"/topic,(\d+)\.", url or "")
    return match.group(1) if match else None


def parse_msg_id(url):
    match = re.search(r"msg(\d+)", url or "")
    return match.group(1) if match else None


def parse_user_id(url):
    match = re.search(r"action=profile;u=(\d+)", url or "")
    return match.group(1) if match else None


def squash(text):
    """Collapse whitespace, including the nbsp this forum emits heavily."""

    if text is None:
        return None

    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
