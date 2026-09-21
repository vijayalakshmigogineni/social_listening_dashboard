import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

url = "https://mcp.humana.com/tad/tad_new/Search.aspx?searchtype=beginswith&docbegin=E&policyType=medical"

print("=" * 80)
print("HUMANA - SEARCH RESULTS FORM INSPECTION")
print("=" * 80)

response = requests.get(url, timeout=30)

print("\nSTATUS:", response.status_code)
print("FINAL URL:", response.url)

soup = BeautifulSoup(response.text, "html.parser")


# ------------------------------------------------------------
# FORMS
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("1. FORMS")
print("=" * 80)

forms = soup.find_all("form")

print("Number of forms:", len(forms))

for i, form in enumerate(forms, 1):

    print("\nFORM", i)
    print("METHOD:", form.get("method"))
    print("ACTION:", form.get("action"))
    print(
        "FULL ACTION:",
        urljoin(response.url, form.get("action") or "")
    )


# ------------------------------------------------------------
# INPUTS
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("2. INPUT FIELDS")
print("=" * 80)

for inp in soup.find_all("input"):

    print(
        "type=", inp.get("type"),
        "| name=", inp.get("name"),
        "| id=", inp.get("id"),
        "| value=", inp.get("value")
    )


# ------------------------------------------------------------
# SELECTS
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("3. SELECT FIELDS")
print("=" * 80)

for select in soup.find_all("select"):

    print(
        "name=", select.get("name"),
        "| id=", select.get("id")
    )

    for option in select.find_all("option"):

        print(
            "   OPTION:",
            option.get("value"),
            "|",
            option.get_text(" ", strip=True)
        )


# ------------------------------------------------------------
# SEARCH-RELATED ELEMENTS
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("4. SEARCH-RELATED ELEMENTS")
print("=" * 80)

for element in soup.find_all(
    ["input", "button", "a"]
):

    text = element.get_text(" ", strip=True)

    combined = str(element).lower()

    if (
        "search" in combined
        or "criteria" in combined
        or "keyword" in combined
    ):

        print("\n", str(element)[:2000])


print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)