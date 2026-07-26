import { useEffect, useState } from "react";
import { format } from "date-fns";
import { dashboardApi } from "../services/api";

const OUTCOME_STYLES = {
  BOOK: "bg-green-50 text-green-700",
  TRANSFER: "bg-amber-50 text-amber-700",
  END: "bg-slate-100 text-slate-600",
};

export default function CallLog() {
  const [calls, setCalls] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    dashboardApi.getCalls({ limit: 50 }).then(({ data }) => setCalls(data));
  }, []);

  async function openCall(id) {
    const { data } = await dashboardApi.getCallDetail(id);
    setSelected(data);
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900 mb-1">Call Log</h1>
      <p className="text-sm text-slate-500 mb-6">Every call Sarah has answered.</p>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-3">Time</th>
              <th className="text-left px-4 py-3">Duration</th>
              <th className="text-left px-4 py-3">Exchanges</th>
              <th className="text-left px-4 py-3">Outcome</th>
              <th></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {calls.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50 cursor-pointer" onClick={() => openCall(c.id)}>
                <td className="px-4 py-3">{format(new Date(c.started_at), "MMM d, h:mm a")}</td>
                <td className="px-4 py-3">{c.duration_seconds ? `${Math.round(c.duration_seconds)}s` : "—"}</td>
                <td className="px-4 py-3">{c.exchange_count ?? "—"}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${OUTCOME_STYLES[c.outcome] || "bg-slate-100 text-slate-600"}`}>
                    {c.outcome || "completed"}
                  </span>
                </td>
                <td className="px-4 py-3 text-brand-600 text-xs font-medium">View →</td>
              </tr>
            ))}
            {calls.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-400">
                  No calls yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50" onClick={() => setSelected(null)}>
          <div className="bg-white rounded-xl max-w-lg w-full max-h-[80vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <h2 className="font-semibold text-lg">Call Transcript</h2>
              <button onClick={() => setSelected(null)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>
            <div className="space-y-3">
              {selected.transcript.map((turn, i) => (
                <div key={i} className={turn.role === "caller" ? "text-slate-800" : "text-brand-700"}>
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-400 mr-2">
                    {turn.role === "caller" ? "Caller" : "Sarah"}
                  </span>
                  {turn.content}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
