import { useState } from "react";
import { adminApi } from "../../services/api";

const EMPTY = {
  organization_name: "",
  clinic_name: "",
  clinic_slug: "",
  address: "",
  city: "",
  state: "",
  country: "US",
  timezone: "America/New_York",
  admin_email: "",
  admin_password: "",
  admin_full_name: "",
  auto_buy_twilio_number: true,
  area_code: "",
  existing_twilio_number: "",
};

export default function OnboardClinic() {
  const [form, setForm] = useState(EMPTY);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await adminApi.onboardClinic(form);
      setResult(data);
      setForm(EMPTY);
    } catch (err) {
      setError(err.response?.data?.detail || "Onboarding failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900 mb-1">Onboard New Clinic</h1>
      <p className="text-sm text-slate-500 mb-6">Create the org, clinic, dashboard login, and connect a phone number — all in one step.</p>

      {result && (
        <div className="mb-6 bg-green-50 border border-green-100 rounded-xl p-4 text-sm text-green-800">
          Clinic onboarded. Twilio number:{" "}
          <span className="font-semibold">{result.twilio_phone_number || "manual assignment needed"}</span>
        </div>
      )}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-100 rounded-xl p-4 text-sm text-red-700">{error}</div>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-slate-200 p-6 max-w-2xl space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Organization Name" value={form.organization_name} onChange={(v) => set("organization_name", v)} required />
          <Field label="Clinic Name" value={form.clinic_name} onChange={(v) => set("clinic_name", v)} required />
        </div>
        <Field label="Clinic Slug (URL-safe)" value={form.clinic_slug} onChange={(v) => set("clinic_slug", v)} required />
        <Field label="Address" value={form.address} onChange={(v) => set("address", v)} />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Field label="City" value={form.city} onChange={(v) => set("city", v)} />
          <Field label="State / Region" value={form.state} onChange={(v) => set("state", v)} />
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Country</label>
            <select
              value={form.country}
              onChange={(e) => set("country", e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="US">United States</option>
              <option value="GB">United Kingdom</option>
              <option value="CA">Canada</option>
              <option value="AU">Australia</option>
              <option value="AE">United Arab Emirates</option>
              <option value="SA">Saudi Arabia</option>
            </select>
          </div>
          <Field label="Timezone" value={form.timezone} onChange={(v) => set("timezone", v)} />
        </div>

        <div className="pt-2 border-t border-slate-100" />

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Admin Full Name" value={form.admin_full_name} onChange={(v) => set("admin_full_name", v)} required />
          <Field label="Admin Email" type="email" value={form.admin_email} onChange={(v) => set("admin_email", v)} required />
        </div>
        <Field label="Admin Password" type="password" value={form.admin_password} onChange={(v) => set("admin_password", v)} required />

        <div className="pt-2 border-t border-slate-100" />

        <Field
          label="Existing Twilio number (optional)"
          value={form.existing_twilio_number}
          onChange={(v) => set("existing_twilio_number", v)}
        />
        <p className="-mt-2 text-xs text-slate-400">
          A number already in this Twilio account (E.164, e.g. +13055551234). We wire Sarah's
          webhook to it and skip buying a new one. Porting a number in from another carrier is a
          separate multi-day process.
        </p>

        {!form.existing_twilio_number && (
          <>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={form.auto_buy_twilio_number}
                onChange={(e) => set("auto_buy_twilio_number", e.target.checked)}
              />
              Auto-purchase a new Twilio phone number
            </label>
            {form.auto_buy_twilio_number && (
              <Field label="Preferred Area Code (optional)" value={form.area_code} onChange={(v) => set("area_code", v)} />
            )}
          </>
        )}

        <button
          type="submit"
          disabled={loading}
          className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-colors disabled:opacity-50"
        >
          {loading ? "Provisioning…" : "Onboard Clinic"}
        </button>
      </form>
    </div>
  );
}

function Field({ label, value, onChange, type = "text", required = false }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      <input
        type={type}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
    </div>
  );
}
