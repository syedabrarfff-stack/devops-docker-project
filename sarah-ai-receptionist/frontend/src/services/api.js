import axios from "axios";
import { useAuthStore } from "../store/useAuthStore";

// The dashboard/admin frontend is served from app./admin.aliyarsolutions.com
// via CloudFront+S3, which has no origin for the backend — a relative path
// here would hit CloudFront itself, not the API. The API runs behind the
// ALB on sarah.aliyarsolutions.com (CORS there already allows both origins).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://sarah.aliyarsolutions.com/api/v1";
const api = axios.create({ baseURL: API_BASE_URL });

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(err);
  }
);

export const authApi = {
  login: (email, password) => api.post("/auth/login", { email, password }),
  me: () => api.get("/auth/me"),
};

export const dashboardApi = {
  getStats: () => api.get("/dashboard/stats"),
  getCalls: (params) => api.get("/dashboard/calls", { params }),
  getCallDetail: (id) => api.get(`/dashboard/calls/${id}`),
  getRecordingUrl: (id) => api.get(`/dashboard/calls/${id}/recording-url`),
  getSettings: () => api.get("/dashboard/settings"),
  updateSettings: (payload) => api.patch("/dashboard/settings", payload),
};

export const appointmentsApi = {
  list: (params) => api.get("/appointments", { params }),
  update: (id, payload) => api.patch(`/appointments/${id}`, payload),
};

export const adminApi = {
  onboardClinic: (payload) => api.post("/admin/clinics/onboard", payload),
  listClinics: () => api.get("/admin/clinics"),
  getAnalytics: () => api.get("/admin/analytics"),
};

export default api;
