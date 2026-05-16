import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import DashboardApp from './App.jsx';
import {
  Activity,
  ArrowRight,
  BarChart3,
  Bot,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  CircleDollarSign,
  CloudCog,
  DatabaseZap,
  Headphones,
  Layers3,
  LockKeyhole,
  MailCheck,
  Menu,
  Network,
  Phone,
  Radar,
  Rocket,
  ServerCog,
  ShieldCheck,
  Sparkles,
  Target,
  UsersRound,
  Workflow,
  X,
  Zap,
} from 'lucide-react';
import './index.css';
import './styles.css';

const serviceGroups = [
  {
    icon: Target,
    title: 'Revenue Systems',
    summary: 'Lead discovery, CRM workflows, proposal drafting, approval packets, and outreach execution.',
    items: ['Lead generation', 'Market discovery', 'CRM deal creation', 'Sales approval flows'],
    accent: 'cyan',
  },
  {
    icon: Bot,
    title: 'Workflow Automation',
    summary: 'Executive workflows, operational logic, voice experiences, scheduling, and internal operating systems.',
    items: ['Workflow assistants', 'Voice systems', 'Process coordination', 'Internal support tools'],
    accent: 'violet',
  },
  {
    icon: CloudCog,
    title: 'Cloud & DevOps',
    summary: 'AWS infrastructure, Docker production runtime, CI/CD, Terraform, monitoring, and release discipline.',
    items: ['AWS architecture', 'Docker deployments', 'Kubernetes planning', 'Jenkins and CI/CD'],
    accent: 'blue',
  },
  {
    icon: ShieldCheck,
    title: 'Security & Reliability',
    summary: 'Defensive scans, credential hygiene, uptime checks, incident detection, and safe production controls.',
    items: ['Defense monitoring', 'Approval safety', 'Secret protection', 'Health checks'],
    accent: 'emerald',
  },
  {
    icon: BarChart3,
    title: 'Business Intelligence',
    summary: 'Dashboards, forecasting, live metrics, weekly optimization reports, and technology radar reviews.',
    items: ['Live dashboards', 'Revenue forecast', 'Tech radar', 'Executive briefings'],
    accent: 'amber',
  },
  {
    icon: Layers3,
    title: 'Digital Platforms',
    summary: 'Client portals, operational dashboards, SaaS interfaces, API integrations, and premium web systems.',
    items: ['Client portals', 'Operational dashboards', 'SaaS builds', 'API integrations'],
    accent: 'rose',
  },
];

const stack = [
  'AWS',
  'Docker',
  'Kubernetes',
  'Terraform',
  'Jenkins',
  'FastAPI',
  'React',
  'PostgreSQL',
  'Redis',
  'Workflow Automation',
  'Cloud Model Services',
  'Operational Intelligence',
  'Vector Search',
  'WebSockets',
  'OAuth',
  'CI/CD',
  'Monitoring',
  'SMTP',
  'Apollo',
  'Google APIs',
];

const architecture = [
  {
    title: 'Command Layer',
    icon: BrainCircuit,
    text: 'Cloud intelligence, service health checks, operational memory, and task classification.',
  },
  {
    title: 'Execution Layer',
    icon: Workflow,
    text: 'Revenue engine, scheduler, CRM sync, lead scoring, outreach drafts, proposal packets, and workflow runners.',
  },
  {
    title: 'Approval Layer',
    icon: CheckCircle2,
    text: 'External sends, contracts, payments, and high-risk changes stay behind Captain approval before execution.',
  },
  {
    title: 'Reliability Layer',
    icon: ShieldCheck,
    text: 'Defensive scans, container health, credential diagnostics, incident reporting, and production-safe recovery paths.',
  },
];

const departments = [
  ['Client Acquisition', 'Pipeline design, ICP targeting, outreach strategy, and revenue operations.'],
  ['Workflow Automation', 'Workflow systems, voice-enabled interfaces, and operational intelligence.'],
  ['Cloud Infrastructure', 'AWS architecture, Docker runtime, deployment safety, and observability.'],
  ['DevOps Engineering', 'CI/CD, Terraform, Kubernetes, Jenkins, monitoring, and release operations.'],
  ['Cybersecurity Unit', 'Risk reviews, vulnerability assessment, access control, and defensive posture.'],
  ['Client Success', 'Onboarding, project coordination, feedback loops, retainers, and account health.'],
];

const proof = [
  ['30', 'Service divisions'],
  ['26', 'Backend API route files'],
  ['17', 'Scheduled operating jobs'],
  ['11+', 'Intelligence routes'],
  ['24/7', 'Cloud-first runtime'],
  ['100%', 'Approval-gated outreach'],
];

const journey = [
  ['Discover', 'Find high-fit buyers and operational pain across target markets.'],
  ['Qualify', 'Score leads, enrich company context, and create clean CRM records.'],
  ['Draft', 'Generate outreach, proposal drafts, pricing logic, and approval packets.'],
  ['Approve', 'Review every external client action before it leaves the system.'],
  ['Deliver', 'Run cloud, workflow, dashboard, and delivery infrastructure workstreams.'],
  ['Improve', 'Feed wins, replies, costs, and failures back into the operating model.'],
];

const navLinks = [
  ['Platform', '#platform'],
  ['Services', '#services'],
  ['Architecture', '#architecture'],
  ['Team', '#team'],
  ['Contact', '#contact'],
];

function PublicWebsite() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [expanded, setExpanded] = useState(serviceGroups[0].title);
  const [status, setStatus] = useState({ type: '', message: '' });
  const [form, setForm] = useState({
    name: '',
    companyService: '',
    requirement: '',
    phone: '',
    email: '',
    budget: '',
    consultationTime: '',
  });

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    onScroll();
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const activeService = useMemo(
    () => serviceGroups.find((item) => item.title === expanded) || serviceGroups[0],
    [expanded],
  );

  const updateForm = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  const closeMenu = () => setMenuOpen(false);

  async function submitRequest(event) {
    event.preventDefault();
    setStatus({ type: 'loading', message: 'Sending request to Aliyar Solutions...' });

    try {
      const response = await fetch('/api/v1/crm/leads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company: form.companyService,
          company_name: form.companyService,
          contact_name: form.name,
          full_name: form.name,
          phone: form.phone,
          email: form.email,
          service_required: form.companyService,
          opportunity_type: form.companyService,
          notes: [
            `Requirement: ${form.requirement}`,
            form.budget ? `Budget: ${form.budget}` : '',
            form.consultationTime ? `Preferred time: ${form.consultationTime}` : '',
          ].filter(Boolean).join('\n'),
          project_description: form.requirement,
          source: 'aliyarsolutions.com',
        }),
      });

      if (!response.ok) throw new Error('Lead submission failed');

      setStatus({
        type: 'success',
        message: 'Request received. Our team will review it and respond within 24 hours.',
      });
      setForm({
        name: '',
        companyService: '',
        requirement: '',
        phone: '',
        email: '',
        budget: '',
        consultationTime: '',
      });
    } catch (error) {
      setStatus({
        type: 'error',
        message: 'The form could not submit yet. Please email hello@aliyarsolutions.com.',
      });
    }
  }

  return (
    <div className="as-site public-mobile-safe">
      <header className={`as-nav-wrap ${scrolled ? 'is-scrolled' : ''}`}>
        <nav className="as-nav">
          <a className="as-brand" href="#top" aria-label="Aliyar Solutions">
            <span className="as-brand-mark"><Zap size={22} /></span>
            <span>
              <strong>Aliyar Solutions</strong>
              <small>Enterprise Automation Infrastructure</small>
            </span>
          </a>

          <div className="as-nav-links">
            {navLinks.map(([label, href]) => <a key={label} href={href}>{label}</a>)}
          </div>

          <a className="as-nav-cta" href="#contact">Book Strategy Call</a>
          <button className="as-menu-button" onClick={() => setMenuOpen((open) => !open)} aria-label="Toggle menu">
            {menuOpen ? <X size={21} /> : <Menu size={21} />}
          </button>
        </nav>
        {menuOpen && (
          <div className="as-mobile-menu">
            {navLinks.map(([label, href]) => <a key={label} href={href} onClick={closeMenu}>{label}</a>)}
            <a href="#contact" onClick={closeMenu}>Book Strategy Call</a>
          </div>
        )}
      </header>

      <main id="top">
        <section className="as-hero">
          <HeroSystem />
          <div className="as-hero-content" data-aos="fade-up">
            <span className="as-kicker"><Sparkles size={16} /> Enterprise technology operations</span>
            <h1>Aliyar Solutions builds intelligent systems that run business operations at scale.</h1>
            <p>
              Our consulting platform combines workflow modernization, cloud operations, revenue systems,
              and delivery controls to help modern companies move faster with safer execution.
            </p>
            <div className="as-hero-actions">
              <a className="as-button as-primary" href="#platform">Explore Platform <ArrowRight size={18} /></a>
              <a className="as-button as-secondary" href="#contact">Start a Project</a>
            </div>
          </div>
          <div className="as-hero-footer" data-aos="fade-up" data-aos-delay="160">
            {proof.slice(0, 4).map(([value, label]) => (
              <div key={label}>
                <strong>{value}</strong>
                <span>{label}</span>
              </div>
            ))}
          </div>
        </section>

        <section id="platform" className="as-section">
          <SectionHead
            eyebrow="Platform"
            title="A live operating system for revenue, cloud, AI, and execution."
            copy="The public face is simple. Underneath it is a coordinated business engine with approvals, CRM, intelligence, automation, and production safety built into the same workflow."
          />
          <div className="as-platform-grid">
            <PlatformPanel
              icon={Activity}
              label="Operational command"
              title="The operating model watches the business loop."
              text="Leads, proposals, approvals, service health, scheduler jobs, dashboard metrics, and production warnings move through one command center."
            />
            <PlatformPanel
              icon={CircleDollarSign}
              label="Revenue execution"
              title="Discovery to deal flow."
              text="The engine can discover leads, promote contacts, draft outreach, generate proposals, estimate deal value, and queue review packets."
            />
            <PlatformPanel
              icon={LockKeyhole}
              label="Controlled autonomy"
              title="Fast internally, careful externally."
              text="Research, scoring, drafting, diagnostics, and CRM updates can run automatically. Client messages and high-risk actions require approval."
            />
          </div>
        </section>

        <section id="services" className="as-section as-section-tight">
          <SectionHead
            eyebrow="Services"
            title="Enterprise automation services, presented as one intelligent delivery system."
            copy="Aliyar Solutions combines strategy, engineering, workflow systems, cloud infrastructure, and business operations into practical client outcomes."
          />
          <div className="as-service-layout">
            <div className="as-service-list">
              {serviceGroups.map((service, index) => {
                const Icon = service.icon;
                const isOpen = activeService.title === service.title;
                return (
                  <button
                    type="button"
                    className={`as-service-row ${isOpen ? 'active' : ''}`}
                    key={service.title}
                    onClick={() => setExpanded(service.title)}
                    data-aos="fade-up"
                    data-aos-delay={index * 45}
                  >
                    <span className={`as-service-icon ${service.accent}`}><Icon size={20} /></span>
                    <span>
                      <strong>{service.title}</strong>
                      <small>{service.summary}</small>
                    </span>
                    <ChevronDown size={18} className={isOpen ? 'rotate' : ''} />
                  </button>
                );
              })}
            </div>
            <div className={`as-service-detail ${activeService.accent}`} data-aos="fade-up">
              <div className="as-detail-top">
                <span>{activeService.title}</span>
                <activeService.icon size={34} />
              </div>
              <h3>{activeService.summary}</h3>
              <div className="as-chip-grid">
                {activeService.items.map((item) => <span key={item}>{item}</span>)}
              </div>
              <a className="as-inline-link" href="#contact">Discuss this capability <ArrowRight size={16} /></a>
            </div>
          </div>
        </section>

        <section className="as-section">
          <SectionHead
            eyebrow="Technology Stack"
            title="Built on the same stack serious automation companies use to ship production systems."
            copy="The platform is designed around cloud reliability, operational intelligence, secure integrations, and observable runtime behavior."
          />
          <div className="as-stack-cloud" data-aos="fade-up">
            {stack.map((item, index) => <span key={item} style={{ '--delay': `${index * 36}ms` }}>{item}</span>)}
          </div>
        </section>

        <section id="architecture" className="as-section as-architecture-section">
          <SectionHead
            eyebrow="Architecture"
            title="A layered execution architecture for modern operations."
            copy="Aliyar Solutions connects intelligence, revenue, CRM, dashboards, approvals, scheduler jobs, and reliability scanning so companies can operate with discipline."
          />
          <div className="as-architecture">
            <div className="as-architecture-map" data-aos="fade-right">
              <div className="as-core-node">
                <BrainCircuit size={38} />
                <strong>Operations Core</strong>
                <span>Command intelligence</span>
              </div>
              {architecture.map((layer, index) => {
                const Icon = layer.icon;
                return (
                  <div className={`as-orbit-node node-${index + 1}`} key={layer.title}>
                    <Icon size={20} />
                    <span>{layer.title}</span>
                  </div>
                );
              })}
            </div>
            <div className="as-architecture-copy" data-aos="fade-left">
              {architecture.map((layer, index) => {
                const Icon = layer.icon;
                return (
                  <article key={layer.title}>
                    <span><Icon size={18} /> 0{index + 1}</span>
                    <h3>{layer.title}</h3>
                    <p>{layer.text}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section className="as-section">
          <SectionHead
            eyebrow="Client Journey"
            title="A disciplined loop from market discovery to delivery improvement."
            copy="The goal is not noise. It is a controlled operating rhythm that creates opportunities, protects trust, and learns from results."
          />
          <div className="as-journey">
            {journey.map(([title, text], index) => (
              <article key={title} data-aos="fade-up" data-aos-delay={index * 55}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="team" className="as-section">
          <SectionHead
            eyebrow="Operating Team"
            title="Structured like a larger company from day one."
            copy="The website presents a professional delivery organization supported by structured internal intelligence, service routing, and reporting."
          />
          <div className="as-team-grid">
            {departments.map(([name, text], index) => (
              <article key={name} data-aos="fade-up" data-aos-delay={index * 50}>
                <UsersRound size={22} />
                <h3>{name}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="as-section as-trust-section">
          <div className="as-trust" data-aos="fade-up">
            <div>
              <span className="as-eyebrow">Proof of depth</span>
              <h2>Not a small website. A production command system with a premium front door.</h2>
            </div>
            <div className="as-proof-grid">
              {proof.map(([value, label]) => (
                <div key={label}>
                  <strong>{value}</strong>
                  <span>{label}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="contact" className="as-section">
          <SectionHead
            eyebrow="Contact"
            title="Start with a short requirement. We will route it to the right capability."
            copy="No long intake form. Send the essentials and Aliyar Solutions will respond with a clear next step."
          />
          <form className="as-contact" onSubmit={submitRequest} data-aos="fade-up">
            <div className="as-form-grid">
              <Field label="Name">
                <input required value={form.name} onChange={(event) => updateForm('name', event.target.value)} />
              </Field>
              <Field label="Company or service needed">
                <input required value={form.companyService} onChange={(event) => updateForm('companyService', event.target.value)} />
              </Field>
              <Field label="Phone number">
                <input required value={form.phone} onChange={(event) => updateForm('phone', event.target.value)} />
              </Field>
              <Field label="Email optional">
                <input type="email" value={form.email} onChange={(event) => updateForm('email', event.target.value)} />
              </Field>
              <Field label="Budget range optional">
                <select value={form.budget} onChange={(event) => updateForm('budget', event.target.value)}>
                  <option value="">Select if known</option>
                  <option>$500 - $1,500</option>
                  <option>$1,500 - $5,000</option>
                  <option>$5,000 - $15,000</option>
                  <option>$15,000+</option>
                </select>
              </Field>
              <Field label="Preferred consultation time optional">
                <input value={form.consultationTime} onChange={(event) => updateForm('consultationTime', event.target.value)} />
              </Field>
            </div>
            <Field label="Short requirement description">
              <textarea
                required
                rows={5}
                value={form.requirement}
                onChange={(event) => updateForm('requirement', event.target.value)}
                placeholder="Tell us what you want automated, built, deployed, fixed, or improved."
              />
            </Field>
            <button className="as-submit" type="submit">
              Send Requirement <ArrowRight size={18} />
            </button>
            {status.message && <p className={`as-form-status ${status.type}`}>{status.message}</p>}
          </form>
        </section>
      </main>

      <footer className="as-footer">
        <div>
          <a className="as-brand" href="#top" aria-label="Aliyar Solutions footer">
            <span className="as-brand-mark"><Zap size={22} /></span>
            <span>
              <strong>Aliyar Solutions</strong>
              <small>Enterprise automation and cloud operations company</small>
            </span>
          </a>
          <p>Cloud operations, workflow modernization, revenue operations, dashboards, and delivery infrastructure for serious businesses.</p>
        </div>
        <div>
          <strong>Platform</strong>
          {navLinks.map(([label, href]) => <a key={label} href={href}>{label}</a>)}
        </div>
        <div>
          <strong>Contact</strong>
          <a href="mailto:hello@aliyarsolutions.com">hello@aliyarsolutions.com</a>
          <a href="#contact">Book a strategy call</a>
        </div>
      </footer>
    </div>
  );
}

function HeroSystem() {
  const nodes = [
    { label: 'Revenue', icon: CircleDollarSign },
    { label: 'Cloud', icon: ServerCog },
    { label: 'CRM', icon: DatabaseZap },
    { label: 'Voice', icon: Headphones },
    { label: 'Security', icon: ShieldCheck },
    { label: 'Outreach', icon: MailCheck },
    { label: 'Signals', icon: Radar },
    { label: 'Delivery', icon: Rocket },
  ];

  return (
    <div className="as-hero-system" aria-hidden="true">
      <div className="as-system-grid" />
      <div className="as-system-ring ring-one" />
      <div className="as-system-ring ring-two" />
      <div className="as-system-core">
        <Network size={30} />
        <span>OPS</span>
      </div>
      {nodes.map((node, index) => {
        const Icon = node.icon;
        return (
          <div className={`as-system-node system-node-${index + 1}`} key={node.label}>
            <Icon size={16} />
            <span>{node.label}</span>
          </div>
        );
      })}
      <div className="as-signal-line line-a" />
      <div className="as-signal-line line-b" />
      <div className="as-signal-line line-c" />
    </div>
  );
}

function PlatformPanel({ icon: Icon, label, title, text }) {
  return (
    <article className="as-platform-panel" data-aos="fade-up">
      <span><Icon size={22} /></span>
      <small>{label}</small>
      <h3>{title}</h3>
      <p>{text}</p>
    </article>
  );
}

function SectionHead({ eyebrow, title, copy }) {
  return (
    <div className="as-section-head" data-aos="fade-up">
      <span className="as-eyebrow">{eyebrow}</span>
      <h2>{title}</h2>
      {copy && <p>{copy}</p>}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="as-field">
      <span>{label}</span>
      {children}
    </label>
  );
}

const shouldRenderDashboard =
  window.location.pathname.startsWith('/dashboard')
  || window.location.port === '3000';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {shouldRenderDashboard ? <DashboardApp /> : <PublicWebsite />}
  </React.StrictMode>,
);
