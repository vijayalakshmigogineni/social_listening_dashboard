import requests
import json

BASE_URL = "https://api.coverage.cms.gov/v1"

print("=" * 80)
print("STEP 1 - GET CMS LICENSE TOKEN")
print("=" * 80)

license_url = f"{BASE_URL}/metadata/license-agreement/"

license_response = requests.get(license_url, timeout=30)

print("LICENSE STATUS:", license_response.status_code)

license_data = license_response.json()

token = license_data["data"][0]["Token"]

print("TOKEN FOUND:", bool(token))
print("TOKEN LENGTH:", len(token))


print("\n" + "=" * 80)
print("STEP 2 - SEARCH NORIDIAN BILLING & CODING ARTICLES")
print("=" * 80)

url = f"{BASE_URL}/reports/local-coverage-articles/"

params = {
    "contractor_id": 357
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
print("REQUEST URL:", response.url)


print("\n" + "=" * 80)
print("STEP 3 - TOP LEVEL STRUCTURE")
print("=" * 80)

data = response.json()

print("TOP-LEVEL KEYS:")
print(list(data.keys()))

print("\nDATA TYPE:")
print(type(data.get("data")))

if isinstance(data.get("data"), list):
    print("NUMBER OF RECORDS:", len(data["data"]))


print("\n" + "=" * 80)
print("STEP 4 - SHOW FIRST 10 ARTICLES")
print("=" * 80)

records = data.get("data", [])

for i, record in enumerate(records[:10], start=1):

    print(f"\n--- ARTICLE {i} ---")

    if isinstance(record, dict):
        for key, value in record.items():
            print(f"{key}: {value}")
    else:
        print(record)


print("\n" + "=" * 80)
print("DONE")
print("=" * 80)