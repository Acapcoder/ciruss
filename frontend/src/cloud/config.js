// Baked-in OAuth client IDs — set ONCE by you (the developer). End users never
// see these or any setup screen; they just click "Connect with Google".
//
// Leave a value empty to hide that provider's connect button until configured.
// (OneDrive = Azure app client ID, Dropbox = app key — add when you create them.)
export const DEFAULT_CLIENT_IDS = {
  gdrive: "663891447220-q4b4cdi33uuaj74cpm9lrt437qqd8uph.apps.googleusercontent.com",
  onedrive: "",
  dropbox: "",
};

// When true, the "Setup IDs" panel is hidden for providers that already have a
// baked-in client ID (so the UI stays simple for end users).
export const HIDE_SETUP_WHEN_CONFIGURED = true;
