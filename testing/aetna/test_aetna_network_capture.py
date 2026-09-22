"""
Uses a real headless browser (Playwright/Chromium) to load Aetna pages the same
way a person's browser would, and logs every XHR/fetch network request it makes.
This is the equivalent of opening Chrome DevTools -> Network tab.

Goal: find the actual data endpoint(s) behind the "What's New" / "CPB listing" /
"Periodic reviews" widgets on the medical CPB page, and behind the CPT code
precertification search box.
"""

import json
from playwright.sync_api import sync_playwright

TARGETS = [
    {
        "name": "Medical CPB page (What's New / CPB listing / Periodic reviews widgets)",
        "url": "https://www.aetna.com/health-care-professionals/clinical-policy-bulletins/medical-clinical-policy-bulletins.html",
        "interact": "cpb_widgets",
    },
    {
        "name": "Precertification lists page (CPT code search)",
        "url": "https://www.aetna.com/health-care-professionals/precertification/precertification-lists.html",
        "interact": "precert_search",
    },
]

captured = []


def log_request(request):
    rtype = request.resource_type
    if rtype in ("xhr", "fetch"):
        captured.append({
            "url": request.url,
            "method": request.method,
            "resource_type": rtype,
        })


def try_cpb_widgets(page):
    # Try clicking the "What's new" tab/dropdowns if present
    for label in ["What's new", "CPB listing", "Periodic reviews"]:
        try:
            el = page.get_by_text(label, exact=False).first
            el.click(timeout=3000)
            page.wait_for_timeout(1500)
        except Exception as e:
            print(f"  (could not click '{label}': {type(e).__name__})")

    # Try interacting with any visible <select> dropdowns
    selects = page.locator("select")
    count = selects.count()
    print(f"  Found {count} <select> dropdowns on page")
    for i in range(min(count, 6)):
        try:
            sel = selects.nth(i)
            options = sel.locator("option")
            if options.count() > 1:
                sel.select_option(index=1)
                page.wait_for_timeout(1500)
        except Exception as e:
            print(f"  (select {i} interaction failed: {type(e).__name__})")


def try_precert_search(page):
    try:
        box = page.locator("input[type='text']").first
        box.fill("64483")
        page.wait_for_timeout(500)
        page.keyboard.press("Enter")
        page.wait_for_timeout(2500)
    except Exception as e:
        print(f"  (precert search interaction failed: {type(e).__name__})")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0")
    page = context.new_page()
    page.on("request", log_request)

    for target in TARGETS:
        print("\n" + "=" * 90)
        print(target["name"])
        print("=" * 90)
        print("URL:", target["url"])

        captured.clear()

        try:
            page.goto(target["url"], timeout=45000, wait_until="networkidle")
        except Exception as e:
            print("Initial load error (continuing anyway):", type(e).__name__, str(e))

        print(f"\nXHR/fetch requests during initial load: {len(captured)}")
        for req in captured:
            print(f"  [{req['method']}] {req['url']}")

        if target["interact"] == "cpb_widgets":
            try_cpb_widgets(page)
        elif target["interact"] == "precert_search":
            try_precert_search(page)

        print(f"\nXHR/fetch requests AFTER interaction (cumulative): {len(captured)}")
        for req in captured:
            print(f"  [{req['method']}] {req['url']}")

    browser.close()

print("\nDone.")
