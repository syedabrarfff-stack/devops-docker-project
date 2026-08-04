import { useEffect, useState } from "react";
import { dashboardApi } from "../services/api";
import { clinicZoneLabel, formatInClinicZone, useClinicTimezone } from "../lib/clinicTime";

const OUTCOME_STYLES = {
  BOOK: "bg-green-50 text-green-700",
  TRANSFER: "bg-amber-50 text-amber-700",
  END: "bg-slate-100 text-slate-600",
};

export default function CallLog() {
  const [calls, setCalls] = useState([]);
  const [selected, setSelected] = useState(null);
  const [recordingUrl, setRecordingUrl] = useState(null);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const timeZone = useClinicTimezone();
  const zoneLabel = clinicZoneLabel(timeZone);

  // Debounced so typing doesn't fire a request per keystroke. Empty query
  // returns the recent calls unfiltered.
  useEffect(() => {
    const params = { limit: 50 };
    if (query.trim()) params.q = query.trim();
    const t = setTimeout(() => {
      dashboardApi.getCalls(params)
        .then(({ data }) => { setCalls(data); setError(null); })
        .catch((err) => setError(err.response?.data?.detail || "Failed to load call log."));
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  async function openCall(id) {
    setRecordingUrl(null);
    const { data } = await dashboardApi.getCallDetail(id);
    setSelected(data);
    if (data.recording_s3_key) {
      try {
        const { data: rec } = await dashboardApi.getRecordingUrl(id);
        setRecordingUrl(rec.url);
      } catch {
        setRecordingUrl(null);
      }
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900 mb-1">Call Log</h1>
      <p className="text-sm text-slate-500 mb-4">Every call Sarah has answered.</p>

      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search by phone number, summary, or anything said on the call…"
        className="w-full mb-6 px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-3">{error}</div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-3">
                Time{zoneLabel && <span className="ml-1 normal-case text-slate-400">({zoneLabel})</span>}
              </th>
              <th className="text-left px-4 py-3">Duration</th>
              <th className="text-left px-4 py-3">Exchanges</th>
              <th className="text-left px-4 py-3">Outcome</th>
              <th></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {calls.map((c) => (
              <tr
                key={c.id}
                className="hover:bg-slate-50 cursor-pointer focus:outline-none focus:bg-slate-50"
                tabIndex={0}
                role="button"
                aria-label={`View call from ${formatInClinicZone(c.started_at, timeZone)}`}
                onClick={() => openCall(c.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    openCall(c.id);
                  }
                }}
              >
                <td className="px-4 py-3">{formatInClinicZone(c.started_at, timeZone)}</td>
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
                  {query.trim() ? "No calls match your search." : "No calls yet."}
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
              <button
                onClick={() => setSelected(null)}
                aria-label="Close call transcript"
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>
            {recordingUrl && (
              <audio controls src={recordingUrl} className="w-full mb-4" preload="none">
                Your browser does not support inline audio playback.
              </audio>
            )}
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
