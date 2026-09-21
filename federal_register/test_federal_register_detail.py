import requests

DOCUMENT_NUMBER = "2026-19015"

URL = f"https://www.federalregister.gov/api/v1/documents/{DOCUMENT_NUMBER}.json"

response = requests.get(URL, timeout=20)

print("HTTP Status:", response.status_code)
print("Request URL:", response.url)

print("=" * 100)

if response.status_code == 200:

    doc = response.json()

    print("TITLE:")
    print(doc.get("title"))

    print("\nDOCUMENT NUMBER:")
    print(doc.get("document_number"))

    print("\nPUBLICATION DATE:")
    print(doc.get("publication_date"))

    print("\nTYPE:")
    print(doc.get("type"))

    print("\nABSTRACT:")
    print(doc.get("abstract"))

    print("\nAGENCY:")
    print(doc.get("agencies"))

    print("\nEFFECTIVE ON:")
    print(doc.get("effective_on"))

    print("\nHTML URL:")
    print(doc.get("html_url"))

else:
    print("Request failed")
    print(response.text)