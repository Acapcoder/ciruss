"""
OAuth 2.0 authorization-code flow so users connect their clouds with one click
and STAY connected (we store a refresh token, encrypted, and the existing
storage clients refresh access tokens automatically).

Developer setup (one time, free):
- Create an OAuth app per provider and put its client_id + client_secret in
  backend/oauth_secrets.json (copy oauth_secrets.example.json). Secrets live
  ONLY on the backend — never shipped to the browser.
- Register this redirect URI on each OAuth app:
    {BACKEND_URL}/api/oauth/{provider}/callback
  e.g. http://localhost:8000/api/oauth/gdrive/callback

End users never see any of this — they just click "Connect with Google".
"""

import os
import json
import base64
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
import models
from crypto_utils import encrypt_data
from storage_clients import get_storage_client

router = APIRouter(prefix="/api/oauth", tags=["oauth"])

BACKEND_URL = os.environ.get("CIRRUS_BACKEND_URL", "http://localhost:8000")

# Per-provider OAuth endpoints. Only providers with a matching storage client
# and configured secrets can actually be connected.
OAUTH = {
    "gdrive": {
        "auth": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "scope": "https://www.googleapis.com/auth/drive.file",
        "auth_extra": {"access_type": "offline", "prompt": "consent select_account", "include_granted_scopes": "true"},
    },
    "onedrive": {
        "auth": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scope": "Files.ReadWrite offline_access User.Read",
        "auth_extra": {"response_mode": "query"},
    },
    "dropbox": {
        "auth": "https://www.dropbox.com/oauth2/authorize",
        "token": "https://api.dropboxapi.com/oauth2/token",
        "scope": "files.content.write account_info.read",
        "auth_extra": {"token_access_type": "offline"},
    },
}

# Providers we can currently upload to server-side (have a storage client).
SUPPORTED = {"gdrive", "dropbox"}


# ------------------------------- secrets --------------------------------
def _load_secrets():
    path = os.path.join(os.path.dirname(__file__), "oauth_secrets.json")
    data = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    # Env overrides (e.g. CIRRUS_GDRIVE_CLIENT_SECRET).
    for p in OAUTH:
        cid = os.environ.get(f"CIRRUS_{p.upper()}_CLIENT_ID")
        sec = os.environ.get(f"CIRRUS_{p.upper()}_CLIENT_SECRET")
        if cid or sec:
            data.setdefault(p, {})
            if cid:
                data[p]["client_id"] = cid
            if sec:
                data[p]["client_secret"] = sec
    return data


def _provider_creds(provider):
    secrets = _load_secrets().get(provider, {})
    cid, sec = secrets.get("client_id"), secrets.get("client_secret")
    if not cid or not sec:
        raise HTTPException(status_code=400, detail=f"{provider} is not configured on the server.")
    return cid, sec


def _redirect_uri(provider):
    return f"{BACKEND_URL}/api/oauth/{provider}/callback"


def _post_form(url, fields):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def _get_json(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


# --------------------------- public endpoints ---------------------------
@router.get("/providers")
def providers():
    """Which providers the UI can offer (configured + supported)."""
    secrets = _load_secrets()
    out = {}
    for p in OAUTH:
        configured = bool(secrets.get(p, {}).get("client_id") and secrets.get(p, {}).get("client_secret"))
        out[p] = {"configured": configured, "supported": p in SUPPORTED}
    return out


@router.get("/{provider}/start")
def start(provider: str, token: str, origin: str = "", db: Session = Depends(get_db)):
    if provider not in OAUTH or provider not in SUPPORTED:
        raise HTTPException(status_code=404, detail="Unknown or unsupported provider")
        
    from crypto_utils import decode_access_token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload.get("sub")

    client_id, _ = _provider_creds(provider)
    cfg = OAUTH[provider]
    state = base64.urlsafe_b64encode(json.dumps({"provider": provider, "origin": origin, "user_id": user_id}).encode()).decode()
    params = {
        "client_id": client_id,
        "redirect_uri": _redirect_uri(provider),
        "response_type": "code",
        "scope": cfg["scope"],
        "state": state,
        **cfg.get("auth_extra", {}),
    }
    return RedirectResponse(f"{cfg['auth']}?{urllib.parse.urlencode(params)}")


@router.get("/{provider}/callback", response_class=HTMLResponse)
def callback(provider: str, request: Request, db: Session = Depends(get_db)):
    code = request.query_params.get("code")
    state_raw = request.query_params.get("state", "")
    if not code:
        return _close_page("", {"ok": False, "error": request.query_params.get("error", "no_code")})
    try:
        state = json.loads(base64.urlsafe_b64decode(state_raw.encode()).decode())
    except Exception:
        state = {}
    origin = state.get("origin", "")
    user_id = state.get("user_id", "")

    try:
        client_id, client_secret = _provider_creds(provider)
        cfg = OAUTH[provider]
        token_fields = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": _redirect_uri(provider),
            "grant_type": "authorization_code",
        }
        if provider == "onedrive":
            token_fields["scope"] = cfg["scope"]  # Microsoft wants scope on exchange
        tok = _post_form(cfg["token"], token_fields)
        refresh_token = tok.get("refresh_token")
        access_token = tok.get("access_token")
        if not refresh_token:
            return _close_page(origin, {"ok": False, "error": "no_refresh_token (re-consent needed)"})

        # Identify the account + read live quota, per provider.
        if provider == "gdrive":
            email, used, limit = _identify_gdrive(access_token)
        elif provider == "onedrive":
            email, used, limit = _identify_onedrive(access_token)
        else:
            email, used, limit = _identify_dropbox(access_token)

        creds = {"client_id": client_id, "client_secret": client_secret, "refresh_token": refresh_token}
        account = models.StorageAccount(
            user_id=user_id,
            provider=provider,
            display_name=email or f"{provider} account",
            credentials_json=encrypt_data(json.dumps(creds)),
            quota_limit=limit or 15 * 1024 * 1024 * 1024,
            used_space=used or 0,
            is_active=True,
            is_mock=False,
        )
        db.add(account)
        db.commit()
        db.refresh(account)

        # Audit log connected account
        try:
            new_log = models.AuditLog(
                user_id=user_id,
                action="CONNECT_ACCOUNT",
                details=f"Connected {provider} account via OAuth: {account.display_name}"
            )
            db.add(new_log)
            db.commit()
        except Exception:
            db.rollback()

        return _close_page(origin, {"ok": True, "provider": provider, "email": email, "account_id": account.id})
    except HTTPException as e:
        return _close_page(origin, {"ok": False, "error": e.detail})
    except Exception as e:
        return _close_page(origin, {"ok": False, "error": str(e)})


def _identify_gdrive(access_token):
    try:
        d = _get_json("https://www.googleapis.com/drive/v3/about?fields=user,storageQuota", access_token)
        q = d.get("storageQuota", {})
        email = (d.get("user") or {}).get("emailAddress")
        used = int(q.get("usage", 0))
        limit = int(q["limit"]) if q.get("limit") else None
        return email, used, limit
    except Exception:
        return None, 0, None


def _identify_onedrive(access_token):
    try:
        d = _get_json("https://graph.microsoft.com/v1.0/me/drive", access_token)
        q = d.get("quota", {})
        owner = (d.get("owner") or {}).get("user") or {}
        email = owner.get("displayName")
        used = int(q.get("used", 0))
        limit = int(q["total"]) if q.get("total") else None
        return email or "OneDrive", used, limit
    except Exception:
        return "OneDrive", 0, None


def _identify_dropbox(access_token):
    try:
        # Dropbox RPC endpoints are POST with a Bearer header and (here) null body.
        req = urllib.request.Request(
            "https://api.dropboxapi.com/2/users/get_space_usage",
            data=b"", headers={"Authorization": f"Bearer {access_token}"},
        )
        with urllib.request.urlopen(req) as resp:
            usage = json.loads(resp.read().decode())
        used = int(usage.get("used", 0))
        limit = usage.get("allocation", {}).get("allocated")
        return "Dropbox", used, int(limit) if limit else None
    except Exception:
        return "Dropbox", 0, None


def _close_page(origin, payload):
    target = json.dumps(origin) if origin else "'*'"
    body = json.dumps({"cirrus_oauth": True, **payload})
    html = f"""<!doctype html><html><body style="background:#0b0f1a;color:#94a3b8;font-family:system-ui">
<p style="padding:24px">You can close this window.</p>
<script>
  try {{ if (window.opener) window.opener.postMessage({body}, {target}); }} catch (e) {{}}
  setTimeout(function(){{ window.close(); }}, 250);
</script></body></html>"""
    return HTMLResponse(html)
