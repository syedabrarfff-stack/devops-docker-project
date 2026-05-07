const CONNECTORS = [
  // Design & Creative
  { id: 'adobe', name: 'Adobe Creative', icon: '🎨', category: 'creative', tools: 57, status: 'connected', color: '#ff0000' },
  { id: 'canva', name: 'Canva', icon: '🖼️', category: 'creative', tools: 32, status: 'connected', color: '#00c4cc' },
  { id: 'figma', name: 'Figma', icon: '🎭', category: 'creative', tools: 18, status: 'connected', color: '#a259ff' },
  { id: 'gamma', name: 'Gamma', icon: '📊', category: 'creative', tools: 7, status: 'connected', color: '#6366f1' },
  { id: 'lucid', name: 'Lucid', icon: '📐', category: 'creative', tools: 15, status: 'connected', color: '#f97316' },

  // Project Management
  { id: 'clickup', name: 'ClickUp', icon: '✅', category: 'productivity', tools: 51, status: 'connected', color: '#7b68ee' },
  { id: 'notion', name: 'Notion', icon: '📝', category: 'productivity', tools: 14, status: 'connected', color: '#ffffff' },
  { id: 'todoist', name: 'Todoist', icon: '📋', category: 'productivity', tools: 45, status: 'connected', color: '#db4035' },
  { id: 'airtable', name: 'Airtable', icon: '🗂️', category: 'productivity', tools: 21, status: 'connected', color: '#fcb400' },

  // Communication
  { id: 'slack', name: 'Slack', icon: '💬', category: 'communication', tools: 13, status: 'connected', color: '#4a154b' },
  { id: 'gmail', name: 'Gmail', icon: '📧', category: 'communication', tools: 6, status: 'connected', color: '#ea4335' },

  // Calendar & Scheduling
  { id: 'google-calendar', name: 'Google Calendar', icon: '📅', category: 'calendar', tools: 8, status: 'connected', color: '#4285f4' },
  { id: 'granola', name: 'Granola', icon: '🎙️', category: 'calendar', tools: 6, status: 'connected', color: '#10b981' },

  // Storage
  { id: 'google-drive', name: 'Google Drive', icon: '💾', category: 'storage', tools: 8, status: 'connected', color: '#fbbc05' },

  // CRM & Sales
  { id: 'hubspot', name: 'HubSpot', icon: '🔶', category: 'crm', tools: 13, status: 'connected', color: '#ff7a59' },
  { id: 'apollo', name: 'Apollo.io', icon: '🎯', category: 'crm', tools: 18, status: 'connected', color: '#f59e0b' },
  { id: 'close', name: 'Close CRM', icon: '🔐', category: 'crm', tools: 34, status: 'connected', color: '#4f46e5' },

  // Marketing
  { id: 'klaviyo', name: 'Klaviyo', icon: '📣', category: 'marketing', tools: 32, status: 'connected', color: '#000000' },

  // Analytics
  { id: 'posthog', name: 'PostHog', icon: '📈', category: 'analytics', tools: 302, status: 'connected', color: '#f54e00' },

  // E-Commerce
  { id: 'shopify', name: 'Shopify', icon: '🛍️', category: 'ecommerce', tools: 25, status: 'connected', color: '#96bf48' },
  { id: 'stripe', name: 'Stripe', icon: '💳', category: 'payments', tools: 31, status: 'connected', color: '#635bff' },
  { id: 'zoho-books', name: 'Zoho Books', icon: '📚', category: 'finance', tools: 60, status: 'connected', color: '#e60000' },

  // Content & CMS
  { id: 'sanity', name: 'Sanity', icon: '🔷', category: 'cms', tools: 34, status: 'connected', color: '#f03e2f' },
  { id: 'wix', name: 'Wix', icon: '🌐', category: 'cms', tools: 18, status: 'connected', color: '#faad4d' },

  // Forms & Surveys
  { id: 'jotform', name: 'Jotform', icon: '📝', category: 'forms', tools: 9, status: 'connected', color: '#ff6100' },
  { id: 'surveymonkey', name: 'SurveyMonkey', icon: '📊', category: 'forms', tools: 19, status: 'connected', color: '#00bf6f' },

  // Dev & Tech
  { id: 'atlassian', name: 'Atlassian Rovo', icon: '🔧', category: 'devops', tools: 37, status: 'connected', color: '#0052cc' },
  { id: 'aws', name: 'AWS Marketplace', icon: '☁️', category: 'devops', tools: 5, status: 'connected', color: '#ff9900' },
  { id: 'ms-learn', name: 'Microsoft Learn', icon: '📘', category: 'devops', tools: 3, status: 'connected', color: '#00a4ef' },

  // Communication/SMS
  { id: 'twilio', name: 'Twilio', icon: '📱', category: 'communication', tools: 2, status: 'connected', color: '#f22f46' },

  // Food & Delivery
  { id: 'uber-eats', name: 'Uber Eats', icon: '🍔', category: 'misc', tools: 2, status: 'connected', color: '#06c167' },

  // Misc / Not Connected
  { id: 'dice', name: 'Dice', icon: '🎲', category: 'misc', tools: 1, status: 'connected', color: '#ff4444' },
  { id: 'airops', name: 'AirOps', icon: '✈️', category: 'ai', tools: 0, status: 'disconnected', color: '#94a3b8' },
  { id: 'box', name: 'Box', icon: '📦', category: 'storage', tools: 0, status: 'disconnected', color: '#0061d5' },
  { id: 'coindesk', name: 'CoinDesk', icon: '₿', category: 'finance', tools: 0, status: 'disconnected', color: '#f7931a' },
  { id: 'linear', name: 'Linear', icon: '📐', category: 'productivity', tools: 0, status: 'disconnected', color: '#5e6ad2' },
];

const AGENT_TEAMS = [
  {
    id: 'executive',
    name: 'JARVIS Commander',
    role: 'Executive AI',
    agents: 1,
    status: 'active',
    icon: '👑',
    color: '#fbbf24',
    tasks: 0,
    model: 'claude-opus',
    description: 'Orchestrates all agent teams, routes tasks, monitors system'
  },
  {
    id: 'sales',
    name: 'Sales Team',
    role: 'Revenue Generation',
    agents: 5,
    status: 'active',
    icon: '💼',
    color: '#10b981',
    tasks: 0,
    model: 'gpt-4o',
    description: 'Outreach, demos, closing, follow-up, pricing'
  },
  {
    id: 'marketing',
    name: 'Marketing Team',
    role: 'Growth & Campaigns',
    agents: 4,
    status: 'active',
    icon: '📣',
    color: '#f59e0b',
    tasks: 0,
    model: 'claude-sonnet',
    description: 'Content, email campaigns, social analytics, SEO'
  },
  {
    id: 'youtube',
    name: 'YouTube Agent',
    role: 'Video Content',
    agents: 1,
    status: 'active',
    icon: '📺',
    color: '#ef4444',
    tasks: 0,
    model: 'gemini-pro',
    description: 'Script writing, thumbnails, upload, SEO optimization'
  },
  {
    id: 'social',
    name: 'Social Media Team',
    role: 'Social Presence',
    agents: 3,
    status: 'active',
    icon: '📱',
    color: '#8b5cf6',
    tasks: 0,
    model: 'gpt-4o',
    description: 'Instagram, YouTube, TikTok, Facebook, LinkedIn'
  },
  {
    id: 'hr',
    name: 'HR & Hiring',
    role: 'Team Building',
    agents: 3,
    status: 'idle',
    icon: '👥',
    color: '#06b6d4',
    tasks: 0,
    model: 'claude-sonnet',
    description: 'Job posts, screening, interviews, onboarding'
  },
  {
    id: 'cybersecurity',
    name: 'Cybersecurity',
    role: 'System Protection',
    agents: 2,
    status: 'active',
    icon: '🛡️',
    color: '#64748b',
    tasks: 0,
    model: 'deepseek-v4-pro',
    description: 'Threat monitoring, vulnerability scanning, incident response'
  },
  {
    id: 'finance',
    name: 'Finance & Accounting',
    role: 'Financial Management',
    agents: 3,
    status: 'idle',
    icon: '💰',
    color: '#84cc16',
    tasks: 0,
    model: 'claude-sonnet',
    description: 'Invoicing, bookkeeping, reporting, tax prep'
  },
  {
    id: 'content',
    name: 'Content Creation',
    role: 'Content Factory',
    agents: 3,
    status: 'active',
    icon: '✍️',
    color: '#f97316',
    tasks: 0,
    model: 'claude-opus',
    description: 'Blog posts, copy, scripts, email templates'
  },
  {
    id: 'devops',
    name: 'DevOps & Tech',
    role: 'Infrastructure',
    agents: 2,
    status: 'active',
    icon: '⚙️',
    color: '#3b82f6',
    tasks: 0,
    model: 'deepseek-v3',
    description: 'CI/CD, deployments, monitoring, AWS infrastructure'
  },
  {
    id: 'support',
    name: 'Customer Support',
    role: 'Client Success',
    agents: 3,
    status: 'active',
    icon: '🎧',
    color: '#ec4899',
    tasks: 0,
    model: 'gpt-4o-mini',
    description: 'Ticket handling, chat support, escalation, feedback'
  },
  {
    id: 'research',
    name: 'Research & Analytics',
    role: 'Intelligence',
    agents: 2,
    status: 'idle',
    icon: '🔭',
    color: '#a78bfa',
    tasks: 0,
    model: 'gemini-pro',
    description: 'Market research, competitor analysis, trend reports'
  },
];

module.exports = { CONNECTORS, AGENT_TEAMS };
