import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import CallLog from "./pages/CallLog";
import Appointments from "./pages/Appointments";
import Settings from "./pages/Settings";
import AdminLayout from "./pages/admin/AdminLayout";
import Clinics from "./pages/admin/Clinics";
import OnboardClinic from "./pages/admin/OnboardClinic";
import Analytics from "./pages/admin/Analytics";

export default function App() {
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
