import requests

url = "https://api.coverage.cms.gov/v1/reports/whats-new/local/"

params = {
    "page": 1,
    "size": 10
}

response = requests.get(
    url,
    params=params,
    timeout=30
)

print("Status:", response.status_code)
print("URL:", response.url)

if response.status_code != 200:
    print("\nResponse:")
    print(response.text[:5000])
else:
    payload = response.json()
    records = payload.get("data", [])

    print(f"\n{len(records)} record(s) on this page\n")

    for i, rec in enumerate(records, start=1):
        contractor = rec.get("contractor_name_type", "").replace("\r\n", " ")
        print(f"[{i}] {rec.get('document_display_id')} ({rec.get('document_type')})")
        print(f"    Title:      {rec.get('title')}")
        print(f"    Contractor: {contractor}")
        print(f"    Note:       {rec.get('note')}")
        print(f"    Updated:    {rec.get('updated_on')}")
        print(f"    Effective:  {rec.get('effective_date')}")
        print(f"    Retired:    {rec.get('retirement_date')}")
        print(f"    URL:        {rec.get('url')}")
        print("-" * 80)
