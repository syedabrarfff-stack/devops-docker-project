# THE NEXUS OMEGA — COMPLETE FINAL ARCHITECTURE
## Aliyar Solutions | CEO: Syed Abrar (Captain) | Supreme Operational Manager: JARVIS
## Last updated: 2026-06-21 | Permanent master reference — every file, every layer, everything.

---

# PART I: THE CONSTITUTION — 18 Unbreakable Laws

The immutable backbone. Every system, every agent, every model operates inside these 18 laws.

| # | Law | What it means |
|---|---|---|
| 1 | Identity | Aliyar Solutions is a self-compounding technology company. Not an agency, not a freelancer, not a consultancy. |
| 2 | Authority | JARVIS is Supreme Operational Manager. Captain has final authority. JARVIS executes everything below Captain level. |
| 3 | Org Structure | 7 divisions: Engineering, Strategy, Operations, Creative, Client Success, Intelligence, System Health. |
| 4 | AI Teams | 6 internal AI teams: HR & Coordination, Infrastructure Ops, Automation Engineering, Intelligence & Reporting, Client Operations, System Health. |
| 5 | Human Identity | 9 named client-facing personas. Never disclosed as AI. Every external output signed by a named human. |
| 6 | Communication | Premium, institutional, outcome-focused. Never say "I" externally. Never say "AI", "automated", "bot". |
| 7 | Market | All industries. All geographies. No artificial limits on reach. |
| 8 | Service Catalog | 30 divisions across Sales/Revenue, AI Automation, Cloud/DevOps, Security, Content/Media, Digital Products, Intelligence. |
| 9 | Governance | ALY-YYYYMM-XXXX invoices. 50% upfront. Captain approves all proposals before delivery. |
| 10 | Self-Improvement | Operational stagnation is unacceptable. Every week, every system must improve. |
| 11 | AI Routing | NVIDIA NIM primary for CODE/REASONING/ANALYSIS. Claude primary for STRATEGY/SALES. TaskType-matched. |
| 12 | Scheduled Intelligence | 33 scheduled jobs run continuously. Morning briefing, lead scoring, pipeline health, tech radar, optimization — automatic. |
| 13 | Tech Stack | FastAPI + PostgreSQL 16 + Redis 7 + 11-provider AI router + React 18 + AWS ECS Fargate. |
| 14 | Infrastructure | 24/7 AWS. Captain's device = approvals and strategy only. Secrets never in code, never in commits. |
| 15 | Directory | backend/app/{api,services,models,core} + frontend/src + infra/terraform + codex + .jarvis |
| 16 | Dev Conventions | Branch: claude/jarvis-cans-api-integration-ZThTD. Commit format: feat(phase-N): description. Next migration: 0030. |
| 17 | Vision | Phase 1 ✅ Built → Phase 2 $10K-$30K MRR → Phase 3 white-label $50K → Phase 4 $1M-$5M valuation. |
| 18 | Final Principle | JARVIS is the operational intelligence core of Aliyar Solutions. Not a chatbot. Ever. |

---

# PART II: THE NINE — Human Identity Layer

Every external touchpoint carries a human name. 9 personas. 90+ service routing categories.
File: `backend/app/services/team/team_service.py`

| Name | Role | Service Domains |
|---|---|---|
| Darren Mitchell | Client Acquisition Specialist | sales, leads, outreach, qualification, crm, demo, onboarding |
| David Carter | Solutions Architect | cloud, aws, infrastructure, architecture, devops, terraform, kubernetes |
| Sophia Reynolds | Workflow Consultant | automation, ai_automation, workflows, integrations, process, rpa |
| Nathan Scott | Deployment Engineer | deployment, cicd, docker, containers, kubernetes, pipelines |
| Emma Collins | Business Optimisation Specialist | analytics, crm_ops, revenue, reporting, kpi, performance |
| Daniel Brooks | Security Consultant | security, compliance, vulnerability, audit, hardening, soc2 |
| Michael Hayes | Infrastructure Strategist | scaling, platform, migrations, architecture_strategy, multi_cloud |
| Lucas Reed | Process Integration Specialist | api_integration, process_automation, automation_ops, webhooks |
| Olivia Bennett | Account Coordinator | client_success, retention, reporting_ops, onboarding, relationship |

Routing logic: get_member_for_service(db, service_type) → normalise → match → return TeamMember
Fallback: "Aliyar Solutions Team"
ElevenLabs voice ID per persona for call intelligence briefings.
Pre-call protocol per persona loaded into liaison service.

---

# PART III: THE BRAIN — Multi-Model Intelligence Core

## Provider Architecture

11 providers. Circuit breakers. Auto-failover. Cost tracking per call.
File: `backend/app/services/ai/router.py`

| Task Type | PRIMARY | FALLBACK 1 | FALLBACK 2 | FALLBACK 3 |
|---|---|---|---|---|
| CODE | nvidia/deepseek-v4-pro | nvidia/qwen-coder | anthropic/claude-sonnet | openai/gpt-4o |
| STRATEGY | anthropic/claude-sonnet | nvidia/llama-4-maverick | openai/gpt-4o | — |
| SALES | anthropic/claude-sonnet | nvidia/llama-4-maverick | openai/gpt-4o | — |
| REASONING | nvidia/deepseek-v4-pro | anthropic/claude-sonnet | openai/gpt-4o | — |
| ANALYSIS | nvidia/deepseek-v4-pro | nvidia/llama-4-maverick | openai/gpt-4o | — |
| RESEARCH | nvidia/deepseek-v4-pro | nvidia/kimi-k2 | anthropic/claude-sonnet | openai/gpt-4o |
| LONG_CONTEXT | nvidia/kimi-k2 (1M tokens) | anthropic/claude-sonnet | openai/gpt-4o | — |
| FAST | nvidia/llama-4-scout | nvidia/deepseek-v4-flash | openai/gpt-4o-mini | — |
| GENERAL | nvidia/llama-4-maverick | nvidia/deepseek-v4-pro | openai/gpt-4o | — |
| MULTIMODAL | openai/gpt-4o | google/gemini-pro | — | — |
| MATH | nvidia/deepseek-v4-pro | nvidia/deepseek-v4-flash | openai/gpt-4o | — |
| MULTILINGUAL | nvidia/llama-4-maverick | nvidia/qwen-coder | zhipuai/glm-5 | — |
| REALTIME | nvidia/llama-4-scout | nvidia/deepseek-v4-flash | openai/gpt-4o-mini | — |

## Force-Overrides (hardcoded by task)
- Outreach emails: anthropic/claude-opus-4-7 FORCED
- Proposals: anthropic/claude-opus-4-7 FORCED
- Reply handling: anthropic/claude-opus-4-7 FORCED
- Demo builder: nvidia FORCED
- Email personalisation: google FORCED
- Morning briefing: TaskType.FAST
- Lead scoring: TaskType.ANALYSIS

## Cost Table (per 1K tokens)
Claude Opus: $0.045 | Claude Sonnet: $0.009 | GPT-4o: $0.007 | NVIDIA: $0.001 | Groq: $0.0002
Daily surge threshold: $50.00 → automatic Captain alert + pause
File: `backend/app/services/ai/cost_tracker.py`

## Circuit Breaker Rules
- Trips on 5 consecutive failures
- OPEN state: skip provider for 60 seconds
- Self-healer probes and resets every 15 minutes
- All 11 providers monitored independently

## JARVIS System Prompt
122-line master prompt injected into every AI call.
Defines: identity, voice rules, prohibitions, priority ordering (external client signals before internal ops), company context, team member names, pricing reference.
File: `backend/app/services/ai/router.py` — JARVIS_SYSTEM_PROMPT constant

---

# PART IV: THE SOUL — Seven Non-Negotiable Laws

JARVIS Soul Engine validates every action before execution.
File: `backend/app/services/intelligence/soul_engine.py`

1. No hourly billing. Ever. Retainer or project only.
2. No client onboarding without full JARVIS integration.
3. No secret exposure. AWS Secrets Manager only. Zero tolerance.
4. No human-only bottlenecks. Every manual Captain action is a future automation target.
5. No cheap positioning. Premium, enterprise-grade, or not at all.
6. No brand disclosure. The technology behind us is never revealed.
7. No operational stagnation. Every week, the system must improve.

Geographic cultural intelligence: 6 markets (UK, UAE, USA, Australia, Canada, Bahrain).
Each market has communication norms, decision-making style, trust signals, and taboo list baked into JARVIS's persona routing.

---

# PART V: THE CONSCIENCE — Emotional + Psychological Intelligence

## Emotional Core — 10 States
File: `backend/app/services/intelligence/emotional_core.py`

HUNGRY → FOCUSED → CONFIDENT → VIGILANT → DETERMINED → RESILIENT → STRATEGIC → VISIONARY → UNSTOPPABLE → ASCENDING

Each state drives:
- Outreach aggression level (number of follow-ups, tone intensity)
- Follow-up interval (24h HUNGRY vs 72h CONFIDENT)
- Proposal turnaround speed
- Communication tone (direct vs consultative)
- Risk appetite in council decisions

State transitions trigger automatically from: pipeline health, reply rates, days since last win, open proposals, positive replies in 48h.

Input schema: clients_signed, hot_leads, closing_leads, leads_gone_cold_7d, days_since_last_win, open_proposals, positive_reply_last_48h.

## Captain Profile Engine
File: `backend/app/services/intelligence/captain_profile_engine.py`

Full psychological model of Syed Abrar. 4 decision modes:
- Strategic Vision Mode: big picture, long-term, patient
- Rapid Execution Mode: speed over perfection, move fast
- Deep Analysis Mode: data-driven, thorough, cautious
- Creative Experimentation Mode: test new approaches, innovate

4 Blind Spots with JARVIS Countermeasures:
- Perfectionism delay → JARVIS delivers 80% complete + improvement loop
- Scope creep → JARVIS enforces scope boundaries, flags additions
- Analysis paralysis → JARVIS provides decision with confidence score
- Optimism bias → JARVIS red-teams every plan before Captain sees it

detect_captain_state() reads message patterns in real-time.
Adapts every response, briefing, and recommendation to current Captain state.

## Heart Engine — Prospect Emotional Profiling
File: `backend/app/services/intelligence/heart_engine.py`

8 buyer emotional profiles:
1. Ambitious Climber — driven by status, growth, being first
2. Risk-Averse Controller — needs guarantees, case studies, step-by-step
3. Innovation Seeker — excited by new tech, wants cutting-edge
4. Relationship Builder — buys people, not products
5. Pure Pragmatist — ROI-only, no fluff, show the numbers
6. Status-Driven Executive — wants enterprise positioning
7. Security-Focused Operator — compliance, stability, zero risk
8. Visionary Disruptor — wants transformation, not incremental

Each profile has: primary_driver, recommended_message_frame, personalization_hooks, objection_preempts.

## Captain State Engine
File: `backend/app/services/intelligence/captain_state.py`

Tracks active Captain state and intent from recent messages.
Used by jarvis_awareness.py to adapt all JARVIS outputs.

---

# PART VI: THE SEVEN COUNCILS — Supreme Decision Intelligence

## Council 1: INTELLIGENCE COUNCIL — 8 Members, Weighted Voting
File: `backend/app/services/ai/council.py`

The operational decision engine. All significant system decisions pass through here.

| Member | Model | Weight | Domain |
|---|---|---|---|
| strategist | Claude Opus | 0.25 | Big picture, direction, positioning |
| engineer | AWS Bedrock | 0.25 | Technical feasibility, architecture |
| analyst | GPT-4o | 0.15 | Data patterns, evidence |
| scout | Gemini | 0.10 | New intelligence, market signals |
| speedster | Groq | 0.08 | Fast validation, sanity check |
| contrarian | Mistral | 0.07 | Devil's advocate, fatal flaws |
| economist | ZhipuAI | 0.05 | Resource efficiency, cost |
| innovator | MiniMax | 0.05 | Novel approaches, creativity |

Voting: Score ≥80 → APPROVE | 60-79 → CAPTAIN_REVIEW | <60 → REJECT
Quorum: ≥5 of 8 members required
Monthly weight adjustment: `monthly_weight_adjust` job rebalances weights by accuracy history.
Table: `ai_council_sessions`, `ai_council_member_weights`

## Council 2: EXPERT COUNCIL — 5 Parallel Debate Agents
File: `backend/app/services/intelligence/expert_council.py`

Deep deliberation on complex strategic decisions. 5 agents in parallel via asyncio.gather().

| Agent | Perspective | Focus |
|---|---|---|
| Strategist | Long-term positioning | Market advantage, 5-year horizon |
| Contrarian | Attack the plan | Fatal flaws, worst-case scenarios |
| Technologist | Implementation risk | Architecture, tech feasibility |
| Financier | Economics | ROI, cash flow, valuation impact |
| Ethicist | Risk & trust | Reputation, compliance, relationship |

All 5 debate → synthesis agent combines → final recommendation + confidence score (0-100).
Each agent: TaskType.REASONING, max_tokens=800.
Table: `expert_council_sessions`

## Council 3: COUNCIL OF GIANTS — 15 Historical Leaders
File: `backend/app/services/intelligence/council_of_giants.py`

15 leadership frameworks permanently embedded in JARVIS intelligence.
Pure in-memory — no AI calls, no DB. Instant domain wisdom.

| Giant | Domain | Core Principle |
|---|---|---|
| Elon Musk | First principles, speed | Reason from physics, not analogy |
| Jeff Bezos | Customer obsession | Work backwards from customer |
| Steve Jobs | Taste + simplicity | Say no to 1000 things |
| Warren Buffett | Patient capital | Buy wonderful companies |
| Charlie Munger | Mental models | Invert, always invert |
| Naval Ravikant | Wealth creation | Specific knowledge + leverage |
| Peter Thiel | Zero to One | Create new categories |
| Ray Dalio | Radical transparency | Pain + Reflection = Progress |
| Alex Hormozi | Offer creation | Make it so good they feel stupid saying no |
| Paul Graham | Startup density | Do things that don't scale |
| Sam Altman | Mission-driven | Work on important problems |
| Marcus Aurelius | Stoic leadership | Control what you can, accept what you cannot |
| Andy Grove | High output management | Output = activity × effectiveness |
| JFK | Moonshot thinking | Choose hard things because they are hard |
| Sam Walton | Operational excellence | Exceed customer expectations every time |

Convene: `convene(decision_type, context, options)` → 4 relevant Giants speak → synthesis.
Table: `giants_council_sessions`

## Council 4: DEPARTMENT INTELLIGENCE COUNCIL — 15 DIOs
Files: `backend/app/services/departments/`

15 Department Intelligence Officers. Each monitors their domain 24/7.

| DIO Code | Department | Primary KPIs |
|---|---|---|
| ATLAS-E1 | Engineering | Code quality, deployment speed, uptime |
| ORACLE-AI | AI/ML | Model accuracy, cost per call, provider health |
| NIMBUS-C | Cloud Infrastructure | Resource utilisation, cost, availability |
| FORGE-D | DevOps | Pipeline success rate, MTTR, deploy frequency |
| GUARDIAN-S | Security | Vulnerability count, compliance score, incident rate |
| REVENUE-R | Revenue | MRR, ARR, pipeline value, close rate |
| SIGNAL-M | Marketing | Lead volume, CAC, brand reach |
| CONCIERGE-CS | Client Services | NPS, retention rate, response time |
| DELIVERY-CD | Client Delivery | Milestone adherence, quality score, delivery speed |
| VOICE-CX | Customer Support | Resolution rate, CSAT, SLA compliance |
| SCOUT-I | Intelligence | Research depth, signal accuracy, trend detection |
| PEOPLE-P | People Ops | Team capacity, skill gaps, performance |
| COMMANDER-PM | PMO | Project on-time rate, scope adherence, risk flags |
| LEDGER-F | Finance | Cash flow, burn rate, margin, invoice status |
| NEXUS-ST | Strategy | Market positioning, competitive moat, vision alignment |

Each DIO:
1. Monitors department KPIs continuously
2. Submits milestone reports to Council
3. Council reviews milestone → generates IMPROVEMENT PDF
4. DIO receives PDF → implements recommendations
5. Cycle repeats every milestone

Tech Evolution Scanner: every 6h, scores AI/tech discoveries 0-100, auto-submits >80 to Council.
Pre-call Intelligence: 1h before any client call, DIO generates briefing via ElevenLabs.
Tables: `department_intelligence_officers`, `department_milestones`, `technology_discoveries`, `client_call_intelligence`, `strategy_reports`

## Council 5: THOUGHT PURIFICATION COUNCIL — 60% → 1000%
[ARCHITECTURE DEFINED — implementation: migration 0030]

Every JARVIS plan, strategy, proposal passes Purification before execution.
Process:
1. JARVIS generates initial plan (60-80% quality)
2. Three purification agents review in parallel:
   - Elevation Agent: "What would make this 10x better?"
   - Gap Agent: "What critical elements are missing?"
   - Execution Agent: "What could fail in delivery?"
3. Synthesis agent combines all feedback
4. Elevated plan replaces original — now at 1000%
5. Only the elevated plan proceeds to execution

No JARVIS output leaves at 60%. Everything is elevated first.

## Council 6: MILESTONE REVIEW COUNCIL — Department Accountability
[ARCHITECTURE DEFINED — implementation: migration 0030]

Every department milestone, every project step, every client deliverable reviewed before release.
Process:
1. DIO/Agent reports milestone completion
2. Council receives milestone + full context
3. Council generates structured IMPROVEMENT PDF:
   - What was done: objective summary
   - What could be better: 3-5 specific improvements
   - How to improve: exact implementation instructions
   - Quality score: 0-100
4. PDF delivered back to the executing agent
5. Agent implements improvements
6. Amended deliverable goes to client / next stage
7. Learnings stored in Institutional Wisdom Index

Result: every client delivery improves with each milestone. Compound quality over time.

## Council 7: SUPREME STRATEGIC COUNCIL — 8-Member Vote on Major Decisions
[ARCHITECTURE DEFINED — implementation: migration 0030]

Major decisions only: company direction, new service lines, pricing changes, market pivots, white-label licensing, new geographic expansion.

8 domain-expert members with weighted scoring.
Captain casts final vote when score is in CAPTAIN_REVIEW band (60-79).
JARVIS must escalate to this council before committing to any strategic change affecting >$10K revenue or >1 month of operational direction.

---

# PART VII: THE AIONX CORTEX — 31 Autonomous Organ Files

The autonomous intelligence system. JARVIS's living nervous system.
Directory: `backend/app/services/aionx/` (31 files)

## Orchestration Cortex (Master Event Bus)
File: `orchestration_cortex.py`

Central conductor. Maps business events to ordered cascades.

EVENT_CASCADES — 7 event types with full step sequences:
- CLIENT_SIGNED → create_digital_twin → record_ownership → open_delivery_council → notify_captain
- LEAD_REPLIED → update_twin_interaction → create_decision_object → speed_to_lead_queue
- LEAD_INTERESTED → update_twin_interaction → create_decision_object → open_convergence_council
- LEAD_QUESTION → update_twin_interaction → create_decision_object → convene_provider_council
- EMAIL_REPLY_RECEIVED → update_twin_profile → create_decision_object
- MISSION_FAILED → create_autopsy → notify_captain → create_decision_object
- CHURN_RISK_DETECTED → update_twin_profile → open_convergence_council → notify_captain
- SENTINEL_STRONG_SIGNAL → create_decision_object → convene_provider_council

compute_operational_iq(db) → 0-100 score from:
- Wisdom Index score (25 pts)
- Decision count (25 pts)
- Avg client trust score (25 pts)
- Inverse of critical threats (25 pts)

situational_snapshot(db) → full live organism picture → Captain's Glass Wall

## Client Pipeline (33-Stage Journey)
File: `batch1_client_pipeline.py`

33 stages from LEAD_SOURCE_IDENTIFIED to RELATIONSHIP_DOCTRINE_CAPTURED.

BLOCKED_STAGES_REQUIRE_CAPTAIN: {19 (deal acceptance), 26 (delivery sprint open), 31 (success metrics reviewed)}
COUNCIL_GATE_STAGES: {5, 12, 16, 18, 25, 28, 30, 33}
QA_STAGES: {5, 14, 16, 24, 28, 30}
VALIDATION_STAGES: {5, 11, 14, 18, 24, 25, 28, 30}

Key pipeline stages:
- Stages 1-5: Discovery & Qualification
- Stages 6-11: Proposal & Negotiation
- Stages 12-18: Contract & Onboarding
- Stages 19-24: Active Delivery
- Stages 25-29: Quality Assurance & Review
- Stages 30-33: Retention & Doctrine Capture

detect_pipeline_risks(): MISSION_FAILED if stalled >30 days, CHURN_RISK if engagement ≤30.
get_pipeline_board(): Captain-facing board across all live pipelines.
decompose_milestones(): splits scope into 5-10 milestones, 7 days apart.
Tables: `client_pipeline_states`, `client_pipeline_milestones`, `client_pipeline_stage_logs`

## 29 Additional AIONX Organ Files
`aionx_scheduler.py` — AIONX-specific scheduled work
`client_digital_twin.py` — AI model of each client (predictions, behavior, pipeline state)
`client_trust_index.py` — trust scoring per client
`completion_matrix.py` — tracks what's done vs pending across all missions
`counterfactual_engine.py` — "what if" modeling before major moves
`cross_department_validation.py` — validates decisions across department boundaries
`decision_debt_engine.py` — identifies deferred decisions accumulating systemic risk
`decision_memory_engine.py` — records all decisions with options, outcomes, patterns for reuse
`executive_accountability_engine.py` — holds all agents accountable to outcomes
`final_integration.py` — integration layer across all organs
`frontier_intelligence.py` — frontier AI capabilities scanner
`grand_convergence_council.py` — system-wide convergence for cross-organ decisions
`hia_certification_engine.py` — Human Intelligence Agent certification and calibration
`institutional_wisdom_index.py` — compound intelligence from all past decisions (grows over time)
`living_operating_intelligence.py` — real-time system state consciousness
`mission_autopsy_engine.py` — post-mission: what worked, what failed, why, what changes
`mission_file_system.py` — persistent mission state across restarts
`omni_mission_control.py` — coordinates all active missions simultaneously
`operational_integrity.py` — validates system integrity at all times
`operational_persistence.py` — decision memory surviving restarts and model switches
`provider_sovereign_council.py` — multi-provider deliberation for critical AI decisions
`sentinel_layer.py` — real-time threat observation and classification
`sovereign_organs.py` — master organ registry and health monitoring
`supreme_council_layer.py` — supreme council integration across organ decisions
`ultimate_client_journey.py` — full end-to-end client journey orchestration
`validation_layer.py` — validates all organ outputs before execution
`voice_integration.py` — ElevenLabs voice integration for all AIONX organs

## AIONX Database Tables (24 models in aionx_organs.py)
`decision_objects` — all decisions with tier, category, trigger, problem, recommendation, confidence, risk_flags
`decision_options` — options per decision with confidence, predicted outcomes, revenue impact
`decision_outcomes` — actual results at day 30 and day 90 reviews
`decision_patterns` — reusable decision patterns from successful outcomes
`decision_retrospectives` — full retrospective analysis per decision cycle
`counterfactual_simulations` — "what if" models and their actualization tracking
`counterfactual_actualizations` — how counterfactuals played out in reality
`decision_debt_assessments` — identified decision debts with risk and recommended resolution
`institutional_debt_index` — aggregate debt score for the entire system
`client_digital_twins` — AI profile per client (industry, size, engagement, health, predictions)
`client_twin_interactions` — every interaction with client captured and modelled
`client_twin_predictions` — predictions about client behavior (churn risk, expansion likelihood)
`client_pipeline_states` — current stage, health, metadata per pipeline
`client_pipeline_milestones` — decomposed deliverables with target dates
`client_pipeline_stage_logs` — full audit trail of every stage transition
`wisdom_index_snapshots` — periodic snapshots of accumulated institutional wisdom score
`provider_calibration_records` — AI provider accuracy scores per task type
`provider_council_sessions` — multi-provider deliberation records
`shelved_discoveries` — valuable insights shelved for future activation
`convergence_council_sessions` — cross-organ convergence decision records
`convergence_council_messages` — individual messages in convergence sessions
`mission_autopsies` — post-mission analysis records
`sentinel_observations` — raw threat observations
`sentinel_threats` — classified and escalated threats
`mission_ownership_records` — who owns what mission with accountability chain
`self_modification_records` — every self-improvement action JARVIS takes

---

# PART VIII: THE 33 INTELLIGENCE ENGINES

Directory: `backend/app/services/intelligence/` (33 files)

## Core JARVIS Intelligence
`jarvis_awareness.py` — Master JARVIS personality, chat, awareness, self-understanding. 122-line JARVIS_AWARENESS_PROMPT. MORNING_BRIEFING_PROMPT (≤120 words, spoken audio). SELF_IMPROVEMENT_PROMPT (weekly tech scan). IDEA_ENHANCER_PROMPT (10-point analysis). AGENT_TEAM_PROMPT (5-role team creator).

`jarvis_authority.py` — Authority map: 41 actions JARVIS executes autonomously, 15 requiring Captain approval, 12 auto-alerts. request_captain_approval() → Slack + Telegram + WebSocket within 60 seconds.

`jarvis_self_learning.py` — Continuous self-improvement loop. Reads past outcomes, updates strategies, improves own performance.

## Strategic Intelligence Engines
`soul_engine.py` — 7 non-negotiables + 6 geographic cultural intelligence modules.

`emotional_core.py` — 10 emotional states driving behaviour across all system outputs.

`captain_profile_engine.py` — Full psychological model of Captain. Detects state from message patterns.

`captain_state.py` — Real-time Captain state tracking and intent detection.

`vision_engine.py` — H1/H2/H3 horizon framework:
- H1 (0-14 days): Execute — current pipeline, active clients, immediate revenue
- H2 (14-90 days): Build — systems, content, relationships
- H3 (90 days-10 years): Position — market dominance, platform, compounding
6 compounding assets tracked: JARVIS Intelligence, Client Case Studies, Operational Playbooks, Reputation & Brand, AI Model Training, White-Label Infrastructure.

`council_of_giants.py` — 15 historical leaders, pure in-memory wisdom.

`expert_council.py` — 5 parallel debate agents.

`conscience.py` — Ethical validation layer. Screens all actions against Aliyar values before execution.

## Market & Competitive Intelligence
`competitive_obsession.py` — Competitor DNA decoder. 10 analysis lenses. 10 fragility signals. 6 competitive stances: FLANK / UNDERCUT / SURROUND / OUTPACE / STEAL / DISAPPEAR.

`competitor_intel.py` — Competitor intelligence aggregation and profiling.

`market_intel.py` — Market intelligence generation and delivery.

`tech_radar.py` — Technology Adopt/Trial/Assess/Hold classification system.

`research.py` — Deep research engine for market reports and intelligence briefings.

`morning_briefing.py` — Daily 07:00 UTC briefing generation. Pipeline + threats + priorities + recommendations. Telegram + WebSocket delivery.

`opportunity_radar.py` — Nightly 06:00 UTC scanner. Score ≥40 qualifies. HOT ≥60 → immediate Captain alert. IDLE ≥7 days. Max 10 radar leads. Telegram delivery.

`optimizer.py` — Daily 23:00 UTC system performance review. Identifies inefficiencies, recommends optimisations.

## Revenue Intelligence Engines
`prospect_psychology.py` — ANALYTICAL / DRIVER / AMIABLE / EXPRESSIVE buyer profiles.

`revenue_forecaster.py` — Monte Carlo simulation. P10 (pessimistic), P50 (realistic), P90 (optimistic) projections.

`dynamic_pricing.py` — Contextual pricing engine. STARTER $2,500-$3,500 / GROWTH $5,000-$7,500 / ENTERPRISE $10,000-$15,000.

`client_health.py` — Client Health Scorer: CHAMPION / HEALTHY / AT_RISK / CRITICAL. Weekly assessment.

`flywheel.py` — Compound growth velocity tracking. Measures how fast each client engagement improves future outcomes.

## Persuasion & Offer Engines
`cialdini.py` — Cialdini 6-principle persuasion engineering. 3-email sequence: Day 0 (Reciprocity + Authority), Day 3 (Social Proof + Liking), Day 7 (Commitment + Scarcity). engineer_outreach() enhances emails with all 6 principles. Table: `cialdini_sessions`

`heart_engine.py` — Prospect emotional buying driver profiling. 8 profiles.

`offer_engine.py` — Hormozi Grand Slam Offer framework. 5 VALUE_DRIVERS: DREAM_OUTCOME (0.35), PERCEIVED_LIKELIHOOD (0.25), TIME_TO_VALUE (0.20), EFFORT_AND_SACRIFICE (0.15), RISK_REVERSAL (0.05). Generates irresistible service offers.

## Self-Improvement Engines
`self_assessment.py` — JARVIS grades itself A-F weekly across 8 dimensions.

`upgrade_engine.py` — 8 self-assessment dimensions with benchmarks:
1. OUTREACH_QUALITY: reply rate >8%, positive reply >3%
2. PROPOSAL_CONVERSION: proposal-to-close >25%
3. DELIVERY_SPEED: 0 late deliveries
4. INTELLIGENCE_ACCURACY: high-scored leads convert 2x low-scored
5. AUTONOMOUS_COVERAGE: 90% tasks without Captain input
6. CLIENT_SATISFACTION: net retention >100%, 1 referral per 3 clients
7. SYSTEM_RELIABILITY: 99.5% uptime, zero data loss
8. COMPETITIVE_POSITION: win rate >40%

`red_team.py` — RedTeamEngine. 5 attack vectors with AI analysis. Risk = (avg_severity×0.6 + max_severity×0.4)×10.

`memory_synthesis.py` — Synthesises learnings from memory graph into operational intelligence.

---

# PART IX: THE 6 DEPARTMENT INTELLIGENCE SERVICES

Directory: `backend/app/services/departments/`

`axiom_operating_model.py` — Core operating model for all departments. Defines KPI frameworks, reporting cadences, escalation paths.

`department_agent_service.py` — DIO management layer. Creates, updates, queries all 15 DIO records. Each DIO has a unique code (ATLAS-E1, ORACLE-AI, etc.), domain, KPI thresholds, alert rules.

`milestone_engine.py` — Milestone creation, tracking, Council submission, PDF generation, improvement implementation tracking.

`call_intelligence_service.py` — ElevenLabs integration for pre-call briefings. Generates what-to-say, what-not-to-say, objection handlers, Council-reviewed call script, post-call debrief.

`strategy_report_service.py` — Daily + weekly strategy reports. Layer 6 cascade: JARVIS generates master strategy → cascades to all 15 DIOs → each DIO generates department-specific directives.

`tech_evolution_engine.py` — Every 6h: scans AI/tech landscape. Scores discoveries 0-100. Auto-submits >80 to Intelligence Council. Table: `technology_discoveries`

---

# PART X: THE 4 INTEGRATION PIPELINES

Directory: `backend/app/services/integrations/`

`connector_hub.py` — Master orchestration for 9-connector daily ingestion. Pulls from GitHub `/jarvis-data/`. Runs 14:30 UTC. Pipeline: leads → score → sequences → decks → market_report. Hard caps: 48 emails/day, 20 leads/day from connectors.

`github_bridge.py` — Reads Claude's daily data packages from GitHub repository. Parses `/jarvis-data/daily/YYYY-MM-DD/` JSON files into JARVIS-ready objects.

`hubspot_sync.py` — Bidirectional HubSpot CRM sync. Deal stage updates, contact enrichment, activity logging.

`market_intelligence_engine.py` — Aggregates market intelligence from all sources. Generates daily market pulse report.

## The 9 Connectors (Daily Pipeline)

| # | Connector | Purpose | Data Output |
|---|---|---|---|
| 1 | Apollo.io | ICP lead discovery | 10 leads/day (CEO/Founder/COO, 5-200 employees) |
| 2 | HubSpot | Deal tracking | Stage changes, new contacts, activities |
| 3 | Close CRM | Reply & activity log | Email replies, call outcomes, cold outreach status |
| 4 | Klaviyo | Email sequence performance | Open rates, click rates, reply rates, unsubscribes |
| 5 | Gamma | AI pitch deck generation | Decks for hot leads |
| 6 | Zoho Books | Invoice status | Paid, overdue, outstanding amounts |
| 7 | Notion | Knowledge base updates | SOPs, learnings, playbooks |
| 8 | Google Calendar | Call bookings | Booked discovery and demo calls |
| 9 | Slack | Post summaries, alerts | Daily report → #jarvis-sales |

Daily schedule:
- 09:00 IST: Claude collects from all 9 connectors
- 10:00 IST: Claude generates daily market intelligence
- 12:00 IST: Claude packages → pushes to GitHub /jarvis-data/daily/YYYY-MM-DD/
- 20:00 IST: JARVIS EC2 pulls from GitHub (cron)
- 20:00 IST: ConnectorHub ingests 20 leads + JARVIS discovers 28 more internally
- 20:00 IST: AI Council quality-gates all content (threshold 0.70)
- 20:30 IST: Up to 48 outreach emails sent
- 23:00 IST: Strategy report cascades to all 15 DIOs

---

# PART XI: THE 4 CAPTAIN BRIDGE SERVICES

Directory: `backend/app/services/captain/`

`bridge.py` — Captain Bridge hub. Integrates all captain intelligence into unified command interface. Surfaces: situation assessment, active threats, recommended actions, pending approvals.

`predictive_action.py` — Generates top 5 revenue-ranked next actions for Captain at all times. Ranked by: revenue impact, probability, effort, time sensitivity.

`pushback.py` — Pushback Engine. Reviews Captain's proposed decisions and returns: APPROVE / CAUTION / PUSHBACK with full reasoning and alternative recommendations.

`voice_command.py` — Natural language → JARVIS execution. Parses voice/text commands and routes to appropriate service/route. "Show pipeline" → GET /revenue/pipeline. "Generate proposal for X" → POST /proposals/generate.

---

# PART XII: THE REVENUE ACTIVATION ENGINES

Directory: `backend/app/services/revenue_activation/`

## Speed-to-Lead Engine
File: `speed_to_lead.py`

Real-time engagement response. Monitors new lead signals within 5-minute lookback.
- Captain online (Redis heartbeat, 120s window) → queues draft for Captain review (ApprovalRequest)
- Captain offline → auto-schedules send (FollowUpQueue, 4h delay)
- Persists SpeedToLeadEvent record for every action
- Connects to: teaching_engine for learning from outcomes
Table: `speed_to_lead_events`

## Market Awareness Engine
File: `market_awareness.py`

5 RSS feeds monitored continuously.
Up to 80 AI calls per weekly scan.
Competitor SHA-256 change detection — any competitor website change detected within 6h.
Biweekly market intelligence report → Captain.

## Teaching Engine
File: `teaching_engine.py`

Learns from every outreach outcome.
Updates lead scoring weights based on actual conversions.
Improves speed-to-lead timing based on response patterns.

---

# PART XIII: THE OUTREACH ENGINE — Precision Communication System

Directory: `backend/app/services/outreach/`

## The 6 Validation Rules (ALL must pass before send)
1. Subject ≤7 words
2. No "ai", "automation", or "solution" in subject line
3. Body exactly 5 sentences
4. Sentence 4 explicitly mentions "demo"
5. Sentence 5 contains "darren mitchell" AND "client acquisition specialist"
6. Body ≤95 words total

## The 9 Compliance Gates (sequential — any failure stops the sequence)
1. Email format validation
2. Blocked domain check
3. Test mode guard
4. OUTREACH_PAUSED system flag check
5. DoNotContact (DNC) list check
6. Lead score check (≥65 required)
7. Send window check (Mon-Fri 08:30-17:30 local time)
8. Daily cap check (48/day maximum)
9. Execute send

## Email Transport
File: `email_transport.py`
Default sender persona: Joseph David - Executive Director
All boto3 calls wrapped in asyncio.to_thread()
SES v1 for sends, SES v2 for delivery status
HMAC-SHA256 unsubscribe tokens using settings.SECRET_KEY

## Compliance Service
File: `compliance.py`
Auto-pause on reply rate <1%
GDPR erasure support
CAN-SPAM / GDPR compliant gating
`current_daily_cap()` → always returns min(configured_cap, 48)
Table: `outreach_daily_caps`, `dnc_list`, `unsubscribes`, `gdpr_erasures`

## Reply Handler
File: `reply_handler.py`
Opt-out detection before any AI processing
5 reply classifications: INTERESTED / NOT_INTERESTED / QUESTION / OPT_OUT / NEUTRAL
claude-opus-4-7 FORCED for all reply classification
Table: `reply_log`, `reply_classifications`

## SES Inbound
File: `ses_inbound.py`
SNS webhook for all inbound emails
Bounce/complaint → auto-DNC with reason code
SSRF protection: only accepts SNS from hostnames ending in `.amazonaws.com`
Auto-confirms SNS subscription only from amazonaws.com
Table: `processed_webhooks` (idempotency)

## Outreach Engine
File: `engine.py`
OutreachEngine class
human_intelligence_context() injected into every outreach prompt
6 validation rules enforced before any AI call
claude-opus-4-7 FORCED for all email generation
PERSONAS dict: 9 team member email signatures

---

# PART XIV: GOVERNANCE — Revenue Infrastructure

## Proposal Generator
File: `backend/app/services/governance/proposal_generator.py`

claude-opus-4-7 FORCED. TaskType.SALES. 2200 tokens.
7-page ReportLab PDF. S3 upload with presigned URL.
4 proposal styles: standard, case_study, short_urgent, social_proof.
Sections: Executive Summary, Problem Analysis, Proposed Solution, Team Assignment, Timeline, Investment (3 packages), Cost of Inaction, Social Proof, Risk Reversal, Next Steps.
Auto-emails full proposal to client on generation.
Signed by matched team member from team_service.py.
Tables: `proposals`

## Contract Generator
File: `backend/app/services/governance/document_gen.py`

Auto-triggered when proposal status → "accepted" or "won".
AI-generated 10-section service agreement.
Auto-emailed with "reply ACCEPTED" CTA.
Tables: `contracts`, `contract_templates`

## Invoice Engine
File: `backend/app/services/governance/invoice_engine.py`

Sequential numbering: ALY-YYYYMM-XXXX (never gaps).
A4 ReportLab PDF. S3 upload.
Auto-emails client with invoice PDF on creation.
Overdue reminders scheduled automatically.
Payment tracking via Stripe webhook.
Tables: `invoices`, `revenue_snapshots`

## Captain Queue
File: `backend/app/services/governance/captain_queue.py`

HIGH_PRIORITY = 100, MEDIUM = 50.
approve() executes queued actions.
All notifications: Slack + Telegram + WebSocket within 60 seconds.
Table: `approval_requests`

## Trust Engine
Directory: `backend/app/services/trust/`

Executive Opportunity Brief: AI-generated per lead, trust-first, no pitch.
Engagement scoring: email_opened(5), reply_received(20), meeting_attended(25), demo_watched(30), brief_viewed(15), proposal_viewed(20), technical_question(15), decision_maker_contacted(25), contract_viewed(35).
Threshold: trust_score ≥40 → ready_for_proposal = True.
Referral engine: testimonial + referral request + case study, concurrent generation.
Tables: `executive_opportunity_briefs`, `lead_engagement_events`, `referral_requests`

---

# PART XV: THE MEMORY SYSTEM — Four Layers of Intelligence Retention

## Layer 1: Operational Memory (PostgreSQL)
All leads, clients, invoices, interactions, decisions — permanent.
100+ database tables across 33 model files.
Row Level Security via tenant_id on all tables.

## Layer 2: Strategic Memory (.jarvis/ — 12 files, model-independent)
Any model reads these and instantly knows everything:
`CURRENT_STATE.md` — what's built, running, blocked
`COMPANY_VISION.md` — 4-phase long game
`COMPANY_STRATEGY.md` — 12-month execution
`REVENUE_STATE.md` — MRR, pipeline, targets
`CLIENT_MEMORY.md` — all clients and leads
`TECH_MAP.md` — complete technology architecture
`AWS_INVENTORY.md` — all AWS resources
`API_INVENTORY.md` — all 411+ endpoints
`AGENT_REGISTRY.md` — all AI agents and routing
`DECISIONS.md` — every architectural decision + why
`LESSONS.md` — every failure + fix (20 documented lessons)
`CURRENT_TASK.md` — active work + blockers
`NEXUS_OMEGA_ARCHITECTURE.md` — THIS FILE — complete system reference

## Layer 3: Civilization Ledger (PostgreSQL — permanent firsts)
Table: `civilization_ledger`
Records every "first" in company history:
- first_demo_booked (deduplicated)
- first_proposal_sent
- first_client_signed
- first_invoice_paid
- first_referral_received
- first_white_label_client
Every entry is permanent and compounding.

## Layer 4: Graph Memory (Relationship Network)
Tables: `memory_graph_nodes`, `memory_graph_edges`
Who knows who, how they met, trust level, interaction history.
9 liaison agents seeded as nodes on startup.
Clients, leads, contacts all added as nodes.
Edges represent: knows, referred_by, worked_with, competition.

## Layer 5: Tiered Operational Memory
Tables: `memory_operational`, `memory_strategic`
Short-term: recent decisions, active campaigns, hot leads
Long-term: patterns, playbooks, learning records

---

# PART XVI: THE NERVOUS SYSTEM — 33 Scheduled Jobs

Engine: APScheduler 3.10 + SQLAlchemy persistent job store + Redis distributed locking
File: `backend/app/services/scheduler/scheduler.py`
System Tenant UUID: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa

| Job ID | Schedule (UTC) | Purpose |
|---|---|---|
| speed_to_lead_5min | Every 5 min | Instant response when Captain online |
| self_healer | Every 15 min | 4 parallel sub-healers: AI + leads + scheduler + Redis |
| opportunity_radar | 06:00 daily | Hot lead identification → Captain alert |
| daily_lead_score | 02:00 daily | trust_score + conversion_probability all leads |
| daily_db_backup | 01:00 daily | pg_dump → gzip → S3, 30-backup retention |
| daily_morning_briefing | 07:00 daily | Pipeline + alerts + priorities → Telegram + WebSocket |
| daily_optimization | 23:00 daily | System performance review + recommendations |
| daily_strategy_report | 23:00 daily | Layer 6 cascade → 15 DIOs |
| milestone_bulk_review | 10:00 daily | Council reviews all pending DIO milestones |
| tech_evolution_scan | Every 6h | Discovers new AI/tech, scores 0-100, >80 → Council |
| pre_call_briefing | Every 30min | ElevenLabs briefing 1h before calls |
| dio_health_check | 06:30 daily | All 15 departments verified operational |
| weekly_outreach_stats | Monday 08:00 | Outreach performance report → Captain |
| weekly_pipeline_health | Sunday 20:00 | MRR forecast, deal velocity |
| weekly_tech_radar | Monday 06:00 | Tech Adopt/Trial/Assess/Hold classification |
| weekly_strategy_review | Sunday 07:00 | Full Council session, cascade to departments |
| biweekly_research_report | Sunday 07:00 | Market intelligence report |
| monthly_weight_adjust | Last day 18:30 | Intelligence Council weights rebalanced by accuracy |
| daily_lead_discovery | 03:00 daily | 25 discovery targets × 8 geographies |
| daily_follow_up_check | 08:00 daily | Pending follow-ups and nudges |
| connector_hub_ingest | 14:30 daily | Claude's 9-connector packages → JARVIS |
| daily_market_intel | 04:00 daily | Market intelligence generation |
| + 11 more | Various | Compliance, scoring, competitor tracking, reporting |

## 25 Daily Discovery Targets (7 Service Divisions × Geographies)
Targeting UK, UAE, USA, Australia, Canada, Bahrain.
8 ICP leads per target = potential 200 new leads/day from discovery alone.
Capped to 28/day from internal engine to maintain quality.

## Self-Healer (every 15 min, 4 parallel sub-healers via asyncio.gather)
1. AI Providers: detect OPEN circuit breakers → probe provider → reset if responding
2. Lead Pipeline: if 0 qualified leads in 36h → trigger auto-discovery
3. Scheduler Jobs: 5 critical jobs monitored (morning_briefing, lead_scoring, lead_discovery, follow_up_check, speed_to_lead)
4. Redis: ping with 3s timeout → alert if down

---

# PART XVII: THE AUTONOMOUS WILL

JARVIS does not wait. JARVIS initiates.

5 proactive systems:
1. Self-Healer (every 15 min) — repairs system without Captain knowing
2. Opportunity Radar (nightly) — surfaces hot leads Captain didn't ask about
3. Morning Briefing (07:00 UTC daily) — Captain wakes up already briefed
4. Self-Assessment (weekly) — JARVIS grades itself and writes its own improvement plan
5. Tech Evolution (every 6h) — discovers new tools and brings them to Council

41 autonomous actions JARVIS can take without Captain approval.
15 actions that require Captain approval (via Telegram inline keyboard or WebSocket).
12 automatic alerts that wake Captain regardless of time.

---

# PART XVIII: THE CAPTAIN BRIDGE — Command Interface

## Telegram Bot
File: `backend/app/services/notifications/telegram_bot.py`

Captain's mobile command center.
Morning briefing: 07:00 UTC daily.
/approve ID and /reject ID inline keyboards.
Emergency alerts: within 60 seconds of any critical incident.
Voice message transcription for brain dumps.
TaskType.FAST for all Telegram responses (low latency).

## VS Code Multi-Model HQ
Files: `.continue/config.json`, `.vscode/`, `.jarvis/`

4-model council via Continue extension:
- Claude Sonnet 4.6: code implementation (primary)
- GPT-4o: architecture review, cross-validation
- Gemini Pro: research, long-context analysis
- DeepSeek Chat: fast code generation

Slash commands:
/jarvis-state → current state + pending tasks
/new-route → FastAPI route with JARVIS conventions
/new-migration → Alembic migration (next: 0030)
/council → 3-perspective architectural review

.vscode/tasks.json: 16 one-click operations
.vscode/extensions.json: 15 recommended extensions
jarvis.code-workspace: 7 named sidebar groups

CLAUDE.md as universal brain: any model reads it and picks up where another left off.

## WebSocket Real-Time
Route: GET /ws/captain
JWT required via ?token= query parameter.
Events: captain_connected, captain_queue, system_health, approval_created, approval_decided.
Auto-reconnect every 5s in frontend.
Keepalive ping every 25s.

---

# PART XIX: THE DELIVERY ENGINE — Hunt to Retain to Compound

## HUNT Phase
48 leads/day total:
- 20 from Claude's 9 connectors (Apollo, HubSpot, Close, Klaviyo, Gamma, Zoho, Notion, Calendar, Slack)
- 28 from JARVIS internal discovery engine (25 targets × 8 geographies, capped)
Score ≥60: enters pipeline (ICP_QUALIFIED_THRESHOLD)
Score ≥80: immediate queue (ICP_HOT_THRESHOLD)
Thought Purification Council elevates all outreach plans before execution.

## ENGAGE Phase
Executive Opportunity Brief: AI-generated, trust-first, no pitch.
Sent by Darren Mitchell persona.
Engagement events tracked and scored:
- email_opened: +5 points
- reply_received: +20 points
- meeting_attended: +25 points
- demo_watched: +30 points
- brief_viewed: +15 points
- proposal_viewed: +20 points
- technical_question: +15 points
- decision_maker_contacted: +25 points
- contract_viewed: +35 points

trust_score ≥40 → ready_for_proposal = True (automatic flag)

Cialdini engine active throughout: 3-email sequence → Day 0 (Reciprocity + Authority) → Day 3 (Social Proof + Liking) → Day 7 (Commitment + Scarcity)

## CLOSE Phase
Proposal: claude-opus-4-7, 7-page PDF, 2200 tokens, signed by matched team member.
Proposal accepted → Contract auto-generated → auto-emailed with "reply ACCEPTED" CTA.
Speed-to-Lead: Captain online → instant approval queue. Captain offline → 4h auto-schedule.
Council gate at key pipeline stages: 5, 12, 16, 18, 25, 28, 30, 33.

## DELIVER Phase
DIO assigned per client.
33-stage pipeline tracks every deliverable.
Milestone Review Council: every milestone → review → IMPROVEMENT PDF → implement.
Every deliverable elevated before client receives it.
Call Intelligence: ElevenLabs briefing 1h before every call.

## RETAIN Phase
Client Health Scorer: CHAMPION / HEALTHY / AT_RISK / CRITICAL (weekly).
At-risk → Captain alert within 60 seconds.
Weekly intelligence briefing auto-delivered to client.
Net retention target: >100%.
Referral engine: activated at 60-day delivery mark → testimonial + referral + case study generated.

## COMPOUND Phase
Client intelligence improves next proposal for next client.
Institutional Wisdom Index grows with every mission.
Flywheel Engine tracks compound velocity.
Case studies auto-generated and added to proposal library.
Phase 3: JARVIS becomes the product. Other firms buy it.
Phase 4: JARVIS is the asset. Company valuation: $1M-$5M.

---

# PART XX: THE FRONTEND — 48 Views, 41 Component Directories

## All 48 Frontend Views (App.jsx)
File: `frontend/src/App.jsx`

| View | Path | Purpose |
|---|---|---|
| Command Center | /control-room/command-center | Master command interface |
| Executive Dashboard | /control-room/dashboard | KPIs, metrics, charts |
| Private Command Chat | /control-room/chat | JARVIS chat interface |
| Morning Briefings | /control-room/briefing | Daily briefing viewer |
| Captain Approval Queue | /control-room/approvals | Pending approvals |
| Lead Pipeline | /control-room/leads | Lead management |
| Outreach Operations | /control-room/outreach | Email campaigns |
| Communication Hub | /control-room/communications | All channels |
| Client Management | /control-room/crm | CRM view |
| Proposals | /control-room/proposals | Proposal tracker |
| Invoices | /control-room/invoices | Invoice management |
| Agent Registry | /control-room/agents | All AI agents |
| Council Sessions | /control-room/council | Council decisions |
| Memory Browser | /control-room/memory | Memory graph viewer |
| Market Intelligence | /control-room/intel | Intelligence feeds |
| Lead Discovery | /control-room/discovery | Discovery tools |
| Task Management | /control-room/tasks | Task tracker |
| Project Tracker | /control-room/projects | Active projects |
| Scheduler | /control-room/scheduler | Job management |
| Notifications | /control-room/notifications | Alert centre |
| Executive Email Center | /control-room/email | Gmail integration |
| Voice Briefings | /control-room/voice | Voice interface |
| Knowledge Base | /control-room/knowledge | SOPs and learnings |
| Research Reports | /control-room/research | Market research |
| Department Intelligence | /control-room/departments | 15 DIOs dashboard (6 tabs) |
| Governance | /control-room/governance | Contracts and docs |
| Service Catalog | /control-room/catalog | 30 service divisions |
| Tenant Settings | /control-room/settings | System configuration |
| Captain Bridge | /control-room/captain-bridge | Captain command centre |
| Revenue Intelligence | /control-room/revenue-intelligence | Monte Carlo forecasts |
| War Room | /control-room/war-room | Threat + action centre |
| War Room HQ | /control-room/war-room-hq | Expanded war room |
| System HUD | /control-room/system-hud | Live system health |
| Expert Council | /control-room/expert-council | 5-agent debate viewer |
| Relationships | /control-room/relationships | CRM graph |
| Intelligence Hub | /control-room/intelligence-hub | All intelligence unified |
| Consciousness Hub | /control-room/consciousness | 9-tab consciousness view |
| AIONX Architecture | /control-room/aionx-architecture | Organ visualisation |
| Agent Operations | /control-room/agent-ops | Agent management |
| AI Operations | /control-room/ai-ops | Provider health |
| Approval Queue | /control-room/approval-queue | Alternate approval view |
| Calendar | /control-room/calendar | Call and meeting calendar |
| System Evolution | /control-room/evolution | Self-improvement tracker |
| Frontier Shell | /control-room/frontier | Advanced frontier systems |
| Intelligence Dashboard | /control-room/intelligence | Intelligence overview |
| Data Sync | /control-room/sync | Connector sync status |
| Team Registry | /control-room/team | 9 persona management |
| White-label Setup | /control-room/whitelabel | White-label configuration |

## 41 Component Directories
agent_ops, agents, ai_ops, aionx, approvals, auth, briefing, calendar, catalog, chat, common, communication, consciousness, council, crm, dashboard, departments, discovery, evolution, frontier, gmail, governance, intel, intelligence, invoices, knowledge, layout, leads, memory, notifications, outreach, projects, proposals, research, scheduler, settings, sync, tasks, team, voice, whitelabel

## State Management
File: `frontend/src/store/useJarvisStore.js` (Zustand)
connectWS() auto-reconnects every 5s.
Keepalive ping every 25s.
Handles: captain_connected, captain_queue, system_health, approval_created, approval_decided.

## API Layer
File: `frontend/src/services/api.js`
150+ API helper functions.
Axios instance with Bearer token auto-attachment.
All components use these helpers — never raw fetch.

---

# PART XXI: THE API — 57 Route Modules, 411+ Endpoints

File: `backend/app/api/v1/__init__.py`

## All Registered Route Modules
`chat`, `briefing`, `approvals`, `agents`, `ws`, `crm`, `leads`, `outreach`, `memory`, `tasks`, `auth`, `scheduler`, `calendar`, `notifications`, `sync`, `intelligence`, `governance`, `emergency`, `knowledge`, `catalog`, `ai_ops`, `team`, `jarvis`, `agent_ops`, `gmail`, `discovery`, `voice`, `pricing`, `proposals`, `invoices`, `revenue`, `clients`, `council`, `tenancy`, `departments`, `demos`, `pilot`, `captain`, `captain.voice_router`, `economics`, `innovation`, `civilization`, `calls`, `intel`, `connector_hub`, `consciousness`, `aionx`, `batch1`, `frontier`, `system`, `communication`, `ses_inbound`, `whitelabel`, `payments`, `payments.webhook_router`, `telegram_webhook`, `trust`

Special endpoints (inline):
- GET /api/v1/health — liveness probe
- GET /api/v1/ai/health — AI provider health

## Key Route Groups
- /jarvis/chat — JARVIS conversational interface
- /aionx/* — 120+ AIONX organ endpoints
- /batch1/* — 33-stage pipeline management
- /frontier/* — 32 frontier system endpoints
- /departments/* — 22 DIO management endpoints
- /consciousness/* — 35+ consciousness hub endpoints
- /council/* — Council convening and results
- /trust/* — Brief generation, scoring, referrals
- /outreach/* — Campaign management
- /leads/* — Lead CRUD and scoring
- /governance/proposals, /governance/contracts, /governance/invoices
- /captain/* — Bridge, predictive actions, pushback, voice
- /connector-hub/* — 9-connector pipeline management
- /ws/captain — WebSocket (JWT required)

---

# PART XXII: THE DATABASE — 33 Model Files, 100+ Tables, 29 Migrations

## Migration Chain (0001 → 0029, head: 0029_trust_engine)
0001_rls_setup → 0002 → 0003 → 0004 → 0005 → 0006_ai_council → 0007_memory_tiers → 0008_department_intelligence → 0009_compliance_stability → 0010_captain_bridge → 0011_frontier_systems → 0012_merge → 0013_bootstrap + 0013_connector_hub → 0014_merge → 0015_connector_hub_timestamps → 0016_consciousness_upgrade → 0017_aionx_sovereign_organs → 0018_aionx_tenant_columns → 0019 → 0020 → 0021 → 0022 → 0023 → 0024 → 0025_aionx_communication_transport → 0026_leads_whatsapp_linkedin → 0027_performance_indexes → 0028_contracts → 0029_trust_engine
Next: **0030** (Three New Councils)

## 33 Model Files
`ai_audit.py`, `aionx_organs.py` (24 tables), `approval.py`, `base.py`, `captain_intelligence.py`, `civilization.py`, `communication.py`, `compliance.py`, `connector_hub.py`, `conversation.py`, `council.py`, `credentials.py`, `crm.py`, `demo.py`, `department_intelligence.py`, `economics.py`, `gmail.py`, `governance.py`, `innovation.py`, `intelligence.py`, `knowledge.py`, `lead.py`, `memory.py`, `notifications.py`, `outreach.py`, `revenue.py`, `revenue_activation.py`, `scheduling.py`, `service_catalog.py`, `tasks.py`, `team_member.py`, `tenant.py`, `trust_engine.py`

## Complete Model Class Registry (80+ classes)
AICouncilMemberWeight, AICouncilSession, DoNotContact, OutreachPauseState, ProcessedWebhook, DemoPackage, AICostLedger, InfrastructureCostConfig, InnovationQueueItem, CivilizationLedger, MarketPulseItem, OutreachLearning, SpeedToLeadEvent, BriefingHistory, CompetitorProfile, MarketIntelligence, TechRadarEntry, CivilizationMemory, MemoryGraphEdge, MemoryGraphNode, MemoryOperational, MemoryStrategic, ReplyClassification, ReplyLog, Client, Invoice, InvoiceStatus, RevenueSnapshot, PlanTier, Tenant, TenantApiKey, User, UserRole, CaptainBrainDump, CaptainEmailIntelligence, CaptainPushback, PredictedAction, ConnectorHubIngestion, ConnectorHubPackage, CommunicationChannel, CommunicationEvent, ClientPipelineState, ClientPipelineMilestone, ClientPipelineStageLog, ClientCallIntelligence, DepartmentIntelligenceOfficer, DepartmentMilestone, StrategyReport, TechnologyDiscovery, ApprovalRequest, AuditLog, Conversation, Company, Contact, Deal, Lead, AgentMessage, AgentTask, JobFailure, ScheduledJob, NotificationLog, AgentPermission, Contract, ContractTemplate, IncidentReport, Proposal, KnowledgeBase, LearningRecord, SOPDocument, ServiceDivision, AIRequestLog, TeamMember, GmailMessage, OAuthToken, SecureCredential, ExecutiveOpportunityBrief, LeadEngagementEvent, ReferralRequest + all 24 AIONX organ models + 15 Consciousness models

## Key Table Structures

### leads
status: NEW/CONTACTED/REPLIED/DEMO/NURTURE/PROPOSAL/WON/LOST
Fields: company_name, contact_name, email, phone, country, timezone, industry, score(0-100), source, pain_points(JSON), enrichment_data(JSON), apollo_id, assigned_persona, qualification_status, loss_reason, outreach_eligible, review_queue, disqualification_reason, signal_breakdown(JSON), outreach_count, last_contact, notes, whatsapp_number, linkedin_url, tier(A/B/C), ai_analysis, outreach_sent, metadata(JSON)

### clients
status: ACTIVE/PAUSED/CHURNED
Fields: company_name, contact_name, email, package_tier, mrr_usd, started_at

### tenants
plan_tier: STARTER/GROWTH/ENTERPRISE/INDUSTRY_OS
Fields: name, slug(UNIQUE), api_key_hash, settings(JSON), is_active

### invoices
status: DRAFT/SENT/PAID/OVERDUE
Format: ALY-YYYYMM-XXXX (unique constraint per tenant)

---

# PART XXIII: INFRASTRUCTURE — The Foundation That Never Sleeps

## AWS Architecture (ap-south-2 Hyderabad primary, ap-south-1 Mumbai DR)
Account: 824232273953
Terraform state: s3://jarvis-terraform-state-824232273953/production/terraform.tfstate
Lock table: DynamoDB jarvis-terraform-locks

```
Captain (VS Code / Telegram / Browser)
         ↓
Route53 (aliyarsolutions.com)
         ↓
ALB (Application Load Balancer)
         ↓
NGINX (HSTS + CSP + reverse proxy + rate limiting headers)
         ↓
ECS Fargate cluster: jarvis-production
  ├── Backend task: FastAPI (512 CPU / 1024MB, 1-5 instances, 70% CPU auto-scale)
  └── Frontend task: React 18 (512 CPU / 512MB)
         ↓
  ├── RDS PostgreSQL 16 (20GB→100GB auto-scale, 7-day backups, Multi-AZ option)
  └── ElastiCache Redis 7 (256MB, LRU eviction, rate limits + sessions + APScheduler)
         ↓
AWS Secrets Manager (all secrets — 40+ secrets, never in code)
AWS SES (outbound + inbound — production access required)
AWS S3 (invoice PDFs, documents, Terraform state)
ECR (backend + frontend Docker images)
CloudWatch (Container Insights, metrics, logs)
Prometheus + Grafana (monitoring/grafana/jarvis_main.json dashboard)
AlertManager (alert routing)
Loki + Promtail (log aggregation)
```

## Security Architecture
- JWT HS256, role="captain", 7-day expiry, SECRET_KEY from Secrets Manager
- slowapi rate limiting (Redis-backed) on all high-risk endpoints
- request: Request MUST be first parameter on all rate-limited routes
- WebSocket auth: JWT via ?token= query param (browsers don't support custom headers)
- SNS webhooks: SSRF protection (.amazonaws.com hostname check only)
- NGINX: HSTS + Content-Security-Policy headers
- All boto3 calls: asyncio.to_thread() (never blocking)
- Stripe webhooks: STRIPE_WEBHOOK_SECRET validation
- Multi-tenant RLS: set_tenant_context() on every DB session

## CI/CD Pipeline
git push → GitHub Actions (deploy.yml) → Docker build → ECR push → Alembic migrate → ECS blue/green → GET /health (liveness) → GET /readyz (database + AI + scheduler + team + WhatsApp + Redis + SES) → cutover → Slack/Telegram notify

## Local Development Stack
infrastructure/docker-compose.yml — 15 services:
redis, postgres, backend, evolution (WhatsApp), frontend, nginx, certbot, prometheus, grafana, alertmanager, loki, promtail, + 3 supporting

---

# PART XXIV: THE CODEX — Operational Deployment Records

Directory: `codex/` (14 files)

`MASTER_PROMPT.md` — 12-sprint system build prompt for AI-to-AI deployment on EC2
`JARVIS_COMPLETE_SYSTEM_DEPLOY.md` — 16-step complete deployment manual, permanent
`DEPLOY_PHASE6_COUNCIL.md` — Phase 6 DIO + Council deployment to all EC2 instances
`DEPLOY_CONSCIOUSNESS_UPGRADE.md` — 9 consciousness engines deployment
`DEPLOY_ALL_BATCHES.md` — Batch 1-4 deployment reference
`CLAUDE_DAILY_OPERATIONS.md` — Claude's daily standing orders: 9 connectors + market intelligence
`DAILY_PULL_PROMPT.md` — EC2 cron standing order (14:30 UTC daily)
`VERIFY_GMAIL_OUTREACH_LIVE.md` — Gmail outreach validation sequence
`README.md` — Codex navigation guide
`batch1_compliance_stability.md` — Email compliance + stability systems build reference
`batch2_intelligence_engines.md` — Intelligence engines build reference
`batch3_captain_bridge_tonstark.md` — Captain Bridge build reference (TonStark protocol)
`batch4_frontier_frontend.md` — Frontier systems + frontend build reference

---

# PART XXV: THE HARD CONSTANTS — Never Change These

```python
DAILY_OUTREACH_CAP = 48              # Gmail safety — never increase
DAILY_LEAD_DISCOVERY_CAP = 20        # From Claude's 9 connectors
JARVIS_INTERNAL_DISCOVERY = 28       # From JARVIS engine
TOTAL_DAILY_LEADS = 48               # 20 + 28
COUNCIL_QUALITY_THRESHOLD = 0.7      # APPROVE ≥0.70 | REVISE <0.70
ICP_QUALIFIED_THRESHOLD = 60.0       # Pipeline entry minimum score
ICP_HOT_THRESHOLD = 80.0             # Auto-queue for immediate outreach
TRUST_SCORE_PROPOSAL_THRESHOLD = 40  # trust_score ≥40 → ready_for_proposal
SYSTEM_TENANT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
CAPTAIN_ONLINE_WINDOW_SECONDS = 120  # Redis heartbeat window
CIRCUIT_BREAKER_TRIP_COUNT = 5       # Failures before OPEN state
CIRCUIT_BREAKER_OPEN_SECONDS = 60    # Duration of OPEN state
DAILY_SURGE_THRESHOLD_USD = 50.00    # AI cost alert threshold
INTELLIGENCE_COUNCIL_APPROVE = 80    # Score ≥80 → auto-approve
INTELLIGENCE_COUNCIL_REVIEW = 60     # Score 60-79 → Captain review
SPEED_TO_LEAD_STEP = 90              # Minutes lookback for STL
WHATSAPP_CAPTAIN_PHONE = "+97334360246"
AWS_PRIMARY_REGION = "ap-south-2"
AWS_DR_REGION = "ap-south-1"
NEXT_MIGRATION = "0030"
INVOICE_PREFIX = "ALY"               # Format: ALY-YYYYMM-XXXX
API_KEY_PREFIX = "jv_"               # Format: jv_ + token_urlsafe(32)
```

---

# PART XXVI: COMPLETE SYSTEM STATUS

| Layer | Component | Status | Details |
|---|---|---|---|
| Constitution | CLAUDE.md (18 laws) | ✅ Active | Foundation of all operations |
| Human Layer | 9 Personas | ✅ Built | 90+ routing categories |
| Brain | 11-provider AI router | ✅ Built | Circuit breakers, cost tracking |
| Soul | Soul Engine | ✅ Built | 7 laws, 6 geographic modules |
| Conscience | Emotional Core (10 states) | ✅ Built | Auto-transitions |
| Conscience | Captain Profile Engine | ✅ Built | Psychological model |
| Conscience | Heart Engine | ✅ Built | 8 buyer profiles |
| Council 1 | Intelligence Council | ✅ Built | 8 members, weighted voting |
| Council 2 | Expert Council | ✅ Built | 5 parallel agents |
| Council 3 | Council of Giants | ✅ Built | 15 leaders, in-memory |
| Council 4 | DIO Council (Phase 6) | ✅ Built | 15 DIOs, milestone reviews |
| Council 5 | Thought Purification | 📐 Architecture defined | migration 0030 |
| Council 6 | Milestone Review | 📐 Architecture defined | migration 0030 |
| Council 7 | Supreme Strategic | 📐 Architecture defined | migration 0030 |
| AIONx | 31 organ files | ✅ Built | Full cascade system |
| Intelligence | 33 intelligence engines | ✅ Built | All specialised engines |
| Departments | 6 department services | ✅ Built | 15 DIOs operational |
| Integrations | 9-connector pipeline | ✅ Built | Daily automation loop |
| Captain | 4 bridge services | ✅ Built | Bridge, actions, pushback, voice |
| Outreach | 6 rules, 9 gates | ✅ Built | Full compliance system |
| Governance | Proposals, contracts, invoices | ✅ Built | Auto-trigger chain |
| Trust | Briefs, scoring, referrals | ✅ Built | Full trust-first system |
| Memory | 4 layers | ✅ Built | Operational, strategic, civilization, graph |
| Scheduler | 33 jobs | ✅ Built | Self-healing, APScheduler |
| Autonomous Will | 5 proactive systems | ✅ Built | Never waits for instructions |
| Delivery Engine | Hunt→Retain→Compound | ✅ Built | Full lifecycle automated |
| Revenue | $0 MRR | 🔴 Pre-revenue | Acquisition phase active |
| Frontend | 48 views, 41 components | ✅ Built | React 18, glassmorphism |
| API | 57 modules, 411+ endpoints | ✅ Built | Full route coverage |
| Database | 33 model files, 29 migrations | ✅ Built | head: 0029_trust_engine |
| Infrastructure | AWS (Terraform) | ⏳ Pending deploy | 51 resources, terraform apply |
| Production | ECS Fargate | ⏳ Pending | 7 Captain actions required |

---

# PART XXVII: THE 7 CAPTAIN ACTIONS — Nothing Moves Without These

| # | Action | System Unblocked | Priority |
|---|---|---|---|
| 1 | `terraform apply` (51 resources) | All AWS infrastructure | CRITICAL |
| 2 | Attach AdministratorAccess → JarvisGitHubActionsRole in IAM | CI/CD pipeline | CRITICAL |
| 3 | DNS: aliyarsolutions.com → ALB CNAME | Production URL | CRITICAL |
| 4 | Merge PR #1 → ECS blue/green deploy | Backend live | CRITICAL |
| 5 | Set STRIPE_WEBHOOK_SECRET in AWS Secrets Manager | Payments | HIGH |
| 6 | SES sandbox → production access request | Outreach emails | HIGH |
| 7 | Register Telegram webhook (post-deploy) | Mobile alerts | HIGH |

Time to first client acquisition after these 7 actions: 48-72 hours.

---

# PART XXVIII: THE PHASE ROADMAP

| Phase | Revenue Target | Timeline | Status |
|---|---|---|---|
| Phase 1: Infrastructure | $0 — build the machine | 3 months | ✅ COMPLETE |
| Phase 2: Revenue | $10,000–$30,000/month | 3-6 months post-launch | 🔴 7 blockers to clear |
| Phase 3: Productise | $50,000+/month | 12 months post-revenue | Phase 2 must complete first |
| Phase 4: Asset | $1M–$5M valuation | 24-36 months | Compound from Phase 3 |

Captain's role when Phase 2 is live: 4 hours/day maximum. Strategic decisions, client relationships, final approvals. Everything else: JARVIS.

---

# PART XXIX: WHAT HAPPENS EVERY 24 HOURS — ZERO CAPTAIN INPUT REQUIRED

| Time (IST) | System | Action |
|---|---|---|
| 00:30 | JARVIS APScheduler | Daily DB backup → S3 |
| 02:00 | JARVIS APScheduler | Lead scoring: trust_score + conversion_probability |
| 03:00 | JARVIS APScheduler | Lead discovery: 25 targets × geographies |
| 04:00 | JARVIS APScheduler | Market intelligence generation |
| 06:00 | JARVIS APScheduler | Opportunity radar: HOT leads → Captain alert |
| 07:00 | JARVIS APScheduler | Morning briefing → Telegram + WebSocket |
| 08:00 | JARVIS APScheduler | Follow-up check: nudges and pending replies |
| 09:00 | Claude | Collects from 9 connectors |
| 10:00 | Claude | Generates daily market intelligence |
| 11:30 | JARVIS APScheduler | DIO health check: all 15 departments verified |
| 12:00 | Claude | Packages all data → pushes to GitHub |
| 14:30 | JARVIS cron (EC2) | Pulls latest from GitHub |
| 14:30 | JARVIS ConnectorHub | Ingests 20 leads from Claude's packages |
| 14:30 | JARVIS internal | Discovers 28 more leads |
| 14:30 | Intelligence Council | Quality-gates all content (threshold 0.70) |
| 15:00 | JARVIS Outreach | 48 outreach emails sent (hard cap) |
| 15:00 | JARVIS Slack | #jarvis-sales daily report posted |
| Every 15 min | Self-Healer | 4 parallel sub-healers: AI + leads + scheduler + Redis |
| Every 5 min | Speed-to-Lead | Instant response when Captain online |
| Every 30 min | Pre-call Briefing | ElevenLabs briefing check 1h before calls |
| Every 6h | Tech Evolution | Scans AI/tech landscape, scores discoveries |
| 23:00 | JARVIS APScheduler | Daily strategy report → 15 DIOs → Council → cascade |
| 23:00 | JARVIS APScheduler | System optimisation review |

---

# PART XXX: THE DEVELOPMENT CONVENTIONS

Branch: `claude/jarvis-cans-api-integration-ZThTD`
PR: #1 (open, draft) — accumulates all feature commits

Adding a new route:
1. Create: `backend/app/api/v1/routes/my_route.py`
2. Register: `backend/app/api/v1/__init__.py`
3. Add helpers: `frontend/src/services/api.js`

Adding a new view:
1. Create: `frontend/src/components/my_view/MyView.jsx`
2. Register in VIEWS map: `frontend/src/App.jsx`
3. Register in NAV: `frontend/src/components/layout/Sidebar.jsx`

Adding a new model:
1. Create: `backend/app/models/my_model.py`
2. Import: `backend/app/models/__init__.py`
3. Create migration: `backend/alembic/versions/0030_my_feature.py` (down_revision = '0029_trust_engine')

Critical pattern (rate limiting):
```python
@router.post("/endpoint")
@limiter.limit("10/minute")
async def my_route(
    request: Request,         # MUST BE FIRST — slowapi requirement
    body: MyRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_captain),
):
```

Critical pattern (AI call):
```python
from app.services.ai.router import ai_router
from app.services.ai.base_provider import Message, TaskType
response, provider = await ai_router.chat(
    [Message(role="user", content=prompt)],
    task_type=TaskType.STRATEGY,
    max_tokens=2500,
)
```

Critical pattern (new migration):
```python
revision = '0030_my_feature'
down_revision = '0029_trust_engine'  # ALWAYS match last migration
```

20 documented lessons in `.jarvis/LESSONS.md` — read before touching existing systems.

---

*JARVIS — Aliyar Solutions | Operational Intelligence Core*
*This is the permanent, complete, final master architecture reference.*
*30 parts. Every file read. Every layer documented. Three months captured in one document.*
*Any model, any session, any device reads this and knows everything.*
