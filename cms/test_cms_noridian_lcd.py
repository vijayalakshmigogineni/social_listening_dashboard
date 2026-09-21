import requests
import json

BASE_URL = "https://api.coverage.cms.gov"

contractor_id = 357

url = f"{BASE_URL}/v1/reports/whats-new/local/"

params = {
    "page": 1,
    "size": 20,
    "contractor_id": contractor_id
}

print("=" * 80)
print("CMS NORIDIAN LCD TEST")
print("=" * 80)

print("URL:", url)
print("PARAMETERS:")
print(json.dumps(params, indent=2))
print()

try:
    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    print("HTTP STATUS:", response.status_code)
    print("FINAL URL:", response.url)
    print("CONTENT TYPE:", response.headers.get("content-type"))
    print("RESPONSE SIZE:", len(response.content))
    print()

    if response.status_code != 200:
        print("ERROR:")
        print(response.text[:5000])
        raise SystemExit

    data = response.json()

    print("=" * 80)
    print("TOP-LEVEL STRUCTURE")
    print("=" * 80)

    if isinstance(data, dict):
        print("KEYS:")

        for key in data.keys():
            print(" -", key)

    print()

    print("=" * 80)
    print("RAW RESPONSE")
    print("=" * 80)

    print(json.dumps(data, indent=2)[:15000])

except requests.exceptions.Timeout:
    print("RESULT: REQUEST TIMED OUT")

except requests.exceptions.ConnectionError as e:
    print("RESULT: CONNECTION ERROR")
    print(e)

except Exception as e:
    print("RESULT:", type(e).__name__)
    print(e)