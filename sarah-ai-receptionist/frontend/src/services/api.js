import axios from "axios";
import { getAccessToken, setAccessToken, useAuthStore } from "../store/useAuthStore";

// The dashboard/admin frontend is served from app./admin.aliyarsolutions.com
// via CloudFront+S3, which has no origin for the backend — a relative path
// here would hit CloudFront itself, not the API. The API runs behind the
// ALB on sarah.aliyarsolutions.com (CORS there already allows both origins).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://sarah.aliyarsolutions.com/api/v1";

// withCredentials so the HttpOnly refresh cookie is included on cross-
// subdomain calls to /auth/refresh. The backend cookie domain is
// .aliyarsolutions.com in prod, scoping the cookie to *.aliyarsolutions.com
// only -- not any other site.
const api = axios.create({ baseURL: API_BASE_URL, withCredentials: true });

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Refresh coalescing: N concurrent 401s from a stale token must trigger ONE
// refresh call, not N. Anything above 1 wastes refresh-token rotations and
// races the server -- one succeeds, the others fail because the refresh
// token was already consumed.
let _refreshInFlight = null;

async function refreshAccessToken() {
  if (_refreshInFlight) return _refreshInFlight;
  _refreshInFlight = (async () => {
    try {
      // Bare axios instance -- using `api` would recurse through this
      // interceptor if /auth/refresh itself returned 401, which it does
      // by design when the cookie is expired.
      const { data } = await axios.post(
        `${API_BASE_URL}/auth/refresh`,
        {},
        { withCredentials: true },
      );
      setAccessToken(data.access_token);
      // Resync identity (role/clinic_id/full_name) to whoever the refresh
      // cookie actually belongs to -- NOT just the token. The cookie is
      // shared across every *.aliyarsolutions.com subdomain, while role/
      // clinic_id/full_name are cached per-origin in localStorage; without
      // this, a browser that logged into two subdomains as two different
      // accounts would keep rendering the older subdomain's stale identity
      // (e.g. still showing the admin console) even after the shared
      // cookie moved to a different, non-admin account -- every API call
      // would then 403 against a UI that still claims to be an admin.
      useAuthStore.getState().setSession(data);
      return data.access_token;
    } finally {
      _refreshInFlight = null;
    }
  })();
  return _refreshInFlight;
}

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    // Refresh-on-401, but only once per request (marked with _retried) --
    // otherwise a genuinely wrong permission (revoked user, disabled
    // account) would loop forever.
    if (
      err.response?.status === 401 &&
      original &&
      !original._retried &&
      !original.url?.endsWith("/auth/refresh") &&
      !original.url?.endsWith("/auth/login")
    ) {
      original._retried = true;
      try {
        const token = await refreshAccessToken();
        original.headers = { ...original.headers, Authorization: `Bearer ${token}` };
        return api(original);
      } catch {
        useAuthStore.getState().logout();
      }
    } else if (err.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(err);
  }
);

export const authApi = {
  login: async (email, password) => {
    const res = await api.post("/auth/login", { email, password });
    setAccessToken(res.data.access_token);
    return res;
  },
  refresh: refreshAccessToken,
  logout: async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      useAuthStore.getState().logout();
    }
  },
  me: () => api.get("/auth/me"),
};

// Every dashboard/appointments call accepts an optional trailing `params`
// object. Clinic users don't need to pass anything -- the backend scopes to
// their own clinic from the JWT. The admin console's per-clinic view passes
// { clinic_id } explicitly, since a platform_admin token carries no clinic
// of its own (see app/core/security.py:get_scoped_clinic_id).
export const dashboardApi = {
  getStats: (params) => api.get("/dashboard/stats", { params }),
  getCalls: (params) => api.get("/dashboard/calls", { params }),
  getCallDetail: (id, params) => api.get(`/dashboard/calls/${id}`, { params }),
  getRecordingUrl: (id, params) => api.get(`/dashboard/calls/${id}/recording-url`, { params }),
  getSettings: (params) => api.get("/dashboard/settings", { params }),
  updateSettings: (payload, params) => api.patch("/dashboard/settings", payload, { params }),
};

export const appointmentsApi = {
  list: (params) => api.get("/appointments", { params }),
  update: (id, payload, params) => api.patch(`/appointments/${id}`, payload, { params }),
};

export const adminApi = {
  onboardClinic: (payload) => api.post("/admin/clinics/onboard", payload),
  listClinics: () => api.get("/admin/clinics"),
  getAnalytics: () => api.get("/admin/analytics"),
};

export default api;
