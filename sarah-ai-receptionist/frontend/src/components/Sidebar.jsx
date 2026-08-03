import { NavLink } from "react-router-dom";
import { LayoutDashboard, PhoneCall, CalendarClock, Settings, LogOut, ShieldCheck } from "lucide-react";
import { authApi } from "../services/api";
import { useAuthStore } from "../store/useAuthStore";

const CLINIC_NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/calls", label: "Call Log", icon: PhoneCall },
  { to: "/appointments", label: "Appointments", icon: CalendarClock },
  { to: "/settings", label: "Settings", icon: Settings },
];

const ADMIN_NAV = [
  { to: "/admin", label: "Admin Console", icon: ShieldCheck },
];

export default function Sidebar() {
  // Use authApi.logout so the server-side refresh token is actually revoked,
  // not just the local state cleared -- useAuthStore.logout only wipes the
  // in-memory access token, leaving the refresh cookie usable for anyone
  // with the machine.
  const { fullName, role } = useAuthStore();
  const logout = authApi.logout;
  const NAV = role === "platform_admin" ? ADMIN_NAV : CLINIC_NAV;

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col h-screen sticky top-0">
      <div className="p-6 border-b border-slate-100">
        <div className="text-xl font-semibold text-brand-700">Sarah</div>
        <div className="text-xs text-slate-400 mt-0.5">by Aliyar Solutions</div>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-50"
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-slate-100">
        <div className="text-sm font-medium text-slate-700 mb-2 truncate">{fullName}</div>
        <button
          onClick={logout}
          className="flex items-center gap-2 text-sm text-slate-500 hover:text-red-600 transition-colors"
        >
          <LogOut size={16} /> Sign out
        </button>
      </div>
    </aside>
  );
}
