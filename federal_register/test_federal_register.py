import requests

URL = "https://www.federalregister.gov/api/v1/documents.json"

params = {
    "per_page": 20,
    "order": "newest",
    "conditions[term]": "Medical coding and billing",
    
}

response = requests.get(URL, params=params, timeout=20)

print("HTTP Status:", response.status_code)
print("Request URL:", response.url)

data = response.json()

print("Total matching documents:", data.get("count"))
print("Documents returned:", len(data.get("results", [])))

print("=" * 100)

for i, doc in enumerate(data.get("results", []), start=1):

    print(f"\nDOCUMENT {i}")
    print("-" * 80)

    print("Title:", doc.get("title"))
    print("Document number:", doc.get("document_number"))
    print("Publication date:", doc.get("publication_date"))
    print("Type:", doc.get("type"))
    print("Abstract:", doc.get("abstract"))
    print("URL:", doc.get("html_url"))