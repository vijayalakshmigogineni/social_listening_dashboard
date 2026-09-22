import os
from apify_client import ApifyClient

token = os.getenv("APIFY_TOKEN")

if not token:
    raise RuntimeError("APIFY_TOKEN is not set")

client = ApifyClient(token=token)

print("Apify client created successfully.")

user = client.user().get()

if user:
    print("Successfully connected to Apify!")
    print(f"Apify username: {user.username}")
else:
    print("Connected, but user information was not returned.")