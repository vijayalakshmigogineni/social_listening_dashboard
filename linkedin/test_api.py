import os

if os.environ.get("APIFY_TOKEN"):
    print("APIFY_TOKEN is set")
else:
    print("APIFY_TOKEN is NOT set")
