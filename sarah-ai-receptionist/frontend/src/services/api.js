import axios from "axios";
import { useAuthStore } from "../store/useAuthStore";

const api = axios.create({ baseURL: "/api/v1" });

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
