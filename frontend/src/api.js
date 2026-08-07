const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:9000";

const ACCESS_KEY = "blossom-platform:access";
const REFRESH_KEY = "blossom-platform:refresh";

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  set({ access, refresh }) {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

async function request(path, { method = "GET", body, auth = false, credentials } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) headers.Authorization = `Bearer ${tokens.access}`;

  const response = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    credentials,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const message =
      data?.detail ||
      data?.error ||
      (data && typeof data === "object" ? Object.values(data).flat().join(" ") : null) ||
      `Request failed (${response.status})`;
    throw new Error(message);
  }
  return data;
}

export const api = {
  // credentials:"include" is what makes the hand-off work at all.
  //
  // This app talks to its own API with a bearer token, which is fine for XHR. But
  // an OIDC authorize request is a top-level browser navigation, and a navigation
  // cannot carry a header — it carries cookies. So signing in here also starts a
  // server session, and "include" is what lets the browser keep the Set-Cookie
  // that comes back from a cross-origin response.
  signup: (payload) =>
    request("/api/auth/signup/", { method: "POST", body: payload, credentials: "include" }),
  login: (payload) =>
    request("/api/auth/login/", { method: "POST", body: payload, credentials: "include" }),
  me: () => request("/api/auth/me/", { auth: true }),

  /** The live OIDC registration, for the Developer page. */
  integration: () => request("/api/auth/integration/", { auth: true }),

  /** Read from the provider exactly as a relying party would read it, so the
   *  page shows the real document rather than a copy of it. */
  discovery: () => request("/.well-known/openid-configuration"),

  /** The member's own banking data. Scoped server-side to the bearer's owner. */
  banking: {
    summary: () => request("/api/banking/summary/", { auth: true }),
    accounts: () => request("/api/banking/accounts/", { auth: true }),
    transactions: (accountId) =>
      request(`/api/banking/accounts/${accountId}/transactions/`, { auth: true }),
  },

  /** The provider console. Staff only — every call here 403s otherwise. */
  provider: {
    overview: () => request("/api/provider/overview/", { auth: true }),
    activity: () => request("/api/provider/activity/", { auth: true }),
    clients: () => request("/api/provider/clients/", { auth: true }),
    createClient: (payload) =>
      request("/api/provider/clients/", { method: "POST", body: payload, auth: true }),
    updateClient: (clientId, payload) =>
      request(`/api/provider/clients/${encodeURIComponent(clientId)}/`, {
        method: "PATCH",
        body: payload,
        auth: true,
      }),
    deleteClient: (clientId) =>
      request(`/api/provider/clients/${encodeURIComponent(clientId)}/`, {
        method: "DELETE",
        auth: true,
      }),
    rotateSecret: (clientId) =>
      request(`/api/provider/clients/${encodeURIComponent(clientId)}/rotate-secret/`, {
        method: "POST",
        auth: true,
      }),
  },

  // Only used when Surmount is configured for the token-exchange fallback. On the
  // OIDC path nothing is called at click time — Investments is a plain link.
  ssoInitiate: () => request("/sso/initiate/", { method: "POST", body: {}, auth: true }),
};

/** Ends the browser session the OIDC endpoints rely on.
 *
 * redirect:"manual" because the endpoint answers with a 302 meant for a real
 * navigation. The session is already cleared by the time it replies, so there is
 * nothing here that needs to follow it. */
export const endSession = () =>
  fetch(`${BASE}/oauth/logout`, { credentials: "include", redirect: "manual" }).catch(
    () => {}
  );
