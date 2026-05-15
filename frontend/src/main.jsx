import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import DashboardApp from './App.jsx';
import AOS from 'aos';
import 'aos/dist/aos.css';
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  Clock3,
  CloudCog,
  Film,
  Globe2,
  Layers3,
  LockKeyhole,
  Menu,
  Rocket,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  UsersRound,
  Workflow,
  X,
} from 'lucide-react';
import './index.css';
import './styles.css';

const categories = [
  {
    id: 'cloud',
    icon: CloudCog,
    title: 'Cloud & DevOps Infrastructure',
    description: 'Production cloud foundations, delivery pipelines, and reliability systems engineered for serious operations.',
    services: ['AWS Architecture', 'Docker & Containers', 'CI/CD Pipelines', 'Terraform', 'Kubernetes', 'Monitoring'],
    full: 'Our engineers design, build, and stabilize cloud environments that are secure, observable, and ready for real customer demand.',
    deliverables: ['Architecture blueprint and deployment plan', 'Infrastructure setup with monitoring', 'Runbooks and handover documentation'],
    timeline: 'Typical timeline: 3-8 weeks',
  },
  {
    id: 'intelligent',
    icon: Workflow,
    title: 'Intelligent Systems',
    description: 'Smart operating systems that reduce manual friction and help teams execute with consistency.',
    services: ['Workflow Systems', 'Smart Business Systems', 'Process Integration', 'Executive Operations'],
    full: 'Our specialists map your operations, remove weak handoffs, and implement intelligent systems that streamline daily work.',
    deliverables: ['Workflow audit and implementation map', 'Integrated tools and handoff logic', 'Training notes for your team'],
    timeline: 'Typical timeline: 2-6 weeks',
  },
  {
    id: 'revenue',
    icon: TrendingUp,
    title: 'Sales & Revenue Systems',
    description: 'Revenue infrastructure for prospecting, outreach, CRM visibility, and reliable follow-up discipline.',
    services: ['Lead Generation Systems', 'Outreach Systems', 'CRM Architecture', 'Sales Operations'],
    full: 'Our experts build the systems behind predictable growth, from clean pipelines to executive reporting and response workflows.',
    deliverables: ['CRM structure and pipeline stages', 'Qualified opportunity workflow', 'Revenue dashboard and reporting'],
    timeline: 'Typical timeline: 2-5 weeks',
  },
  {
    id: 'security',
    icon: LockKeyhole,
    title: 'Cybersecurity & Compliance',
    description: 'Security hardening, vulnerability reviews, and operational controls for cloud and application environments.',
    services: ['Security Operations', 'Vulnerability Assessment', 'Compliance Hardening', 'Infrastructure Hardening'],
    full: 'Our security consultants review your risk surface, strengthen controls, and give leadership a clear remediation plan.',
    deliverables: ['Risk-ranked findings report', 'Access and infrastructure hardening', 'Executive remediation roadmap'],
    timeline: 'Typical timeline: 1-4 weeks',
  },
  {
    id: 'products',
    icon: Layers3,
    title: 'Digital Products & Platforms',
    description: 'Premium websites, portals, dashboards, and SaaS platforms built for real business use.',
    services: ['Web Applications', 'Client Portals', 'Operational Dashboards', 'SaaS Platforms'],
    full: 'Our engineers ship polished digital products with performance, responsive design, clean data flows, and launch readiness.',
    deliverables: ['Product design and frontend build', 'Backend integration and deployment', 'Launch checklist and support notes'],
    timeline: 'Typical timeline: 3-8 weeks',
  },
  {
    id: 'media',
    icon: Film,
    title: 'Content & Media Operations',
    description: 'Content systems, design production, video workflows, and social operations for consistent brand output.',
    services: ['Content Systems', 'Social Media Operations', 'Video Production', 'Graphic Design'],
    full: 'Our team builds repeatable media operations so your brand can publish with quality, speed, and professional consistency.',
    deliverables: ['Content calendar and production workflow', 'Creative templates and brand assets', 'Publishing and reporting process'],
    timeline: 'Typical timeline: 1-4 weeks',
  },
  {
    id: 'intelligence',
    icon: BarChart3,
    title: 'Business Intelligence',
    description: 'Analytics systems, KPI dashboards, research, and decision support for leadership teams.',
    services: ['Analytics Systems', 'KPI Dashboards', 'Market Research', 'Competitive Analysis'],
    full: 'Our analysts and engineers turn scattered business data into dashboards, reports, and insights leaders can trust.',
    deliverables: ['KPI model and data structure', 'Executive dashboards and reports', 'Research summary with recommendations'],
    timeline: 'Typical timeline: 2-6 weeks',
  },
];

const stats = ['30+ Services', 'Global Clients', '24/7 Operations', 'Enterprise Grade'];

const steps = [
  ['Submit Your Request', 'Fill our project form'],
  ['Strategy Call', 'Our team reviews and proposes solution'],
  ['We Build & Deliver', 'Full execution by our specialists'],
  ['You Scale', 'Ongoing support and optimization'],
];

const team = [
  ['Darren Mitchell', 'Client Acquisition Specialist', 'Growth strategy and qualified project intake'],
  ['David Carter', 'Solutions Architect', 'Cloud architecture and technical planning'],
  ['Sophia Reynolds', 'Workflow Consultant', 'Operational design and process improvement'],
  ['Nathan Scott', 'Deployment Engineer', 'Production launches and infrastructure delivery'],
  ['Emma Collins', 'Business Optimisation Specialist', 'Efficiency reviews and execution planning'],
  ['Daniel Brooks', 'Security Consultant', 'Risk assessment and infrastructure hardening'],
  ['Michael Hayes', 'Infrastructure Strategist', 'Scale planning and reliability systems'],
  ['Lucas Reed', 'Process Integration Specialist', 'Tooling, data flows, and handoff systems'],
  ['Olivia Bennett', 'Account Coordinator', 'Client communication and delivery coordination'],
];

const hearOptions = ['Google', 'LinkedIn', 'Referral', 'Social Media', 'Other'];

function PublicWebsite() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [expanded, setExpanded] = useState(categories[0].id);
  const [status, setStatus] = useState({ type: '', message: '' });
  const [form, setForm] = useState({
    fullName: '',
    company: '',
    email: '',
    phone: '',
    service: '',
    consultation: 'Yes',
    heard: 'Google',
    description: '',
  });

  useEffect(() => {
    AOS.init({ once: true, duration: 720, easing: 'ease-out-cubic', offset: 90 });
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const activeCategory = useMemo(
    () => categories.find((category) => category.id === expanded) || categories[0],
    [expanded],
  );

  const updateForm = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const scrollToBooking = () => {
    setMenuOpen(false);
    document.getElementById('booking')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  async function submitRequest(event) {
    event.preventDefault();
    setStatus({ type: 'loading', message: 'Submitting your request...' });

    try {
      const response = await fetch('/api/v1/crm/leads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company: form.company || form.fullName,
          contact_name: form.fullName,
          full_name: form.fullName,
          company_name: form.company,
          email: form.email,
          phone: form.phone,
          service_required: form.service,
          opportunity_type: form.service,
          consultation_call: form.consultation === 'Yes',
          referral_source: form.heard,
          notes: `Consultation: ${form.consultation}. Heard about us: ${form.heard}. Project: ${form.description}`,
          project_description: form.description,
          source: 'aliyarsolutions.com',
        }),
      });

      if (!response.ok) {
        throw new Error('Request failed');
      }

      setStatus({
        type: 'success',
        message: 'Request received. Our team contacts you within 24 hours.',
      });
      setForm((current) => ({ ...current, fullName: '', company: '', email: '', phone: '', description: '' }));
    } catch (error) {
      setStatus({
        type: 'error',
        message: 'We could not submit the request yet. Please email hello@aliyarsolutions.com.',
      });
    }
  }

  return (
    <div className="site-shell public-mobile-safe">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <div className="announcement">
        🔥 Limited Time — 30% OFF all services until 21st May 2026 — Book now to lock in your rate
      </div>

      <header className={`nav-wrap ${scrolled ? 'is-scrolled' : ''}`}>
        <nav className="nav">
          <a className="brand" href="#top" aria-label="Aliyar Solutions home">
            <span className="brand-mark">AS</span>
            <span>Aliyar Solutions</span>
          </a>

          <div className="nav-links">
            <a href="#services">Services</a>
            <a href="#process">How It Works</a>
            <a href="#team">Our Team</a>
            <a href="#booking">Contact</a>
          </div>

          <button className="nav-cta" onClick={scrollToBooking}>Book a Consultation</button>
          <button className="menu-button" onClick={() => setMenuOpen((open) => !open)} aria-label="Toggle menu">
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </nav>

        {menuOpen && (
          <div className="mobile-menu">
            <a onClick={() => setMenuOpen(false)} href="#services">Services</a>
            <a onClick={() => setMenuOpen(false)} href="#process">How It Works</a>
            <a onClick={() => setMenuOpen(false)} href="#team">Our Team</a>
            <a onClick={() => setMenuOpen(false)} href="#booking">Contact</a>
            <button onClick={scrollToBooking}>Book a Consultation</button>
          </div>
        )}
      </header>

      <main id="top">
        <section className="hero section-pad">
          <div className="hero-grid" data-aos="fade-up">
            <div className="hero-kicker">
              <Sparkles size={16} />
              Premium delivery partner for modern companies
            </div>
            <h1>Enterprise Technology<br />Delivered by Experts</h1>
            <p>
              Aliyar Solutions partners with businesses worldwide to build cloud infrastructure,
              intelligent systems, and operational technology that scales.
            </p>
            <div className="hero-actions">
              <a className="button primary" href="#services">Explore Our Services <ArrowRight size={18} /></a>
              <button className="button secondary" onClick={scrollToBooking}>Talk to Our Team</button>
            </div>
          </div>

          <div className="stat-grid" data-aos="fade-up" data-aos-delay="140">
            {stats.map((stat) => (
              <div className="stat-card" key={stat}>{stat}</div>
            ))}
          </div>
        </section>

        <section id="services" className="section section-pad">
          <div className="section-head" data-aos="fade-up">
            <span>Services</span>
            <h2>What We Deliver</h2>
            <p>End-to-end technology solutions for every operational need</p>
          </div>

          <div className="service-grid">
            {categories.map((category, index) => {
              const Icon = category.icon;
              const isOpen = expanded === category.id;
              return (
                <article
                  className={`service-card ${isOpen ? 'active' : ''}`}
                  key={category.id}
                  onClick={() => setExpanded(isOpen ? '' : category.id)}
                  data-aos="fade-up"
                  data-aos-delay={index * 45}
                >
                  <div className="service-top">
                    <div className="icon-box"><Icon size={23} /></div>
                    <ChevronDown className={isOpen ? 'rotate' : ''} size={19} />
                  </div>
                  <h3>{category.title}</h3>
                  <p>{category.description}</p>
                  <ul>
                    {category.services.slice(0, 4).map((service) => (
                      <li key={service}><CheckCircle2 size={14} />{service}</li>
                    ))}
                  </ul>
                  <div className="service-actions">
                    <span className="learn">Learn More <ArrowRight size={15} /></span>
                    <button type="button" onClick={(event) => { event.stopPropagation(); scrollToBooking(); }}>Book</button>
                  </div>
                </article>
              );
            })}
          </div>

          <div className="service-detail" data-aos="fade-up">
            <div>
              <span className="detail-label">Expanded service</span>
              <h3>{activeCategory.title}</h3>
              <p>{activeCategory.full}</p>
            </div>
            <div className="detail-list">
              <strong>Key deliverables</strong>
              {activeCategory.deliverables.map((item) => (
                <span key={item}><CheckCircle2 size={15} />{item}</span>
              ))}
            </div>
            <div className="detail-side">
              <span>{activeCategory.timeline}</span>
              <button className="button primary compact" onClick={scrollToBooking}>Book This Service</button>
            </div>
          </div>
        </section>

        <section id="process" className="section section-pad">
          <div className="section-head" data-aos="fade-up">
            <span>Process</span>
            <h2>How It Works</h2>
            <p>Clear steps, senior ownership, and professional execution from day one.</p>
          </div>
          <div className="timeline">
            {steps.map(([title, copy], index) => (
              <div className="step-card" key={title} data-aos="fade-up" data-aos-delay={index * 80}>
                <span className="step-number">0{index + 1}</span>
                <h3>{title}</h3>
                <p>{copy}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="team" className="section section-pad">
          <div className="section-head" data-aos="fade-up">
            <span>Our Team</span>
            <h2>The Team Behind Your Success</h2>
            <p>Dedicated professionals across strategy, engineering, security, and client delivery.</p>
          </div>
          <div className="team-grid">
            {team.map(([name, role, specialty], index) => (
              <article className="team-card" key={name} data-aos="fade-up" data-aos-delay={index * 40}>
                <div className="avatar">{name.split(' ').map((part) => part[0]).join('')}</div>
                <h3>{name}</h3>
                <span>{role}</span>
                <p>{specialty}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="section section-pad">
          <div className="section-head" data-aos="fade-up">
            <span>Value</span>
            <h2>Technology That Pays For Itself</h2>
          </div>
          <div className="value-cta" data-aos="fade-up">
            <strong>Technology That Pays For Itself</strong>
            <p>
              Poor technology costs more than good technology. Every system failure, every security breach,
              every missed workflow is money leaving your business. Aliyar Solutions delivers enterprise-grade
              technology at a price that protects both your reputation and your bottom line — because we believe
              no business should lose to a problem that has a solution.
            </p>
            <button className="button primary" onClick={scrollToBooking}>
              Get a Free Consultation — No Commitment Required <ArrowRight size={18} />
            </button>
          </div>
        </section>

        <section id="booking" className="section section-pad">
          <div className="section-head" data-aos="fade-up">
            <span>Contact</span>
            <h2>Start Your Project</h2>
            <p>Fill in your details and our team will reach out within 24 hours</p>
          </div>

          <form className="booking-card" onSubmit={submitRequest} data-aos="fade-up">
            <div className="form-grid">
              <Field label="Full Name *">
                <input required value={form.fullName} onChange={(event) => updateForm('fullName', event.target.value)} />
              </Field>
              <Field label="Company Name">
                <input value={form.company} onChange={(event) => updateForm('company', event.target.value)} />
              </Field>
              <Field label="Email Address *">
                <input required type="email" value={form.email} onChange={(event) => updateForm('email', event.target.value)} />
              </Field>
              <Field label="Phone Number (optional)">
                <input value={form.phone} onChange={(event) => updateForm('phone', event.target.value)} />
              </Field>
              <Field label="Service Required *">
                <select required value={form.service} onChange={(event) => updateForm('service', event.target.value)}>
                  <option value="" disabled>Select a service category</option>
                  {categories.map((category) => <option key={category.id}>{category.title}</option>)}
                </select>
              </Field>
            </div>

            <div className="toggle-row">
              <div>
                <span>Do you need a consultation call first?</span>
                <div className="toggle-group">
                  {['Yes', 'No'].map((option) => (
                    <button
                      type="button"
                      className={form.consultation === option ? 'selected' : ''}
                      onClick={() => updateForm('consultation', option)}
                      key={option}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </div>
              <Field label="How did you hear about us?">
                <select value={form.heard} onChange={(event) => updateForm('heard', event.target.value)}>
                  {hearOptions.map((option) => <option key={option}>{option}</option>)}
                </select>
              </Field>
            </div>

            <Field label="Project Description *">
              <textarea
                required
                rows={4}
                placeholder="Tell us about your project, goals, and timeline..."
                value={form.description}
                onChange={(event) => updateForm('description', event.target.value)}
              />
            </Field>

            <button className="submit-button" type="submit">
              Submit Request — We'll Reach Out Within 24 Hours <ArrowRight size={18} />
            </button>
            {status.message && <p className={`form-status ${status.type}`}>{status.message}</p>}
          </form>
        </section>
      </main>

      <footer className="footer">
        <div className="footer-grid">
          <div>
            <h3>Aliyar Solutions</h3>
            <p>Enterprise technology delivered by experts.</p>
            <a href="mailto:hello@aliyarsolutions.com">hello@aliyarsolutions.com</a>
          </div>
          <div>
            <h4>Services</h4>
            {categories.map((category) => <a href="#services" key={category.id}>{category.title}</a>)}
          </div>
          <div>
            <h4>Company</h4>
            <a href="#team">About</a>
            <a href="#booking">Contact</a>
            <a href="#booking">Book Consultation</a>
          </div>
        </div>
        <div className="footer-bottom">
          © 2026 Aliyar Solutions. All rights reserved. Enterprise Technology Company.
        </div>
      </footer>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {window.location.port === '3000' || window.location.pathname.startsWith('/dashboard') ? (
      <DashboardApp />
    ) : (
      <PublicWebsite />
    )}
  </React.StrictMode>,
);
