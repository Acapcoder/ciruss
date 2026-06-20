"""One-off screenshot capture for the CIRRUS report (local demo env)."""
import time
from playwright.sync_api import sync_playwright

BASE = "http://localhost:5175"
OUT = "c:/Users/sanan/OneDrive/Desktop/cirrus/report/assets"
EMAIL = f"demo{int(time.time())}@cirrus.app"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1360, "height": 900}, device_scale_factor=2)

    # 1. Sign in page
    page.goto(f"{BASE}/signin", wait_until="networkidle")
    page.wait_for_timeout(1200)
    page.screenshot(path=f"{OUT}/01_signin.png", full_page=True)

    # 2. Sign up page
    page.goto(f"{BASE}/signup", wait_until="networkidle")
    page.wait_for_timeout(800)
    page.screenshot(path=f"{OUT}/02_signup.png", full_page=True)

    # Fill the sign-up form and submit
    page.fill('input[placeholder="Enter your full name"]', "Demo User")
    page.fill('input[type="email"]', EMAIL)
    page.fill('input[type="password"]', "DemoPass123!")
    page.check('#accept-terms')
    page.click('button:has-text("Create Account")')
    page.wait_for_timeout(3500)  # let signup + redirect + data load happen

    # 3. Dashboard
    page.goto(f"{BASE}/dashboard", wait_until="networkidle")
    page.wait_for_timeout(2500)
    page.screenshot(path=f"{OUT}/03_dashboard.png", full_page=True)

    # 4. Connections
    page.goto(f"{BASE}/connections", wait_until="networkidle")
    page.wait_for_timeout(2000)
    page.screenshot(path=f"{OUT}/04_connections.png", full_page=True)

    # 5. File Manager
    page.goto(f"{BASE}/files", wait_until="networkidle")
    page.wait_for_timeout(2000)
    page.screenshot(path=f"{OUT}/05_files.png", full_page=True)

    browser.close()
    print("Screenshots saved for", EMAIL)
