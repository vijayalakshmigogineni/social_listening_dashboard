import requests
from bs4 import BeautifulSoup


URL = "https://www.aapc.com/discuss/threads/bcbs-tx-denying-cpt-codes-15771-15772.236380/"


response = requests.get(
    URL,
    headers={
        "User-Agent": "Mozilla/5.0"
    },
    timeout=30
)

print("Status:", response.status_code)

response.raise_for_status()


soup = BeautifulSoup(
    response.text,
    "html.parser"
)


print("\nPAGE TITLE:")
print(soup.title.get_text(strip=True))


print("\nALL TEXT:")
print(
    soup.get_text(
        "\n",
        strip=True
    )[:10000]
)