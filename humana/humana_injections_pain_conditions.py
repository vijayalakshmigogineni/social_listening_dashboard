import requests
from bs4 import BeautifulSoup
import re

HOME_URL = "https://mcp.humana.com/tad/tad_new/home.aspx?type=provider"

SEARCH_TERM = "Epidural"

TARGET_POLICY = "Injections for Pain Conditions - Medicare Advantage"

OUTPUT_FILE = "humana_injections_pain_conditions.pdf"


print("=" * 80)
print("HUMANA - DOWNLOAD ACTUAL POLICY PDF")
print("=" * 80)


session = requests.Session()


# ------------------------------------------------------------
# STEP 1 - GET HOME PAGE
# ------------------------------------------------------------

response = session.get(
    HOME_URL,
    timeout=30
)

print("\nSTEP 1")
print("Home status:", response.status_code)

soup = BeautifulSoup(
    response.text,
    "html.parser"
)

viewstate = soup.find(
    "input",
    {"name": "__VIEWSTATE"}
)

viewstate_generator = soup.find(
    "input",
    {"name": "__VIEWSTATEGENERATOR"}
)


# ------------------------------------------------------------
# STEP 2 - SEARCH EPIDURAL
# ------------------------------------------------------------

print("\nSTEP 2")
print("Searching for:", SEARCH_TERM)

data = {
    "__VIEWSTATE": viewstate.get("value", ""),

    "__VIEWSTATEGENERATOR":
        viewstate_generator.get("value", "")
        if viewstate_generator
        else "",

    "ctl00$ContentPlaceHolder1$CriteriaTextBox":
        SEARCH_TERM,

    "ctl00$ContentPlaceHolder1$SearchButton.x": "1",
    "ctl00$ContentPlaceHolder1$SearchButton.y": "1",
}

search_response = session.post(
    HOME_URL,
    data=data,
    timeout=30
)

print("Search status:", search_response.status_code)
print("Search URL:", search_response.url)


# ------------------------------------------------------------
# STEP 3 - FIND TARGET POLICY
# ------------------------------------------------------------

print("\nSTEP 3")
print("Finding target policy...")

search_soup = BeautifulSoup(
    search_response.text,
    "html.parser"
)

target_link = None

for link in search_soup.find_all("a"):

    text = link.get_text(
        " ",
        strip=True
    )

    if text == TARGET_POLICY:

        target_link = link
        break


if not target_link:

    raise SystemExit(
        "Target policy was not found."
    )


print("Found:")
print(target_link.get_text(" ", strip=True))

href = target_link.get("href", "")

print("\nPostback:")
print(href)


# ------------------------------------------------------------
# STEP 4 - EXTRACT POSTBACK
# ------------------------------------------------------------

match = re.search(
    r"__doPostBack\('([^']*)','([^']*)'\)",
    href
)

if not match:

    raise SystemExit(
        "Could not extract postback."
    )

event_target = match.group(1)
event_argument = match.group(2)

print("\nEvent target:")
print(event_target)


# ------------------------------------------------------------
# STEP 5 - SUBMIT POSTBACK
# ------------------------------------------------------------

print("\nSTEP 5")
print("Opening actual policy document...")

result_viewstate = search_soup.find(
    "input",
    {"name": "__VIEWSTATE"}
)

result_generator = search_soup.find(
    "input",
    {"name": "__VIEWSTATEGENERATOR"}
)

post_data = {
    "__EVENTTARGET": event_target,
    "__EVENTARGUMENT": event_argument,

    "__VIEWSTATE":
        result_viewstate.get("value", ""),

    "__VIEWSTATEGENERATOR":
        result_generator.get("value", "")
        if result_generator
        else "",
}


policy_response = session.post(
    search_response.url,
    data=post_data,
    timeout=30
)

print("Policy status:", policy_response.status_code)

print("Policy URL:")
print(policy_response.url)

print("\nContent type:")
print(
    policy_response.headers.get(
        "content-type"
    )
)


# ------------------------------------------------------------
# STEP 6 - SAVE PDF
# ------------------------------------------------------------

if "application/pdf" not in (
    policy_response.headers.get(
        "content-type",
        ""
    ).lower()
):

    raise SystemExit(
        "Response is not a PDF."
    )


with open(
    OUTPUT_FILE,
    "wb"
) as f:

    f.write(
        policy_response.content
    )


print("\nSTEP 6")
print("PDF SAVED SUCCESSFULLY")

print("\nFile:")
print(OUTPUT_FILE)

print("\nSize:")
print(
    len(policy_response.content),
    "bytes"
)

print("\n" + "=" * 80)
print("DOWNLOAD COMPLETE")
print("=" * 80)