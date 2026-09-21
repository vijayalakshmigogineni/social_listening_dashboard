import requests

BASE_URL = "https://api.coverage.cms.gov/v1"

url = f"{BASE_URL}/reports/local-coverage-final-lcds/"

params = {
    "contractor_id": 335
}

print("=" * 80)
print("NOVITAS - FINAL LCD TEST")
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

records = data.get("data", [])

print("\nDATA TYPE:")
print(type(records))

print("\nNUMBER OF RECORDS:")
print(len(records))


print("\n" + "=" * 80)
print("FIRST 10 NOVITAS LCDs")
print("=" * 80)

for i, record in enumerate(records[:10], start=1):

    print(f"\n--- LCD {i} ---")

    if isinstance(record, dict):

        for key, value in record.items():
            print(f"{key}: {value}")

    else:
        print(record)


print("\n" + "=" * 80)
print("SEARCHING FOR PAIN-RELATED LCDs")
print("=" * 80)

pain_terms = [
    "pain",
    "epidural",
    "facet",
    "nerve",
    "spinal",
    "radiofrequency",
    "injection",
    "stimulator"
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

    print(f"\n--- PAIN MATCH {i} ---")

    for key, value in record.items():
        print(f"{key}: {value}")


print("\n" + "=" * 80)
print("DONE")
print("=" * 80)