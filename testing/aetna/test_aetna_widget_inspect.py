from playwright.sync_api import sync_playwright

URL = "https://www.aetna.com/health-care-professionals/clinical-policy-bulletins/medical-clinical-policy-bulletins.html"

captured = []


def log_request(request):
    if "xmlfilter" in request.url or "aem-services" in request.url:
        captured.append({"url": request.url, "method": request.method})


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent="Mozilla/5.0")
    page.on("request", log_request)

    page.goto(URL, timeout=45000, wait_until="networkidle")

    print("=" * 90)
    print("ALL <select> ELEMENTS - outerHTML (truncated)")
    print("=" * 90)
    selects = page.locator("select")
    n = selects.count()
    for i in range(n):
        html = selects.nth(i).evaluate("el => el.outerHTML")
        print(f"\n--- select #{i} ---")
        print(html[:600])

    print("\n" + "=" * 90)
    print("TRYING TO SELECT REAL OPTIONS IN THE FIRST 'WHAT'S NEW' DROPDOWNS")
    print("=" * 90)

    captured.clear()

    # What's New has two selects: Status, Month (based on earlier text dump order)
    # Try selecting a non-placeholder option in each of the first few selects by label text
    for i in range(min(n, 4)):
        try:
            sel = selects.nth(i)
            options = sel.locator("option").all_text_contents()
            print(f"select #{i} options: {options}")
            if len(options) > 1:
                sel.select_option(index=1, force=True)
                page.wait_for_timeout(1200)
        except Exception as e:
            print(f"select #{i} failed: {type(e).__name__} {e}")

    page.wait_for_timeout(1500)

    print(f"\nxmlfilter/aem-services requests fired during this interaction: {len(captured)}")
    for c in captured:
        print(" ", c["method"], c["url"])

    browser.close()
