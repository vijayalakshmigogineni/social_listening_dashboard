import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HOME_URL = "https://mcp.humana.com/tad/tad_new/home.aspx?type=provider"

SEARCH_TERM = "Epidural"

print("=" * 80)
print("HUMANA - KEYWORD SEARCH TEST")
print("=" * 80)

session = requests.Session()

# ------------------------------------------------------------
# STEP 1 - GET HOME PAGE
# ------------------------------------------------------------

print("\nSTEP 1 - GET HOME PAGE")

response = session.get(HOME_URL, timeout=30)

print("STATUS:", response.status_code)

if response.status_code != 200:
    raise SystemExit("Could not access Humana home page.")

soup = BeautifulSoup(response.text, "html.parser")


# ------------------------------------------------------------
# STEP 2 - EXTRACT ASP.NET STATE FIELDS
# ------------------------------------------------------------

print("\nSTEP 2 - EXTRACT ASP.NET STATE")

viewstate = soup.find("input", {"name": "__VIEWSTATE"})
viewstate_generator = soup.find(
    "input",
    {"name": "__VIEWSTATEGENERATOR"}
)

if not viewstate:
    raise SystemExit("VIEWSTATE not found.")

print("VIEWSTATE found:", True)
print(
    "VIEWSTATEGENERATOR found:",
    bool(viewstate_generator)
)


# ------------------------------------------------------------
# STEP 3 - PREPARE SEARCH FORM
# ------------------------------------------------------------

print("\nSTEP 3 - PREPARE SEARCH")

data = {
    "__VIEWSTATE": viewstate.get("value", ""),
    "__VIEWSTATEGENERATOR": (
        viewstate_generator.get("value", "")
        if viewstate_generator
        else ""
    ),

    # Actual Humana search textbox
    "ctl00$ContentPlaceHolder1$CriteriaTextBox": SEARCH_TERM,

    # ASP.NET image button
    "ctl00$ContentPlaceHolder1$SearchButton.x": "1",
    "ctl00$ContentPlaceHolder1$SearchButton.y": "1",
}

print("SEARCH TERM:", SEARCH_TERM)


# ------------------------------------------------------------
# STEP 4 - SUBMIT SEARCH
# ------------------------------------------------------------

print("\nSTEP 4 - SUBMIT SEARCH")

search_response = session.post(
    HOME_URL,
    data=data,
    timeout=30
)

print("STATUS:", search_response.status_code)
print("FINAL URL:", search_response.url)


# ------------------------------------------------------------
# STEP 5 - READ RESULTS
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 5 - SEARCH RESULTS")
print("=" * 80)

result_soup = BeautifulSoup(
    search_response.text,
    "html.parser"
)

text = result_soup.get_text(
    "\n",
    strip=True
)

print(text[:12000])


# ------------------------------------------------------------
# STEP 6 - FIND POLICY LINKS / DOCUMENT REFERENCES
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 6 - POLICY / DOCUMENT LINKS")
print("=" * 80)

count = 0

for link in result_soup.find_all("a", href=True):

    link_text = link.get_text(" ", strip=True)
    href = link.get("href")

    if not link_text:
        continue

    # Print policy-looking links
    if (
        "policy" in link_text.lower()
        or "epidural" in link_text.lower()
        or "pain" in link_text.lower()
        or "stimulator" in link_text.lower()
        or "nerve" in link_text.lower()
    ):

        print("\nTEXT:", link_text)
        print("HREF:", urljoin(search_response.url, href))

        count += 1


print("\nPotential policy links:", count)


# ------------------------------------------------------------
# STEP 7 - LOOK FOR HUMANA DOCUMENT URLS IN HTML
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 7 - DCTM DOCUMENT REFERENCES")
print("=" * 80)

html = search_response.text

marker = "https://dctm.humana.com"

positions = []
start = 0

while True:

    position = html.find(marker, start)

    if position == -1:
        break

    positions.append(position)
    start = position + len(marker)


print("DCTM references found:", len(positions))

for position in positions[:20]:

    snippet = html[
        position:position + 800
    ]

    print("\n" + "-" * 70)
    print(snippet)


print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)