# JARVIS API INVENTORY
_All routes registered in backend/app/api/v1/__init__.py_
_Base URL: https://api.aliyarsolutions.com/api/v1 (production) | http://localhost:8000/api/v1 (local)_

## Authentication
- POST /auth/login → returns JWT token (role: captain)
- GET  /auth/me → current user
- Captain credentials: CAPTAIN_USERNAME / CAPTAIN_PASSWORD (in .env)

## Core Operations
| Module | Prefix | Key Endpoints |
|--------|--------|---------------|
| Chat | /chat | POST / (60/min rate limited) |
| Briefing | /briefing | GET /morning-ai, POST /generate |
| Council | /council | POST /convene (20/min), GET /sessions |
| Captain | /captain | All routes JWT-locked at router level |
| System | /system | GET /hud, POST /self-heal (JWT required) |
| WebSocket | /ws | /ws (public), /ws/captain (JWT required) |

## CRM & Sales
| Module | Prefix | Key Endpoints |
|--------|--------|---------------|
| Leads | /leads | CRUD + scoring + pipeline |
| CRM | /crm | Companies, Contacts, Deals |
| Discovery | /discovery | POST /run, POST /free-sources |
| Outreach | /outreach | POST /execute (10/min), /sequences, /enroll |
| Sync | /sync | POST /apollo (5/min) |
| Demos | /demos | POST /generate (+ prospect_email auto-emails) |
| Trust | /trust | POST /briefs/generate, POST /engagement, GET /score/{lead_id}, POST /referrals/generate |

## Governance & Revenue
| Module | Prefix | Key Endpoints |
|--------|--------|---------------|
| Governance | /governance | Invoices, Proposals, Contracts, Permissions |
| Proposals | /proposals | POST /generate (30/min) |
| Invoices | /invoices | CRUD |
| Revenue | /revenue | GET /clients, /mrr, /pipeline |
| Clients | /clients | CRUD + auto welcome email |
| Payments | /payments | Stripe links, webhooks, bank/Wise |
| Pricing | /pricing | Service pricing matrix |

## AI & Intelligence
| Module | Prefix | Key Endpoints |
|--------|--------|---------------|
| AI Ops | /ai | GET /health, provider status |
| Intelligence | /intelligence | Tech radar, optimizer, research |
| AIONx | /aionx | Self-heal, frontier, cascade, threats |
| Memory | /memory | Operational + strategic memory |
| Knowledge | /knowledge | SOPs, learnings, KB |
| Departments | /departments | Department intelligence officers |
| Council | /council | Multi-model debate sessions |

## Infrastructure & Ops
| Module | Prefix | Key Endpoints |
|--------|--------|---------------|
| Scheduler | /scheduler | Cron/interval/oneshot jobs (JWT) |
| Approvals | /approvals | Captain approval queue (JWT) |
| Emergency | /emergency | Incidents, alerts (JWT) |
| Notifications | /notifications | History, channels |
| Agents | /agents | Agent registry, task queue |

## AI Providers Configured
| Provider | Key Env Var | Status |
|----------|-------------|--------|
| Anthropic (Claude) | ANTHROPIC_API_KEY | Primary |
| OpenAI (GPT) | OPENAI_API_KEY | Configured |
| Google (Gemini) | GOOGLE_API_KEY | Configured |
| DeepSeek | DEEPSEEK_API_KEY | Configured |
| Groq | GROQ_API_KEY | Configured |
| AWS Bedrock | USE_AWS + AWS creds | Configured |
| NVIDIA | NVIDIA_API_KEY | Configured |
| Mistral | MISTRAL_API_KEY | Configured |
| Moonshot | MOONSHOT_API_KEY | Configured |
| ZhipuAI | ZHIPUAI_API_KEY | Configured |
| MiniMax | MINIMAX_API_KEY | Configured |

## Task Routing (ai/router.py)
- CODE → claude-sonnet → deepseek → gpt-4o
- REASONING → claude-opus → gpt-4o → gemini-pro
- STRATEGY → claude-opus → gpt-4o → claude-sonnet
- RESEARCH → gemini-pro → gpt-4o → claude-sonnet
- FAST → deepseek-flash → llama-3-3 → gpt-4o-mini
