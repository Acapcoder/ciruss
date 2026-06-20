"""
Live browser storage clients for the free, web-dashboard providers:
Google Drive, OneDrive, and Dropbox.

Authentication model — "use the browser you're already signed into"
--------------------------------------------------------------------
CIRRUS does NOT ask for or store any passwords. On connect it seeds a private
automation profile from your existing local Chrome profile (cookies + key) so
the account is already signed in. If that session can't be reused (e.g. Chrome's
app-bound cookie encryption blocks it, or you've never signed in), it falls back
to opening a visible window once so you can sign in by hand; that session is
then persisted for all future background uploads.

Security notes
- No passwords are persisted anywhere — only browser session cookies, stored
  locally under backend/browser_profiles/<account_id> (treat as sensitive; keep
  off version control / shared disks).
- This is local-only by nature: it reads the local machine's Chrome session, so
  it cannot run on a headless server (AWS) where no signed-in browser exists.
"""

import os
import re
import time
import shutil
from urllib.parse import quote

from storage_clients import StorageProviderClient

PROFILE_ROOT = os.path.join(os.path.dirname(__file__), "browser_profiles")

PROVIDERS = {
    "gdrive_browser": {
        "label": "Google Drive",
        "home": "https://drive.google.com/drive/my-drive",
        "storage": "https://drive.google.com/settings/storage",
        "logged_out": "accounts.google.com",
        "search": "https://drive.google.com/drive/search?q={q}",
    },
    "onedrive_browser": {
        "label": "OneDrive",
        "home": "https://onedrive.live.com/",
        "storage": "https://onedrive.live.com/",
        "logged_out": "login.live.com",
        "search": "https://onedrive.live.com/?q={q}",
    },
    "dropbox_browser": {
        "label": "Dropbox",
        "home": "https://www.dropbox.com/home",
        "storage": "https://www.dropbox.com/account/plan",
        "logged_out": "dropbox.com/login",
        "search": "https://www.dropbox.com/search/personal?query={q}",
    },
}

BROWSER_PROVIDERS = tuple(PROVIDERS.keys())


def _parse_bytes(text: str) -> int:
    m = re.search(r"([\d.,]+)\s*(bytes|KB|MB|GB|TB)", text, re.IGNORECASE)
    if not m:
        return 0
    value = float(m.group(1).replace(",", ""))
    unit = m.group(2).upper()
    mult = {"BYTES": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    return int(value * mult.get(unit, 1))


def _system_chrome_user_data() -> str | None:
    """Locate the local Chrome 'User Data' directory (Windows / mac / Linux)."""
    candidates = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(os.path.join(local, "Google", "Chrome", "User Data"))
    home = os.path.expanduser("~")
    candidates += [
        os.path.join(home, "Library", "Application Support", "Google", "Chrome"),
        os.path.join(home, ".config", "google-chrome"),
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return c
    return None


class BrowserStorageClient(StorageProviderClient):
    def __init__(self, provider: str, account_id: str):
        if provider not in PROVIDERS:
            raise ValueError(f"Unsupported browser provider: {provider}")
        self.provider = provider
        self.cfg = PROVIDERS[provider]
        self.profile_dir = os.path.join(PROFILE_ROOT, account_id)
        os.makedirs(self.profile_dir, exist_ok=True)

    # ------------------------ system-session seeding ------------------------
    def _seed_from_system_chrome(self) -> bool:
        """Copy the local Chrome session (cookies + decryption key) into our
        automation profile so we inherit existing logins. Best-effort."""
        src = _system_chrome_user_data()
        if not src:
            return False
        try:
            # The 'Local State' file holds the key used to decrypt cookies.
            ls = os.path.join(src, "Local State")
            if os.path.exists(ls):
                shutil.copy2(ls, os.path.join(self.profile_dir, "Local State"))
            # Copy the Default profile's session-bearing files.
            for rel in (
                ("Default", "Network", "Cookies"),
                ("Default", "Cookies"),
                ("Default", "Login Data"),
                ("Default", "Web Data"),
                ("Default", "Preferences"),
            ):
                s = os.path.join(src, *rel)
                if os.path.exists(s):
                    d = os.path.join(self.profile_dir, *rel)
                    os.makedirs(os.path.dirname(d), exist_ok=True)
                    shutil.copy2(s, d)
            return True
        except Exception as e:
            print(f"Could not seed from system Chrome profile: {e}")
            return False

    # ----------------------------- browser plumbing -----------------------------
    def _launch(self, headless: bool):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        kwargs = dict(
            headless=headless,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        try:
            # Prefer the user's real Chrome so the inherited session matches.
            self._ctx = self._pw.chromium.launch_persistent_context(
                self.profile_dir, channel="chrome", **kwargs
            )
        except Exception:
            # Fall back to Playwright's bundled Chromium if Chrome isn't present.
            self._ctx = self._pw.chromium.launch_persistent_context(
                self.profile_dir, **kwargs
            )
        self.page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
        return self.page

    def _close(self):
        try:
            self._ctx.close()
        finally:
            self._pw.stop()

    def _is_logged_in(self, page) -> bool:
        return self.cfg["logged_out"] not in page.url

    def _require_session(self, page):
        page.goto(self.cfg["home"], wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        if not self._is_logged_in(page):
            raise RuntimeError(
                f"{self.cfg['label']} session is not signed in. Re-connect the "
                f"account in CIRRUS to refresh the browser session."
            )

    # ------------------------------- connect --------------------------------
    def connect(self, timeout: int = 300) -> bool:
        """Establish a usable signed-in session.

        1) Seed from the local Chrome profile and try to reuse it headlessly.
        2) If still not signed in, open a visible window for a one-time login.
        """
        self._seed_from_system_chrome()

        # Attempt 1: silently reuse the inherited Chrome session.
        page = self._launch(headless=True)
        try:
            page.goto(self.cfg["home"], wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            if self._is_logged_in(page):
                return True
        finally:
            self._close()

        # Attempt 2: visible, user signs in once; session then persists.
        page = self._launch(headless=False)
        try:
            page.goto(self.cfg["home"], wait_until="domcontentloaded")
            deadline = time.time() + timeout
            while time.time() < deadline:
                if self._is_logged_in(page):
                    page.wait_for_timeout(1500)
                    return True
                page.wait_for_timeout(2000)
            raise TimeoutError(f"Timed out waiting for {self.cfg['label']} sign-in.")
        finally:
            self._close()

    # ------------------------------- interface --------------------------------
    def get_used_space(self) -> int:
        page = self._launch(headless=True)
        try:
            self._require_session(page)
            page.goto(self.cfg["storage"], wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            body = page.inner_text("body")
            m = re.search(r"([\d.,]+\s*(?:bytes|KB|MB|GB|TB))\s*of", body, re.IGNORECASE)
            return _parse_bytes(m.group(1)) if m else 0
        finally:
            self._close()

    def upload_file(self, file_path: str, filename: str) -> str:
        page = self._launch(headless=True)
        try:
            self._require_session(page)
            if self.provider == "gdrive_browser":
                self._gdrive_upload(page, file_path)
            elif self.provider == "onedrive_browser":
                self._onedrive_upload(page, file_path)
            else:
                self._dropbox_upload(page, file_path)
            return filename
        finally:
            self._close()

    def _gdrive_upload(self, page, file_path):
        page.goto(self.cfg["home"], wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        with page.expect_file_chooser() as fc:
            page.click('button:has-text("New"), [guidedhelpid="new_menu_button"]')
            page.wait_for_timeout(800)
            page.click("text=File upload")
        fc.value.set_files(file_path)
        try:
            page.wait_for_selector("text=/upload(s)? complete/i", timeout=120000)
        except Exception:
            page.wait_for_timeout(8000)

    def _onedrive_upload(self, page, file_path):
        page.goto(self.cfg["home"], wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        with page.expect_file_chooser() as fc:
            page.click('button:has-text("Upload")')
            page.wait_for_timeout(800)
            page.click('text=/^Files$/')
        fc.value.set_files(file_path)
        page.wait_for_timeout(10000)

    def _dropbox_upload(self, page, file_path):
        page.goto(self.cfg["home"], wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        with page.expect_file_chooser() as fc:
            page.click('button:has-text("Upload"), [aria-label="Upload"]')
            page.wait_for_timeout(800)
            page.click("text=/Upload files|Files/")
        fc.value.set_files(file_path)
        page.wait_for_timeout(10000)

    def download_file(self, stored_name: str, download_path: str):
        page = self._launch(headless=True)
        try:
            self._require_session(page)
            page.goto(self.cfg["search"].format(q=quote(stored_name)),
                      wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            row = page.locator(f'text="{stored_name}"').first
            row.click(button="right")
            with page.expect_download(timeout=120000) as dl:
                page.click("text=Download")
            dl.value.save_as(download_path)
        finally:
            self._close()

    def delete_file(self, stored_name: str):
        page = self._launch(headless=True)
        try:
            self._require_session(page)
            page.goto(self.cfg["search"].format(q=quote(stored_name)),
                      wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            row = page.locator(f'text="{stored_name}"').first
            row.click(button="right")
            page.click("text=/Remove|Delete|Move to trash/")
        except Exception:
            pass
        finally:
            self._close()

    def get_web_link(self, stored_name: str) -> str:
        return self.cfg["search"].format(q=quote(stored_name))


def get_browser_client(provider: str, account_id: str) -> BrowserStorageClient:
    return BrowserStorageClient(provider, account_id)
