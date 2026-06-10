from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto("http://localhost:8000/")
    page.wait_for_load_state("networkidle")
    page.screenshot(path="dashboard_pw.png", full_page=True)
    browser.close()
    print("saved: dashboard_pw.png")
