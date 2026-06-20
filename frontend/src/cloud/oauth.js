import { PROVIDERS } from "./providers.js";

// The redirect URI to register in each provider's OAuth app.
export function getRedirectUri() {
  return `${window.location.origin}/oauth-callback.html`;
}

// Open the provider's consent screen in a popup and resolve with the token.
// Uses the OAuth implicit flow: the token comes back in the URL fragment, which
// oauth-callback.html forwards to us via postMessage.
export function authorize(providerKey, clientId) {
  const redirectUri = getRedirectUri();
  const authUrl = PROVIDERS[providerKey].buildAuthUrl(clientId, redirectUri);

  return new Promise((resolve, reject) => {
    const popup = window.open(authUrl, "cirrus_oauth", "width=520,height=660");
    if (!popup) {
      reject(new Error("Popup blocked — allow popups for this site and retry."));
      return;
    }

    const timer = setInterval(() => {
      if (popup.closed) {
        clearInterval(timer);
        window.removeEventListener("message", onMessage);
        reject(new Error("Sign-in window closed before completing."));
      }
    }, 500);

    function onMessage(e) {
      if (e.origin !== window.location.origin) return;
      if (!e.data || !e.data.cirrus_oauth) return;
      clearInterval(timer);
      window.removeEventListener("message", onMessage);
      try { popup.close(); } catch { /* ignore */ }

      const { access_token, expires_in, error } = e.data;
      if (error) reject(new Error(error));
      else if (!access_token) reject(new Error("No access token returned. Check the OAuth app / redirect URI."));
      else resolve({ access_token, expires_at: Date.now() + (Number(expires_in) || 3600) * 1000 });
    }

    window.addEventListener("message", onMessage);
  });
}
