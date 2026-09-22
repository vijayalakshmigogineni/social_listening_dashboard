import requests

url = "https://api.coverage.cms.gov/docs/v1/swagger"

response = requests.get(url, timeout=30)

print("STATUS:", response.status_code)
print("CONTENT TYPE:", response.headers.get("content-type"))
print("URL:", response.url)

print("\nFIRST 5000 CHARACTERS:\n")
print(response.text[:5000])