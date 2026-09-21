import requests
import json

LICENSE_URL = "https://api.coverage.cms.gov/v1/metadata/license-agreement/"
LCD_URL = "https://api.coverage.cms.gov/v1/data/lcd/"

LCD_ID = "39240"

print("=" * 80)
print("STEP 1 - GET CMS LICENSE TOKEN")
print("=" * 80)

response = requests.get(LICENSE_URL, timeout=30)

print("LICENSE STATUS:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise SystemExit

license_data = response.json()

token = license_data["data"][0]["Token"]

print("TOKEN FOUND: YES")
print("TOKEN LENGTH:", len(token))


print("\n" + "=" * 80)
print("STEP 2 - REQUEST NORIDIAN LCD")
print("=" * 80)

params = {
    "lcdid": LCD_ID
}

headers = {
    "Authorization": f"Bearer {token}"
}

response = requests.get(
    LCD_URL,
    params=params,
    headers=headers,
    timeout=30
)

print("LCD STATUS:", response.status_code)
print("LCD URL:", response.url)


print("\n" + "=" * 80)
print("STEP 3 - RESPONSE")
print("=" * 80)

try:
    result = response.json()

    print("TOP-LEVEL KEYS:")
    print(list(result.keys()))

    print("\nFULL JSON RESPONSE:")
    print(json.dumps(result, indent=2))

except Exception:
    print(response.text)