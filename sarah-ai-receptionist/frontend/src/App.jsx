import { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import { authApi } from "./services/api";
import { useAuthStore } from "./store/useAuthStore";
import Dashboard from "./pages/Dashboard";
import CallLog from "./pages/CallLog";
import Appointments from "./pages/Appointments";
import Settings from "./pages/Settings";
import AdminLayout from "./pages/admin/AdminLayout";
import Clinics from "./pages/admin/Clinics";
import OnboardClinic from "./pages/admin/OnboardClinic";
import Analytics from "./pages/admin/Analytics";

export default function App() {
  // Silent refresh on load: reloads and new tabs no longer carry the access
  // token (only the identity fields persist), so try to mint a fresh one
  // from the refresh cookie the browser will send automatically. Failure
  // just means "not signed in", handled by Layout redirecting to /login.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await authApi.refresh();
      } catch {
        /* not signed in / cookie expired -- Layout will redirect */
      }
      if (!cancelled) useAuthStore.getState().markBootstrapped();
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/calls" element={<CallLog />} />
        <Route path="/appointments" element={<Appointments />} />
        <Route path="/settings" element={<Settings />} />
      </Route>

      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<Clinics />} />
        <Route path="onboard" element={<OnboardClinic />} />
        <Route path="analytics" element={<Analytics />} />
      </Route>
    </Routes>
  );
}
