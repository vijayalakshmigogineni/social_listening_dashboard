import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HOME_URL = "https://mcp.humana.com/tad/tad_new/home.aspx?type=provider"
SEARCH_TERM = "Epidural"

print("=" * 80)
print("HUMANA - RETRIEVE SPECIFIC POLICY TEST")
print("=" * 80)

session = requests.Session()

# ------------------------------------------------------------
# STEP 1 - GET HOME PAGE
# ------------------------------------------------------------

print("\nSTEP 1 - GET HOME PAGE")

response = session.get(HOME_URL, timeout=30)

print("STATUS:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")

viewstate = soup.find("input", {"name": "__VIEWSTATE"})
viewstate_generator = soup.find(
    "input",
    {"name": "__VIEWSTATEGENERATOR"}
)

if not viewstate:
    raise SystemExit("VIEWSTATE not found.")

print("VIEWSTATE found:", True)
print("VIEWSTATEGENERATOR found:", bool(viewstate_generator))


# ------------------------------------------------------------
# STEP 2 - PERFORM EPIDURAL SEARCH
# ------------------------------------------------------------

print("\nSTEP 2 - SEARCH FOR:", SEARCH_TERM)

data = {
    "__VIEWSTATE": viewstate.get("value", ""),
    "__VIEWSTATEGENERATOR": (
        viewstate_generator.get("value", "")
        if viewstate_generator
        else ""
    ),

    "ctl00$ContentPlaceHolder1$CriteriaTextBox": SEARCH_TERM,

    "ctl00$ContentPlaceHolder1$SearchButton.x": "1",
    "ctl00$ContentPlaceHolder1$SearchButton.y": "1",
}

search_response = session.post(
    HOME_URL,
    data=data,
    timeout=30
)

print("SEARCH STATUS:", search_response.status_code)
print("SEARCH URL:", search_response.url)


# ------------------------------------------------------------
# STEP 3 - FIND THE TARGET POLICY ROW
# ------------------------------------------------------------

print("\nSTEP 3 - FIND TARGET POLICY")

result_soup = BeautifulSoup(
    search_response.text,
    "html.parser"
)

target_text = "Injections for Pain Conditions - Medicare Advantage"

target_link = None

for link in result_soup.find_all("a"):

    text = link.get_text(" ", strip=True)

    if text == target_text:

        target_link = link
        break


if not target_link:

    print("TARGET POLICY NOT FOUND")
    print("\nAvailable policy names:")

    for link in result_soup.find_all("a"):

        text = link.get_text(" ", strip=True)

        if text:
            print("-", text)

    raise SystemExit()


print("TARGET FOUND:")
print(target_link.get_text(" ", strip=True))

print("\nTARGET HREF:")
print(target_link.get("href"))


# ------------------------------------------------------------
# STEP 4 - EXTRACT THE POSTBACK TARGET
# ------------------------------------------------------------

href = target_link.get("href", "")

print("\nSTEP 4 - POSTBACK INFORMATION")

print("HREF:")
print(href)


# Expected form:
# javascript:__doPostBack('CONTROL','ARGUMENT')

import re

match = re.search(
    r"__doPostBack\('([^']*)','([^']*)'\)",
    href
)

if not match:

    print("\nCould not parse postback.")
    raise SystemExit()

event_target = match.group(1)
event_argument = match.group(2)

print("\nEVENT TARGET:")
print(event_target)

print("\nEVENT ARGUMENT:")
print(event_argument)


# ------------------------------------------------------------
# STEP 5 - SUBMIT POSTBACK
# ------------------------------------------------------------

print("\nSTEP 5 - SUBMIT POLICY POSTBACK")

# Need the current VIEWSTATE from the search result page

search_viewstate = result_soup.find(
    "input",
    {"name": "__VIEWSTATE"}
)

search_viewstate_generator = result_soup.find(
    "input",
    {"name": "__VIEWSTATEGENERATOR"}
)

if not search_viewstate:

    raise SystemExit(
        "Search result VIEWSTATE not found."
    )


post_data = {
    "__EVENTTARGET": event_target,
    "__EVENTARGUMENT": event_argument,

    "__VIEWSTATE": search_viewstate.get("value", ""),

    "__VIEWSTATEGENERATOR": (
        search_viewstate_generator.get("value", "")
        if search_viewstate_generator
        else ""
    ),
}


policy_response = session.post(
    search_response.url,
    data=post_data,
    timeout=30
)

print("POLICY RESPONSE STATUS:")
print(policy_response.status_code)

print("\nPOLICY RESPONSE URL:")
print(policy_response.url)

print("\nCONTENT TYPE:")
print(policy_response.headers.get("content-type"))


# ------------------------------------------------------------
# STEP 6 - INSPECT RESPONSE
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 6 - POLICY RESPONSE")
print("=" * 80)

policy_soup = BeautifulSoup(
    policy_response.text,
    "html.parser"
)

print("\nPAGE TITLE:")

if policy_soup.title:
    print(policy_soup.title.get_text(strip=True))
else:
    print("No title")


print("\nPAGE TEXT:")

policy_text = policy_soup.get_text(
    "\n",
    strip=True
)

print(policy_text[:15000])


# ------------------------------------------------------------
# STEP 7 - FIND DOCUMENT / PDF LINKS
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 7 - DOCUMENT LINKS")
print("=" * 80)

for link in policy_soup.find_all(
    "a",
    href=True
):

    text = link.get_text(
        " ",
        strip=True
    )

    href = link.get("href")

    if (
        "pdf" in href.lower()
        or "dctm" in href.lower()
        or "document" in href.lower()
        or "policy" in text.lower()
    ):

        print("\nTEXT:", text)
        print(
            "URL:",
            urljoin(
                policy_response.url,
                href
            )
        )


print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)