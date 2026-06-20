// Client-side provider definitions. Each provider authenticates in the browser
// via an OAuth popup (implicit token flow — no client secret) and talks to the
// official REST API directly from the browser (these APIs send CORS headers, so
// a browser with a Bearer token can call them).
//
// Configure a Client ID per provider on the Cloud Connections page. The redirect
// URI to register in each OAuth app is shown there (your site origin +
// /oauth-callback.html).

export const PROVIDERS = {
  gdrive: {
    label: "Google Drive",
    color: "#34a853",
    buildAuthUrl(clientId, redirectUri) {
      const p = new URLSearchParams({
        client_id: clientId,
        response_type: "token",
        redirect_uri: redirectUri,
        scope: "https://www.googleapis.com/auth/drive.file",
        include_granted_scopes: "true",
        // Always show the account chooser so a user can add multiple Gmails.
        prompt: "select_account consent",
      });
      return `https://accounts.google.com/o/oauth2/v2/auth?${p}`;
    },
    async quota(token) {
      const r = await fetch(
        "https://www.googleapis.com/drive/v3/about?fields=storageQuota,user",
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!r.ok) throw new Error(`Drive quota ${r.status}`);
      const d = await r.json();
      const q = d.storageQuota || {};
      return {
        used: Number(q.usage || 0),
        total: q.limit ? Number(q.limit) : null,
        account: d.user?.emailAddress || null,
      };
    },
    async upload(token, blob, name) {
      const metadata = { name };
      const form = new FormData();
      form.append(
        "metadata",
        new Blob([JSON.stringify(metadata)], { type: "application/json" })
      );
      form.append("file", blob);
      const r = await fetch(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,webViewLink",
        { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form }
      );
      if (!r.ok) throw new Error(`Drive upload ${r.status}: ${await r.text()}`);
      const d = await r.json();
      return { id: d.id, webLink: d.webViewLink };
    },
  },

  onedrive: {
    label: "OneDrive",
    color: "#0364b8",
    buildAuthUrl(clientId, redirectUri) {
      const p = new URLSearchParams({
        client_id: clientId,
        response_type: "token",
        redirect_uri: redirectUri,
        response_mode: "fragment",
        scope: "Files.ReadWrite User.Read",
      });
      return `https://login.microsoftonline.com/common/oauth2/v2.0/authorize?${p}`;
    },
    async quota(token) {
      const r = await fetch("https://graph.microsoft.com/v1.0/me/drive", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`OneDrive quota ${r.status}`);
      const d = await r.json();
      const q = d.quota || {};
      return {
        used: Number(q.used || 0),
        total: q.total ? Number(q.total) : null,
        account: d.owner?.user?.displayName || null,
      };
    },
    async upload(token, blob, name) {
      const path = `CIRRUS/${name}`;
      const r = await fetch(
        `https://graph.microsoft.com/v1.0/me/drive/root:/${encodeURIComponent(path)}:/content`,
        { method: "PUT", headers: { Authorization: `Bearer ${token}` }, body: blob }
      );
      if (!r.ok) throw new Error(`OneDrive upload ${r.status}: ${await r.text()}`);
      const d = await r.json();
      return { id: d.id, webLink: d.webUrl };
    },
  },

  dropbox: {
    label: "Dropbox",
    color: "#0061fe",
    buildAuthUrl(clientId, redirectUri) {
      const p = new URLSearchParams({
        client_id: clientId,
        response_type: "token",
        redirect_uri: redirectUri,
        token_access_type: "online",
      });
      return `https://www.dropbox.com/oauth2/authorize?${p}`;
    },
    async quota(token) {
      const r = await fetch("https://api.dropboxapi.com/2/users/get_space_usage", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`Dropbox quota ${r.status}`);
      const d = await r.json();
      const total = d.allocation?.allocated ?? null;
      return { used: Number(d.used || 0), total: total ? Number(total) : null, account: null };
    },
    async upload(token, blob, name) {
      const arg = { path: `/${name}`, mode: "add", autorename: true, mute: true };
      const r = await fetch("https://content.dropboxapi.com/2/files/upload", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/octet-stream",
          "Dropbox-API-Arg": JSON.stringify(arg),
        },
        body: blob,
      });
      if (!r.ok) throw new Error(`Dropbox upload ${r.status}: ${await r.text()}`);
      const d = await r.json();
      return { id: d.id, webLink: `https://www.dropbox.com/home?preview=${encodeURIComponent(d.name)}` };
    },
  },
};

export const PROVIDER_KEYS = Object.keys(PROVIDERS);
