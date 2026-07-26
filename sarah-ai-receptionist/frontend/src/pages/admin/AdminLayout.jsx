import { Outlet, Navigate, NavLink } from "react-router-dom";
import { LogOut } from "lucide-react";
import { useAuthStore } from "../../store/useAuthStore";

const NAV = [
  { to: "/admin", label: "Clinics" },
  { to: "/admin/onboard", label: "Onboard New Clinic" },
  { to: "/admin/analytics", label: "Analytics" },
];

export default function AdminLayout() {
  const { token, role, logout } = useAuthStore();
  if (!token) return <Navigate to="/login" replace />;
  if (role !== "platform_admin") return <Navigate to="/" replace />;

  return (
    <div className="flex">
      <aside className="w-64 bg-slate-900 text-white flex flex-col h-screen sticky top-0">
        <div className="p-6 border-b border-slate-800">
          <div className="text-xl font-semibold">Sarah Admin</div>
          <div className="text-xs text-slate-400 mt-0.5">Aliyar Solutions — Captain's Console</div>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {NAV.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end
              className={({ isActive }) =>
                `block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? "bg-brand-600 text-white" : "text-slate-300 hover:bg-slate-800"
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-slate-800">
          <button onClick={logout} className="flex items-center gap-2 text-sm text-slate-400 hover:text-white">
            <LogOut size={16} /> Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 p-8 max-w-5xl mx-auto w-full">
        <Outlet />
      </main>
    </div>
  );
}
