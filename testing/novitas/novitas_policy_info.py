import requests

BASE_URL = "https://api.coverage.cms.gov/v1"

print("=" * 80)
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


print("\n" + "=" * 80)
print("STEP 2 - GET NOVITAS LCD L36920")
print("=" * 80)

lcd_id = 36920

url = f"{BASE_URL}/data/lcd/"

params = {
    "lcdid": lcd_id
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

print("LCD STATUS:", response.status_code)

if response.status_code != 200:
    print(response.text[:5000])
    raise SystemExit()


data = response.json()

print("\n" + "=" * 80)
print("STEP 3 - POLICY CHANGE FIELDS")
print("=" * 80)

record = data["data"][0]

fields = [
    "lcd_id",
    "lcd_version",
    "title",
    "orig_det_eff_date",
    "rev_eff_date",
    "rev_end_date",
    "status",
    "last_updated",
    "issue",
    "issue_change"
]

for field in fields:

    print("\nFIELD:", field)

    if field in record:

        value = record[field]

        print("TYPE :", type(value).__name__)

        if isinstance(value, str) and len(value) > 3000:
            value = value[:3000] + "... [TRUNCATED]"

        print("VALUE:")
        print(value)

    else:
        print("NOT FOUND")


print("\n" + "=" * 80)
print("DONE")
print("=" * 80)