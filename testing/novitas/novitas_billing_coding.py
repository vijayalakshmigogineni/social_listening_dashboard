import requests

BASE_URL = "https://api.coverage.cms.gov/v1"

print("=" * 80)
print("NOVITAS - BILLING & CODING ARTICLE TEST")
print("=" * 80)


# -------------------------------------------------------------------
# STEP 1 - GET CMS LICENSE TOKEN
# -------------------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 1 - GET CMS LICENSE TOKEN")
print("=" * 80)

license_url = f"{BASE_URL}/metadata/license-agreement/"

license_response = requests.get(
    license_url,
    timeout=30
)

print("LICENSE STATUS:", license_response.status_code)

license_data = license_response.json()

token = license_data["data"][0]["Token"]

print("TOKEN FOUND:", bool(token))
print("TOKEN LENGTH:", len(token))


# -------------------------------------------------------------------
# STEP 2 - GET NOVITAS BILLING & CODING ARTICLES
# -------------------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 2 - GET NOVITAS BILLING & CODING ARTICLES")
print("=" * 80)

url = f"{BASE_URL}/reports/local-coverage-articles/"

params = {
    "contractor_id": 335
}

headers = {
    "Authorization": f"Bearer {token}"
}

response = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=30
)

print("ARTICLE STATUS:", response.status_code)

print("\nACTUAL URL:")
print(response.url)


if response.status_code != 200:
    print("\nERROR:")
    print(response.text[:5000])
    raise SystemExit()


data = response.json()


# -------------------------------------------------------------------
# STEP 3 - STRUCTURE
# -------------------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 3 - RESPONSE STRUCTURE")
print("=" * 80)

print("TOP LEVEL KEYS:")
print(list(data.keys()))

records = data.get("data", [])

print("\nDATA TYPE:")
print(type(records))

print("\nNUMBER OF RECORDS:")
print(len(records))


# -------------------------------------------------------------------
# STEP 4 - FIRST 10 ARTICLES
# -------------------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 4 - FIRST 10 NOVITAS ARTICLES")
print("=" * 80)

for i, record in enumerate(records[:10], start=1):

    print(f"\n--- ARTICLE {i} ---")

    if isinstance(record, dict):

        for key, value in record.items():
            print(f"{key}: {value}")

    else:
        print(record)


# -------------------------------------------------------------------
# STEP 5 - SEARCH FOR PAIN-RELATED ARTICLES
# -------------------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 5 - SEARCHING FOR PAIN-RELATED ARTICLES")
print("=" * 80)

pain_terms = [
    "pain",
    "epidural",
    "facet",
    "nerve",
    "spinal",
    "radiofrequency",
    "injection",
    "stimulator",
    "botulinum"
]

pain_matches = []

for record in records:

    if not isinstance(record, dict):
        continue

    title = str(record.get("title", "")).lower()

    if any(term in title for term in pain_terms):
        pain_matches.append(record)


print("PAIN-RELATED MATCHES:", len(pain_matches))


for i, record in enumerate(pain_matches[:20], start=1):

    print(f"\n--- PAIN ARTICLE {i} ---")

    for key, value in record.items():
        print(f"{key}: {value}")


print("\n" + "=" * 80)
print("DONE")
print("=" * 80)