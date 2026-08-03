import { Outlet, Navigate } from "react-router-dom";
import Sidebar from "./Sidebar";
import { getAccessToken, useAuthStore } from "../store/useAuthStore";

export default function Layout() {
  // Checked from the module-level access token, not persisted state --
  // localStorage no longer holds it. `bootstrapped` distinguishes "session
  // is over, redirect to login" from "haven't tried to silent-refresh yet",
  // avoiding a login-screen flash on hard reload.
  const { role, bootstrapped } = useAuthStore();
  if (!bootstrapped) return null;
  if (!getAccessToken()) return <Navigate to="/login" replace />;
  if (role === "platform_admin") return <Navigate to="/admin" replace />;

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-8 max-w-6xl mx-auto w-full">
        <Outlet />
      </main>
    </div>
  );
}
