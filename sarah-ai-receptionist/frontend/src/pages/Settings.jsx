import { useEffect, useState } from "react";
import { dashboardApi } from "../services/api";

export default function Settings() {
  const [form, setForm] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    dashboardApi.getSettings().then(({ data }) => setForm(data));
  }, []);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
    setSaved(false);
  }

  async function save() {
    await dashboardApi.updateSettings({
      name: form.name,
      address: form.address,
      city: form.city,
      state: form.state,
      timezone: form.timezone,
      sarah_name: form.sarah_name,
    });
    setSaved(true);
  }

  if (!form) return null;

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900 mb-1">Settings</h1>
      <p className="text-sm text-slate-500 mb-6">Clinic details and how Sarah introduces herself.</p>

      <div className="bg-white rounded-xl border border-slate-200 p-6 max-w-xl space-y-4">
        <Field label="Clinic Name" value={form.name} onChange={(v) => set("name", v)} />
        <Field label="Sarah's Name" value={form.sarah_name} onChange={(v) => set("sarah_name", v)} />
        <Field label="Address" value={form.address || ""} onChange={(v) => set("address", v)} />
        <div className="grid grid-cols-2 gap-4">
          <Field label="City" value={form.city || ""} onChange={(v) => set("city", v)} />
          <Field label="State" value={form.state || ""} onChange={(v) => set("state", v)} />
        </div>
        <Field label="Timezone" value={form.timezone} onChange={(v) => set("timezone", v)} />

        <div className="pt-2 border-t border-slate-100">
          <div className="text-xs text-slate-400">Twilio Number</div>
          <div className="text-sm font-medium text-slate-700">{form.twilio_phone_number || "Not assigned"}</div>
        </div>

        <button
          onClick={save}
          className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          Save Changes
        </button>
        {saved && <span className="ml-3 text-sm text-green-600">Saved.</span>}
      </div>
    </div>
  );
}

function Field({ label, value, onChange }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
    </div>
  );
}
