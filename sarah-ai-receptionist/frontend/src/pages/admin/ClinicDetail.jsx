import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import Dashboard from "../Dashboard";
import CallLog from "../CallLog";
import Appointments from "../Appointments";
import Settings from "../Settings";

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "calls", label: "Calls" },
  { key: "appointments", label: "Appointments" },
  { key: "settings", label: "Settings" },
];

// Admin's window into one clinic's operational view -- the same Dashboard /
// CallLog / Appointments / Settings pages a clinic user sees, reused as-is
// with an explicit clinicId so platform_admin (who has no clinic of their
// own) can view transcripts, recordings, bookings, and config for any
// onboarded clinic. Only one tab is mounted at a time, so each tab's own
// data-fetching effect runs fresh on every switch -- no extra state to wire.
export default function ClinicDetail() {
  const { clinicId } = useParams();
  const [tab, setTab] = useState("overview");

  return (
    <div>
      <Link
        to="/admin"
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-4"
      >
        <ArrowLeft size={14} /> All clinics
      </Link>

      <div className="border-b border-slate-200 mb-6">
        <nav className="flex gap-6">
          {TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                tab === key
                  ? "border-brand-600 text-brand-700"
                  : "border-transparent text-slate-500 hover:text-slate-700"
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      </div>

      {tab === "overview" && <Dashboard clinicId={clinicId} />}
      {tab === "calls" && <CallLog clinicId={clinicId} />}
      {tab === "appointments" && <Appointments clinicId={clinicId} />}
      {tab === "settings" && <Settings clinicId={clinicId} />}
    </div>
  );
}
