"""Render the HTML report to a PDF using headless Chromium (no header/footer)."""
import os
from playwright.sync_api import sync_playwright

HTML = os.path.join(os.path.dirname(__file__), "CIRRUS_Report.html")
PDF = os.path.join(os.path.dirname(__file__), "CIRRUS_Report.pdf")
url = "file:///" + HTML.replace("\\", "/")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    page.goto(url, wait_until="networkidle")
    page.pdf(
        path=PDF,
        format="A4",
        print_background=True,
        display_header_footer=False,  # no footer line, no page numbers
        margin={"top": "2cm", "bottom": "2cm", "left": "2cm", "right": "2cm"},
    )
    b.close()
    print("PDF written to", PDF, "size", round(os.path.getsize(PDF) / 1024), "KB")
