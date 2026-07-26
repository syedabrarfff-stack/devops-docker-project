import { Outlet, Navigate } from "react-router-dom";
import Sidebar from "./Sidebar";
import { useAuthStore } from "../store/useAuthStore";

export default function Layout() {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-8 max-w-6xl mx-auto w-full">
        <Outlet />
      </main>
    </div>
  );
}
