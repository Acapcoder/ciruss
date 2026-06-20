// Local persistence for CIRRUS (client-side only — no backend).
// Multi-account model: a user can connect SEVERAL accounts (e.g. many Gmails)
// and pool them all. Each account = one connected cloud login.
import { DEFAULT_CLIENT_IDS } from './config.js';

const KEY = "cirrus_state_v2";

const empty = { clientIds: {}, accounts: [], files: [] };

export function loadState() {
  let parsed = {};
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) parsed = JSON.parse(raw);
  } catch { /* ignore */ }
  const state = { ...empty, ...parsed };
  // Baked-in client IDs take effect unless the user has overridden them.
  state.clientIds = { ...DEFAULT_CLIENT_IDS, ...(state.clientIds || {}) };
  return state;
}

export function saveState(state) {
  localStorage.setItem(KEY, JSON.stringify(state));
}

export function tokenValid(t) {
  return !!(t && t.access_token && (!t.expires_at || t.expires_at > Date.now() + 5000));
}
