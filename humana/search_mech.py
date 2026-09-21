import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

url = "https://mcp.humana.com/tad/tad_new/home.aspx?type=provider"

print("=" * 80)
print("HUMANA - SEARCH MECHANISM TEST")
print("=" * 80)

response = requests.get(url, timeout=30)

print("\nSTATUS:", response.status_code)
print("FINAL URL:", response.url)

soup = BeautifulSoup(response.text, "html.parser")


# ------------------------------------------------------------
# 1. FIND ALL FORMS
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("1. FORMS FOUND")
print("=" * 80)

forms = soup.find_all("form")

print("Number of forms:", len(forms))

for i, form in enumerate(forms, 1):

    print("\n" + "-" * 70)
    print("FORM", i)

    print("METHOD:", form.get("method"))
    print("ACTION:", form.get("action"))
    print(
        "FULL ACTION:",
        urljoin(response.url, form.get("action") or "")
    )


# ------------------------------------------------------------
# 2. FIND INPUT FIELDS
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("2. INPUT FIELDS")
print("=" * 80)

inputs = soup.find_all("input")

print("Number of inputs:", len(inputs))

for inp in inputs:

    print(
        "type=",
        inp.get("type"),
        "| name=",
        inp.get("name"),
        "| id=",
        inp.get("id"),
        "| value=",
        inp.get("value")
    )


# ------------------------------------------------------------
# 3. FIND SEARCH-RELATED ELEMENTS
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("3. SEARCH-RELATED ELEMENTS")
print("=" * 80)

for element in soup.find_all(
    ["input", "button", "a", "form"]
):

    text = element.get_text(" ", strip=True)

    combined = (
        str(element).lower()
    )

    if (
        "search" in combined
        or "keyword" in combined
        or "policy" in combined
    ):

        print("\nELEMENT:")
        print(str(element)[:1500])


# ------------------------------------------------------------
# 4. LINKS CONTAINING SEARCH/POLICY TERMS
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("4. RELEVANT LINKS")
print("=" * 80)

for link in soup.find_all("a", href=True):

    text = link.get_text(" ", strip=True)
    href = link.get("href")

    combined = (text + " " + href).lower()

    if any(
        word in combined
        for word in [
            "search",
            "policy",
            "preauth",
            "coverage"
        ]
    ):

        print(
            "TEXT:",
            text,
            "| URL:",
            urljoin(response.url, href)
        )


print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)