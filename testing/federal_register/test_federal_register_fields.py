import requests

DOCUMENT_NUMBER = "2026-19015"

URL = f"https://www.federalregister.gov/api/v1/documents/{DOCUMENT_NUMBER}.json"

response = requests.get(URL, timeout=20)

print("HTTP Status:", response.status_code)
print("Request URL:", response.url)

print("=" * 100)

if response.status_code == 200:

    doc = response.json()

    print("AVAILABLE FIELDS")
    print("=" * 100)

    for key, value in doc.items():

        if isinstance(value, (dict, list)):
            print(f"\n{key}:")
            print(value)

        else:
            print(f"{key}: {value}")

else:
    print("Request failed")
    print(response.text)