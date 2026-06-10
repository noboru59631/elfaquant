from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 1000})
    page.goto("http://localhost:8000/")
    page.wait_for_load_state("networkidle")
    # Wait until balance is loaded (not "loading...")
    try:
        page.wait_for_function(
            "!document.getElementById('bMnt').textContent.includes('loading')",
            timeout=15000
        )
    except Exception as e:
        print(f"wait timeout: {e}")
    page.wait_for_timeout(500)
    mnt  = page.locator("#bMnt").inner_text()
    usdt = page.locator("#bUsdt").inner_text()
    print(f"bMnt={mnt!r}  bUsdt={usdt!r}")
    page.screenshot(path="dashboard_v2.png", full_page=True)
    browser.close()
    print("saved: dashboard_v2.png")
