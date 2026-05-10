import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../../services/api";

const STAGES = ["discovery", "proposal", "negotiation", "closed_won", "closed_lost"];
const STAGE_COLORS = {
  discovery: "text-blue-400",
  proposal: "text-yellow-400",
  negotiation: "text-orange-400",
  closed_won: "text-green-400",
  closed_lost: "text-red-400",
};

function ContactCard({ contact }) {
  return (
    <div className="glass rounded-xl p-4 border border-white/5 hover:border-blue-500/30 transition-all">
      <div className="flex items-start justify-between mb-2">
        <div>
          <p className="font-semibold text-white">{contact.name}</p>
          <p className="text-sm text-gray-400">{contact.title || "—"}</p>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full border ${
          contact.status === "active" ? "border-green-500/40 text-green-400 bg-green-500/10" :
          contact.status === "lead" ? "border-blue-500/40 text-blue-400 bg-blue-500/10" :
          "border-gray-600 text-gray-400"
        }`}>{contact.status || "new"}</span>
      </div>
      <p className="text-xs text-gray-500 truncate">{contact.email || "No email"}</p>
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-gray-600">{contact.country || "Unknown"}</span>
        <span className="text-xs text-blue-400">Score: {contact.score || 0}</span>
      </div>
      {contact.tags?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {contact.tags.slice(0, 3).map(tag => (
            <span key={tag} className="text-xs px-1.5 py-0.5 rounded bg-white/5 text-gray-400">{tag}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function DealRow({ deal }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-white/5 last:border-0">
      <div>
        <p className="text-sm font-medium text-white">{deal.title}</p>
        <p className="text-xs text-gray-500">{deal.service_type || "General"}</p>
      </div>
      <div className="text-right">
        <p className="text-sm font-semibold text-white">
          {deal.currency} {Number(deal.value || 0).toLocaleString()}
        </p>
        <p className={`text-xs ${STAGE_COLORS[deal.stage] || "text-gray-400"}`}>{deal.stage}</p>
      </div>
    </div>
  );
}

export default function CRMDashboard() {
  const [tab, setTab] = useState("contacts");
  const [contacts, setContacts] = useState([]);
  const [deals, setDeals] = useState([]);
  const [pipeline, setPipeline] = useState({});
  const [contactStats, setContactStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [showAddContact, setShowAddContact] = useState(false);
  const [newContact, setNewContact] = useState({ name: "", email: "", title: "", country: "" });

  useEffect(() => {
    loadAll();
  }, []);

  async function loadAll() {
    setLoading(true);
    try {
      const [c, d, p, cs] = await Promise.all([
        api.get("/crm/contacts?limit=50").then(r => r.data),
        api.get("/crm/deals?limit=50").then(r => r.data),
        api.get("/crm/deals/pipeline").then(r => r.data),
        api.get("/crm/contacts/stats").then(r => r.data),
      ]);
      setContacts(c);
      setDeals(d);
      setPipeline(p);
      setContactStats(cs);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }

  async function addContact() {
    try {
      await api.post("/crm/contacts", newContact);
      setShowAddContact(false);
      setNewContact({ name: "", email: "", title: "", country: "" });
      loadAll();
    } catch (e) {
      console.error(e);
    }
  }

  const totalPipelineValue = deals
    .filter(d => !["closed_lost"].includes(d.stage))
    .reduce((s, d) => s + (d.value || 0), 0);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">CRM</h1>
          <p className="text-gray-400 text-sm">Contacts, companies &amp; deals</p>
        </div>
        <button
          onClick={() => setShowAddContact(true)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          + Add Contact
        </button>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Contacts", value: contactStats.total || 0, color: "text-blue-400" },
          { label: "Active", value: contactStats.active || 0, color: "text-green-400" },
          { label: "Open Deals", value: deals.filter(d => !d.stage.includes("closed")).length, color: "text-yellow-400" },
          { label: "Pipeline Value", value: `$${(totalPipelineValue / 1000).toFixed(0)}k`, color: "text-purple-400" },
        ].map(s => (
          <div key={s.label} className="glass rounded-xl p-4 border border-white/5">
            <p className="text-gray-400 text-xs mb-1">{s.label}</p>
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white/5 rounded-lg p-1 w-fit">
        {["contacts", "deals"].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all capitalize ${
              tab === t ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="text-center text-gray-500 py-12">Loading...</div>
      ) : tab === "contacts" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {contacts.length === 0 ? (
            <p className="text-gray-500 col-span-3 text-center py-8">No contacts yet. Add your first one.</p>
          ) : (
            contacts.map(c => <ContactCard key={c.id} contact={c} />)
          )}
        </div>
      ) : (
        <div className="glass rounded-xl border border-white/5 divide-y divide-white/5">
          {/* Pipeline summary */}
          <div className="grid grid-cols-5 gap-2 p-4">
            {STAGES.map(stage => {
              const count = deals.filter(d => d.stage === stage).length;
              const val = deals.filter(d => d.stage === stage).reduce((s, d) => s + (d.value || 0), 0);
              return (
                <div key={stage} className="text-center">
                  <p className={`text-xs font-medium ${STAGE_COLORS[stage]}`}>{stage.replace("_", " ")}</p>
                  <p className="text-lg font-bold text-white">{count}</p>
                  <p className="text-xs text-gray-500">${(val / 1000).toFixed(0)}k</p>
                </div>
              );
            })}
          </div>
          <div className="p-4">
            {deals.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No deals yet.</p>
            ) : (
              deals.map(d => <DealRow key={d.id} deal={d} />)
            )}
          </div>
        </div>
      )}

      {/* Add Contact Modal */}
      <AnimatePresence>
        {showAddContact && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50"
            onClick={() => setShowAddContact(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="glass rounded-2xl border border-white/10 p-6 w-full max-w-md"
              onClick={e => e.stopPropagation()}
            >
              <h2 className="text-lg font-bold text-white mb-4">New Contact</h2>
              <div className="space-y-3">
                {[
                  { key: "name", placeholder: "Full name *", required: true },
                  { key: "email", placeholder: "Email address" },
                  { key: "title", placeholder: "Job title" },
                  { key: "country", placeholder: "Country" },
                ].map(f => (
                  <input
                    key={f.key}
                    value={newContact[f.key]}
                    onChange={e => setNewContact(p => ({ ...p, [f.key]: e.target.value }))}
                    placeholder={f.placeholder}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50"
                  />
                ))}
              </div>
              <div className="flex gap-3 mt-5">
                <button
                  onClick={() => setShowAddContact(false)}
                  className="flex-1 py-2 rounded-lg border border-white/10 text-gray-400 hover:text-white text-sm transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={addContact}
                  disabled={!newContact.name}
                  className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white text-sm font-medium transition-colors"
                >
                  Create Contact
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
