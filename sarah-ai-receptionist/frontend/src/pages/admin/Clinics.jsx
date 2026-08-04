import { useEffect, useState } from "react";
import { format } from "date-fns";
import { Link } from "react-router-dom";
import { adminApi } from "../../services/api";

export default function Clinics() {
  const [clinics, setClinics] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    adminApi.listClinics()
      .then(({ data }) => setClinics(data))
      .catch((err) => setError(err.response?.data?.detail || "Failed to load clinics."));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900 mb-1">All Clinics</h1>
      <p className="text-sm text-slate-500 mb-6">Every clinic running on the Sarah platform.</p>
      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-3">{error}</div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-3">Clinic</th>
              <th className="text-left px-4 py-3">Phone Number</th>
              <th className="text-left px-4 py-3">Plan</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="text-left px-4 py-3">Onboarded</th>
              <th></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {clinics.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50">
                <td className="px-4 py-3 font-medium">{c.name}</td>
                <td className="px-4 py-3">{c.twilio_phone_number || "—"}</td>
                <td className="px-4 py-3 capitalize">{c.plan}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${c.is_active ? "bg-green-50 text-green-700" : "bg-slate-100 text-slate-500"}`}>
                    {c.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-500">{format(new Date(c.created_at), "MMM d, yyyy")}</td>
                <td className="px-4 py-3 text-right">
                  <Link to={`/admin/clinics/${c.id}`} className="text-brand-600 text-xs font-medium hover:text-brand-700">
                    View Dashboard →
                  </Link>
                </td>
              </tr>
            ))}
            {clinics.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                  No clinics onboarded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
