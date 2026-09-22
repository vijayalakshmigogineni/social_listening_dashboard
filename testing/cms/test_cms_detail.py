import requests

LICENSE_URL = "https://api.coverage.cms.gov/v1/metadata/license-agreement/"

response = requests.get(
    LICENSE_URL,
    timeout=30
)

print("Status:", response.status_code)

if response.status_code != 200:
    print(response.text[:5000])
else:
    payload = response.json()
    meta = payload.get("meta", {})
    status = meta.get("status", {})
    notes = meta.get("notes", "").replace("\r\n", "\n").strip()
    records = payload.get("data", [])

    print("=" * 80)
    print("CMS LICENSE AGREEMENT")
    print("=" * 80)
    print(f"API Status: {status.get('id')} - {status.get('message')}")

    for i, rec in enumerate(records, start=1):
        print(f"\nRecord [{i}]")
        for key, value in rec.items():
            print(f"    {key}: {value}")

    print("\n" + "-" * 80)
    print("License Notes")
    print("-" * 80)
    print(notes)
    print("=" * 80)
