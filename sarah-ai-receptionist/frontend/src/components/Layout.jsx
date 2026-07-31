import { Outlet, Navigate } from "react-router-dom";
import Sidebar from "./Sidebar";
import { useAuthStore } from "../store/useAuthStore";

export default function Layout() {
  const { token, role } = useAuthStore();
  if (!token) return <Navigate to="/login" replace />;
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
