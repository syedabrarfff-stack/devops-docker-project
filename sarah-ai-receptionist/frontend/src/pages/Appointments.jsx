import { useEffect, useState } from "react";
import { appointmentsApi } from "../services/api";
import { clinicZoneLabel, formatInClinicZone, useClinicTimezone } from "../lib/clinicTime";

export default function Appointments() {
  const [appointments, setAppointments] = useState([]);
  const [error, setError] = useState(null);
  const timeZone = useClinicTimezone();
  const zoneLabel = clinicZoneLabel(timeZone);

  useEffect(() => {
    load();
  }, []);

  function load() {
    appointmentsApi.list({ upcoming_only: true })
      .then(({ data }) => setAppointments(data))
      .catch((err) => setError(err.response?.data?.detail || "Failed to load appointments."));
  }

  async function markStatus(id, status) {
    await appointmentsApi.update(id, { status });
    load();
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900 mb-1">Appointments</h1>
      <p className="text-sm text-slate-500 mb-6">Upcoming bookings from Sarah and manual entries.</p>
      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-3">{error}</div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-3">
                Date &amp; Time{zoneLabel && <span className="ml-1 normal-case text-slate-400">({zoneLabel})</span>}
              </th>
              <th className="text-left px-4 py-3">Patient</th>
              <th className="text-left px-4 py-3">Service</th>
              <th className="text-left px-4 py-3">Source</th>
              <th className="text-left px-4 py-3">Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {appointments.map((a) => (
              <tr key={a.id} className="hover:bg-slate-50">
                <td className="px-4 py-3">{formatInClinicZone(a.appointment_datetime, timeZone)}</td>
                <td className="px-4 py-3">{a.patient_name || "—"}</td>
                <td className="px-4 py-3">{a.service_type}</td>
                <td className="px-4 py-3 text-xs text-slate-400 uppercase">{a.source}</td>
                <td className="px-4 py-3 capitalize">{a.status}</td>
                <td className="px-4 py-3 space-x-2 text-xs">
                  {a.status !== "confirmed" && (
                    <button onClick={() => markStatus(a.id, "confirmed")} className="text-green-600 font-medium">
                      Confirm
                    </button>
                  )}
                  {a.status !== "cancelled" && (
                    <button onClick={() => markStatus(a.id, "cancelled")} className="text-red-500 font-medium">
                      Cancel
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {appointments.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                  No upcoming appointments.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
