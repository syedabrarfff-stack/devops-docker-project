import { useEffect, useState } from "react";
import { PhoneCall, CalendarCheck, PhoneForwarded, Zap, PhoneMissed } from "lucide-react";
import { dashboardApi } from "../services/api";
import StatCard from "../components/StatCard";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    dashboardApi.getStats()
      .then(({ data }) => setStats(data))
      .catch((err) => setError(err.response?.data?.detail || "Failed to load stats."));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900 mb-1">Dashboard</h1>
      <p className="text-sm text-slate-500 mb-6">Today's activity at a glance.</p>
      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-3">{error}</div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Calls Today" value={stats?.calls_today ?? "—"} icon={PhoneCall} />
        <StatCard label="Booked Today" value={stats?.appointments_booked_today ?? "—"} icon={CalendarCheck} />
        <StatCard label="Transferred Today" value={stats?.transfers_today ?? "—"} icon={PhoneForwarded} />
        <StatCard label="Hung Up Early" value={stats?.abandoned_today ?? "—"} icon={PhoneMissed} />
      </div>

      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <Zap size={16} className="text-brand-500" />
            Average Response Latency
          </div>
          <div className="mt-2 text-2xl font-semibold text-slate-900">
            {stats?.avg_response_ms ? `${Math.round(stats.avg_response_ms)}ms` : "—"}
          </div>
          <p className="text-xs text-slate-400 mt-1">Time from caller speech to Sarah's first spoken response.</p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <PhoneMissed size={16} className="text-amber-500" />
            Calls Needing Attention Today
          </div>
          <div className="mt-2 text-2xl font-semibold text-slate-900">
            {stats ? (stats.abandoned_today + stats.unanswered_transfers_today) : "—"}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Callers who hung up before engaging ({stats?.abandoned_today ?? 0}) plus transfers the front
            desk didn't pick up ({stats?.unanswered_transfers_today ?? 0}).
          </p>
        </div>
      </div>
    </div>
  );
}
