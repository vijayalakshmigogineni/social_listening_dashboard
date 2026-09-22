import requests
import json

BASE_URL = "https://api.coverage.cms.gov/v1"

url = f"{BASE_URL}/data/contractor/"

params = {
    "contractor_name": "NOVITAS"
}

print("=" * 80)
print("NOVITAS - CMS CONTRACTOR SEARCH")
print("=" * 80)

print("\nREQUEST URL:")
print(url)

print("\nPARAMETERS:")
print(params)

response = requests.get(
    url,
    params=params,
    timeout=30
)

print("\nSTATUS:", response.status_code)

print("\nACTUAL URL:")
print(response.url)

if response.status_code != 200:
    print("\nERROR:")
    print(response.text[:5000])
    raise SystemExit()

data = response.json()

print("\n" + "=" * 80)
print("TOP LEVEL STRUCTURE")
print("=" * 80)

print("TOP LEVEL KEYS:")
print(list(data.keys()))

print("\nDATA TYPE:")
print(type(data.get("data")))

records = data.get("data", [])

print("\nNUMBER OF RECORDS:")
print(len(records))

print("\n" + "=" * 80)
print("NOVITAS CONTRACTOR RECORDS")
print("=" * 80)

for i, record in enumerate(records, start=1):

    print(f"\n--- RECORD {i} ---")

    if isinstance(record, dict):

        for key, value in record.items():
            print(f"{key}: {value}")

    else:
        print(record)

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)