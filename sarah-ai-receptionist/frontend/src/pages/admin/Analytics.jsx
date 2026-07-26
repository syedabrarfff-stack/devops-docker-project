import { useEffect, useState } from "react";
import { Building2, PhoneCall, CalendarCheck } from "lucide-react";
import { adminApi } from "../../services/api";
import StatCard from "../../components/StatCard";

export default function Analytics() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    adminApi.getAnalytics().then(({ data }) => setStats(data));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900 mb-1">Platform Analytics</h1>
      <p className="text-sm text-slate-500 mb-6">Aggregate performance across every clinic.</p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard label="Active Clinics" value={stats?.active_clinics ?? "—"} icon={Building2} />
        <StatCard label="Calls This Month" value={stats?.calls_this_month ?? "—"} icon={PhoneCall} />
        <StatCard label="Bookings This Month" value={stats?.bookings_this_month ?? "—"} icon={CalendarCheck} />
      </div>
    </div>
  );
}
