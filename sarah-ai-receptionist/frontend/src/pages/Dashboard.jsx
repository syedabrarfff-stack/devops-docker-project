import { useEffect, useState } from "react";
import { PhoneCall, CalendarCheck, PhoneForwarded, Zap } from "lucide-react";
import { dashboardApi } from "../services/api";
import StatCard from "../components/StatCard";

export default function Dashboard() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    dashboardApi.getStats().then(({ data }) => setStats(data));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900 mb-1">Dashboard</h1>
      <p className="text-sm text-slate-500 mb-6">Today's activity at a glance.</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Calls Today" value={stats?.calls_today ?? "—"} icon={PhoneCall} />
        <StatCard label="Calls This Week" value={stats?.calls_this_week ?? "—"} icon={PhoneCall} />
        <StatCard label="Booked Today" value={stats?.appointments_booked_today ?? "—"} icon={CalendarCheck} />
        <StatCard label="Transferred Today" value={stats?.transfers_today ?? "—"} icon={PhoneForwarded} />
      </div>

      <div className="mt-6 bg-white rounded-xl border border-slate-200 p-5">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
          <Zap size={16} className="text-brand-500" />
          Average Response Latency
        </div>
        <div className="mt-2 text-2xl font-semibold text-slate-900">
          {stats?.avg_response_ms ? `${Math.round(stats.avg_response_ms)}ms` : "—"}
        </div>
        <p className="text-xs text-slate-400 mt-1">Time from caller speech to Sarah's first spoken response.</p>
      </div>
    </div>
  );
}
