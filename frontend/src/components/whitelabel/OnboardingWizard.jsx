import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, ChevronRight, Loader2, Zap, Users, Mail, Plug, Target, Eye, Rocket, Building2 } from 'lucide-react'
import api from '../../services/api'

const STEPS = [
  { num: 1, label: 'Branding',      icon: Zap },
  { num: 2, label: 'Your Team',     icon: Users },
  { num: 3, label: 'Email',         icon: Mail },
  { num: 4, label: 'Integrations',  icon: Plug },
  { num: 5, label: 'Market Focus',  icon: Target },
  { num: 6, label: 'Review',        icon: Eye },
  { num: 7, label: 'Go Live',       icon: Rocket },
]

const Input = ({ label, value, onChange, placeholder, type = 'text' }) => (
  <div className="mb-4">
    <label className="block text-xs text-white/50 mb-1">{label}</label>
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white/90 outline-none focus:border-jarvis-blue/40"
    />
  </div>
)

function TenantPicker({ onSelect }) {
  const [tenants, setTenants] = useState(null)
  const [error, setError] = useState(null)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ name: '', admin_email: '', admin_password: '' })

  useEffect(() => {
    api.get('/api/v1/admin/tenants').then(r => setTenants(r.data.tenants || []))
      .catch(err => setError(err.response?.data?.detail || err.message))
  }, [])

  async function createTenant() {
    setCreating(true); setError(null)
    try {
      const r = await api.post('/api/v1/admin/tenants', { ...form, plan_tier: 'STARTER' })
      onSelect(r.data.tenant.tenant_id)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
    setCreating(false)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950 flex items-center justify-center p-6">
      <div className="w-full max-w-lg">
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500/30 to-purple-500/30 border border-blue-500/30 flex items-center justify-center mx-auto mb-4">
            <Building2 size={22} className="text-blue-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">Select an Organization</h1>
          <p className="text-white/40 text-sm mt-1">Resume onboarding for an existing tenant, or create a new one.</p>
        </div>

        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-6">
          {error && <div className="mb-4 bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-xs text-red-400">{error}</div>}

          {tenants === null ? (
            <div className="flex justify-center py-6"><Loader2 size={18} className="animate-spin text-white/30" /></div>
          ) : tenants.length > 0 ? (
            <div className="mb-6 space-y-2">
              {tenants.map(t => (
                <button key={t.id} onClick={() => onSelect(t.tenant_id)}
                  className="w-full text-left bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl px-4 py-3 transition-all">
                  <div className="text-sm text-white/90 font-medium">{t.name}</div>
                  <div className="text-xs text-white/40 mt-0.5">{t.plan_tier} · {t.is_active ? 'active' : 'inactive'}</div>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-white/40 text-sm mb-6">No tenants yet — create the first one below.</p>
          )}

          <div className="pt-4 border-t border-white/10">
            <h2 className="text-white font-semibold mb-4 text-sm">Create New Organization</h2>
            <Input label="Company Name *" value={form.name} onChange={v => setForm(f => ({ ...f, name: v }))} placeholder="Growth Agency Ltd" />
            <Input label="Admin Email *" value={form.admin_email} onChange={v => setForm(f => ({ ...f, admin_email: v }))} placeholder="admin@youragency.com" />
            <Input label="Admin Password *" type="password" value={form.admin_password} onChange={v => setForm(f => ({ ...f, admin_password: v }))} placeholder="12+ characters" />
            <button onClick={createTenant} disabled={creating || !form.name || !form.admin_email || form.admin_password.length < 12}
              className="w-full mt-2 flex items-center justify-center gap-2 bg-blue-500/20 border border-blue-500/40 text-blue-400 px-5 py-2.5 rounded-xl text-sm font-medium hover:bg-blue-500/30 transition-all disabled:opacity-50">
              {creating ? <Loader2 size={14} className="animate-spin" /> : null}
              Create & Continue
              {!creating && <ChevronRight size={14} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function OnboardingWizard({ tenantId, onComplete }) {
  const [resolvedTenantId, setResolvedTenantId] = useState(tenantId || null)
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // Step data
  const [branding, setBranding] = useState({ company_name: '', tagline: '', logo_url: '', primary_color: '#3b82f6', company_website: '', founder_name: '' })
  const [emailDomain, setEmailDomain] = useState('')
  const [personas, setPersonas] = useState([{ name: '', role: 'sales', title: 'Client Acquisition Specialist', is_primary_outreach: true }])
  const [emailCfg, setEmailCfg] = useState({ executive_email: '', executive_name: 'Joseph David', reply_to_name: '' })
  const [integrations, setIntegrations] = useState({ apollo_api_key: '', hubspot_api_key: '', slack_webhook_url: '' })
  const [market, setMarket] = useState({ target_markets: '', target_industries: '', service_offerings: '', icp_description: '' })
  const [review, setReview] = useState(null)

  async function runStep() {
    setLoading(true); setError(null)
    try {
      let r
      const base = `/api/v1/whitelabel/onboarding/${resolvedTenantId}`
      if (step === 1) r = await api.post(`${base}/step1-branding`, branding)
      if (step === 2) r = await api.post(`${base}/step2-personas`, {
        personas, email_domain: emailDomain
      })
      if (step === 3) r = await api.post(`${base}/step3-email`, emailCfg)
      if (step === 4) r = await api.post(`${base}/step4-integrations`, integrations)
      if (step === 5) r = await api.post(`${base}/step5-market`, {
        target_markets: market.target_markets.split(',').map(s => s.trim()).filter(Boolean),
        target_industries: market.target_industries.split(',').map(s => s.trim()).filter(Boolean),
        service_offerings: market.service_offerings.split(',').map(s => s.trim()).filter(Boolean),
        icp_description: market.icp_description,
      })
      if (step === 6) {
        const rev = await api.get(`${base}/step6-review`)
        setReview(rev.data); setResult(rev.data); setStep(7); setLoading(false); return
      }
      if (step === 7) {
        r = await api.post(`${base}/step7-golive`)
        setResult(r.data)
        if (onComplete) onComplete(r.data)
        setLoading(false); return
      }
      setResult(r.data)
      setStep(s => Math.min(s + 1, 7))
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
    setLoading(false)
  }

  const addPersona = () => setPersonas(p => [...p, { name: '', role: 'sales', title: '', is_primary_outreach: false }])
  const updatePersona = (i, field, val) => setPersonas(p => p.map((item, idx) => idx === i ? { ...item, [field]: val } : item))

  if (!resolvedTenantId) {
    return <TenantPicker onSelect={setResolvedTenantId} />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950 flex items-center justify-center p-6">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500/30 to-purple-500/30 border border-blue-500/30 flex items-center justify-center mx-auto mb-4">
            <Zap size={22} className="text-blue-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">JARVIS Setup Wizard</h1>
          <p className="text-white/40 text-sm mt-1">Configure your AI operations brain in 7 steps</p>
        </div>

        {/* Step indicators */}
        <div className="flex items-center justify-center gap-1 mb-8 flex-wrap">
          {STEPS.map(s => (
            <div key={s.num} className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium transition-all
              ${step === s.num ? 'bg-blue-500/20 border border-blue-500/40 text-blue-400' :
                step > s.num ? 'bg-green-500/10 border border-green-500/20 text-green-400' :
                'bg-white/5 border border-white/10 text-white/30'}`}>
              {step > s.num ? <CheckCircle2 size={10} /> : <s.icon size={10} />}
              {s.label}
            </div>
          ))}
        </div>

        {/* Step content */}
        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-6">
          <AnimatePresence mode="wait">
            <motion.div key={step} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.2 }}>

              {step === 1 && (
                <div>
                  <h2 className="text-white font-semibold mb-4">Company Branding</h2>
                  <Input label="Company Name *" value={branding.company_name} onChange={v => setBranding(b => ({ ...b, company_name: v }))} placeholder="Growth Agency Ltd" />
                  <Input label="Tagline" value={branding.tagline} onChange={v => setBranding(b => ({ ...b, tagline: v }))} placeholder="AI-Powered Operations for Modern Businesses" />
                  <Input label="Founder Name" value={branding.founder_name} onChange={v => setBranding(b => ({ ...b, founder_name: v }))} placeholder="Your name" />
                  <Input label="Website" value={branding.company_website} onChange={v => setBranding(b => ({ ...b, company_website: v }))} placeholder="https://youragency.com" />
                  <Input label="Brand Color" type="color" value={branding.primary_color} onChange={v => setBranding(b => ({ ...b, primary_color: v }))} placeholder="#3b82f6" />
                </div>
              )}

              {step === 2 && (
                <div>
                  <h2 className="text-white font-semibold mb-1">Team Personas</h2>
                  <p className="text-white/40 text-xs mb-4">These names appear in all outreach emails. Clients see real people.</p>
                  <Input label="Email Domain *" value={emailDomain} onChange={setEmailDomain} placeholder="youragency.com" />
                  {personas.map((p, i) => (
                    <div key={i} className="bg-white/5 rounded-xl p-3 mb-3 border border-white/10">
                      <div className="text-xs text-white/40 mb-2">Persona {i + 1}{p.is_primary_outreach ? ' (Primary Sender)' : ''}</div>
                      <Input label="Full Name" value={p.name} onChange={v => updatePersona(i, 'name', v)} placeholder="James Harper" />
                      <Input label="Title" value={p.title} onChange={v => updatePersona(i, 'title', v)} placeholder="Client Acquisition Specialist" />
                    </div>
                  ))}
                  {personas.length < 9 && (
                    <button onClick={addPersona} className="text-xs text-blue-400 hover:text-blue-300 underline">+ Add another team member</button>
                  )}
                </div>
              )}

              {step === 3 && (
                <div>
                  <h2 className="text-white font-semibold mb-1">Executive Email Identity</h2>
                  <p className="text-white/40 text-xs mb-4">JARVIS sends outreach from this SES identity. The executive persona is Joseph David.</p>
                  <Input label="Executive Email Address *" value={emailCfg.executive_email} onChange={v => setEmailCfg(e => ({ ...e, executive_email: v }))} placeholder="joseph.david@aliyarsolutions.com" />
                  <Input label="Display Name" value={emailCfg.executive_name} onChange={v => setEmailCfg(e => ({ ...e, executive_name: v }))} placeholder="Joseph David" />
                  <Input label="Reply-To Name" value={emailCfg.reply_to_name} onChange={v => setEmailCfg(e => ({ ...e, reply_to_name: v }))} placeholder="Joseph David" />
                  <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-xs text-amber-400 mt-2">
                    AWS SES production access and sender verification are required before client delivery can begin.
                  </div>
                </div>
              )}

              {step === 4 && (
                <div>
                  <h2 className="text-white font-semibold mb-1">Integrations</h2>
                  <p className="text-white/40 text-xs mb-4">All optional. JARVIS works without them — but unlocks more power with them.</p>
                  <Input label="Apollo API Key" value={integrations.apollo_api_key} onChange={v => setIntegrations(i => ({ ...i, apollo_api_key: v }))} placeholder="For lead enrichment" />
                  <Input label="HubSpot API Key" value={integrations.hubspot_api_key} onChange={v => setIntegrations(i => ({ ...i, hubspot_api_key: v }))} placeholder="For CRM sync" />
                  <Input label="Slack Webhook URL" value={integrations.slack_webhook_url} onChange={v => setIntegrations(i => ({ ...i, slack_webhook_url: v }))} placeholder="For daily briefing alerts" />
                </div>
              )}

              {step === 5 && (
                <div>
                  <h2 className="text-white font-semibold mb-1">Market Focus</h2>
                  <p className="text-white/40 text-xs mb-4">Tell JARVIS exactly who to hunt for you.</p>
                  <Input label="Target Markets (comma separated)" value={market.target_markets} onChange={v => setMarket(m => ({ ...m, target_markets: v }))} placeholder="UK, USA, UAE, Australia" />
                  <Input label="Target Industries (comma separated)" value={market.target_industries} onChange={v => setMarket(m => ({ ...m, target_industries: v }))} placeholder="SaaS, FinTech, E-commerce, Healthcare" />
                  <Input label="Your Services (comma separated)" value={market.service_offerings} onChange={v => setMarket(m => ({ ...m, service_offerings: v }))} placeholder="AI Automation, Lead Generation, CRM Setup" />
                  <div className="mb-4">
                    <label className="block text-xs text-white/50 mb-1">Ideal Client Profile</label>
                    <textarea value={market.icp_description} onChange={e => setMarket(m => ({ ...m, icp_description: e.target.value }))}
                      placeholder="50-500 employee companies, B2B, £2M+ revenue, have tried automation before but failed..."
                      maxLength={5000} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white/90 outline-none focus:border-blue-500/40 h-24 resize-none" />
                  </div>
                </div>
              )}

              {step === 6 && review && (
                <div>
                  <h2 className="text-white font-semibold mb-4">Review Before Going Live</h2>
                  {Object.entries(review.checklist?.steps || {}).map(([key, done]) => (
                    <div key={key} className="flex items-center gap-3 py-2 border-b border-white/5">
                      <CheckCircle2 size={14} className={done ? 'text-green-400' : 'text-white/20'} />
                      <span className="text-sm text-white/70 capitalize">{key.replace(/_/g, ' ')}</span>
                      <span className={`ml-auto text-xs ${done ? 'text-green-400' : 'text-amber-400'}`}>{done ? 'Complete' : 'Missing'}</span>
                    </div>
                  ))}
                  {review.warning && <div className="mt-4 bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-xs text-amber-400">{review.warning}</div>}
                </div>
              )}

              {step === 7 && (
                <div className="text-center py-4">
                  {result?.status === 'LIVE' ? (
                    <div>
                      <div className="w-16 h-16 rounded-full bg-green-500/20 border border-green-500/30 flex items-center justify-center mx-auto mb-4">
                        <Rocket size={28} className="text-green-400" />
                      </div>
                      <h2 className="text-white font-bold text-xl mb-2">JARVIS is Live</h2>
                      <p className="text-white/50 text-sm mb-4">{result.message}</p>
                      <a href="/dashboard" className="inline-block bg-blue-500/20 border border-blue-500/40 text-blue-400 px-6 py-2.5 rounded-xl text-sm font-medium hover:bg-blue-500/30 transition-all">
                        Open Dashboard →
                      </a>
                    </div>
                  ) : (
                    <div>
                      <h2 className="text-white font-semibold mb-2">Ready to Launch?</h2>
                      <p className="text-white/40 text-sm">JARVIS will start operating for your agency immediately. Lead discovery begins at next scheduled run.</p>
                    </div>
                  )}
                </div>
              )}

            </motion.div>
          </AnimatePresence>

          {/* Error */}
          {error && <div className="mt-4 bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-xs text-red-400">{error}</div>}

          {/* Actions */}
          {!(step === 7 && result?.status === 'LIVE') && (
            <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/10">
              <button onClick={() => setStep(s => Math.max(1, s - 1))} disabled={step === 1}
                className="text-sm text-white/40 hover:text-white/70 disabled:opacity-30 transition-all">
                ← Back
              </button>
              <button onClick={runStep} disabled={loading}
                className="flex items-center gap-2 bg-blue-500/20 border border-blue-500/40 text-blue-400 px-5 py-2 rounded-xl text-sm font-medium hover:bg-blue-500/30 transition-all disabled:opacity-50">
                {loading ? <Loader2 size={14} className="animate-spin" /> : null}
                {step === 7 ? 'Launch JARVIS' : step === 6 ? 'Confirm' : 'Save & Continue'}
                {!loading && <ChevronRight size={14} />}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
