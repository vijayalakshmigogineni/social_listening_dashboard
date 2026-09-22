import requests
import json

BASE_URL = "https://api.coverage.cms.gov"

url = f"{BASE_URL}/v1/data/contractor/"

print("=" * 80)
print("CMS CONTRACTOR API - NORIDIAN TEST")
print("=" * 80)
print("URL:", url)
print()

try:
    response = requests.get(
        url,
        timeout=30
    )

    print("HTTP STATUS:", response.status_code)
    print("CONTENT TYPE:", response.headers.get("content-type"))
    print("RESPONSE SIZE:", len(response.content))
    print()

    if response.status_code != 200:
        print("ERROR RESPONSE:")
        print(response.text[:3000])
        raise SystemExit

    data = response.json()

    print("TOP-LEVEL TYPE:", type(data).__name__)
    print()

    # Show structure first
    if isinstance(data, dict):
        print("TOP-LEVEL KEYS:")
        for key in data.keys():
            print(" -", key)

    print()
    print("=" * 80)
    print("SEARCHING FOR NORIDIAN")
    print("=" * 80)

    # Convert response to text so we can locate every Noridian occurrence
    text = json.dumps(data, indent=2)

    lines = text.splitlines()

    matches = []

    for i, line in enumerate(lines):
        if "NORIDIAN" in line.upper():
            start = max(0, i - 5)
            end = min(len(lines), i + 8)

            matches.append(lines[start:end])

    if not matches:
        print("No NORIDIAN occurrence found.")
    else:
        print("Found", len(matches), "Noridian occurrence(s).")
        print()

        for index, block in enumerate(matches, start=1):
            print("-" * 80)
            print(f"MATCH {index}")
            print("-" * 80)

            for line in block:
                print(line)

except requests.exceptions.Timeout:
    print("REQUEST TIMED OUT")

except requests.exceptions.ConnectionError as e:
    print("CONNECTION ERROR")
    print(e)

except Exception as e:
    print("ERROR:", type(e).__name__)
    print(e)