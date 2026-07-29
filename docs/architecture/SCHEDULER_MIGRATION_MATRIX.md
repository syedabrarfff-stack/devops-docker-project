# Scheduler Migration Matrix — Task #23

**Status:** Authoritative migration plan for retiring `app/services/scheduler/engine.py`
in favor of the canonical `app/services/scheduler/scheduler.py`.
**Do not delete `engine.py`** until every row below is either `Implemented` or has an
explicit Captain sign-off to leave it unmigrated.

Background: `engine.py` was never started in production (`main.py` only calls
`scheduler.py`'s `start_scheduler()`; `scheduler/__init__.py` only re-exports from
`scheduler.py`). `scheduler.py` already contains a `DEPRECATED_JOB_IDS` list that
proves most of this migration was done deliberately in the past — 21 of its 23
entries are exact matches to `engine.py` job names. This matrix accounts for the
remaining gap: jobs that were never carried over, in either direction.

## Legend

| Disposition | Meaning |
|---|---|
| **Implemented** | Done and merged as of this document (Task #23 Phase A/B, commit `5d35ed0`) |
| **Keep as-is** | Already correct in `scheduler.py`; no further work |
| **Merge** | Folded into an existing `scheduler.py` job; no separate job needed |
| **Rewrite** | Needs a fresh implementation in `scheduler.py`, reusing engine.py's logic where sound |
| **Replace** | A newer, better mechanism already covers this need; the old job should not be ported as-is |
| **Remove permanently** | Confirmed dead weight in both files; safe to drop with zero functional loss |

---

## Section 1 — Already resolved (Task #23 Phase A/B)

| Job | Disposition | Business purpose | Technical dependency | Replacement | Why this is correct |
|---|---|---|---|---|---|
| `daily_briefing` | Superseded | Generic AI-chat morning message to Captain | `ai_router.chat` → Telegram | `daily_morning_briefing` + `captain_dashboard_briefing` | Both replacements carry real pipeline data; this one was a freeform chat prompt with no data behind it. Already in `DEPRECATED_JOB_IDS`. |
| `lead_scoring_sweep` | Merge | Re-score existing leads on a cadence | `bulk_score` | `daily_lead_scoring` | Same underlying need, richer per-tenant implementation already exists. |
| `daily_icp_lead_scoring` | Merge | Score yesterday's new leads, promote top 20 | `lead_scoring_engine.score_yesterday_new_leads` | `daily_lead_scoring` | Calls the *exact same* function. |
| `outreach_processor` | Merge | Send due outreach emails | `outreach_engine.execute_due_outreach` | `daily_follow_up_check` | Same call, multi-tenant. |
| `contact_sync` | Keep as manual-only | Apollo contact sync | `sync_from_apollo` | `POST /sync/apollo` | Function still reachable on demand via `routes/sync.py`. Confirm with Captain whether this should be re-scheduled or stay manual — flagged, not silently dropped. |
| `tech_radar_scan` | Merge (renamed) | Weekly tech radar scan | `TechRadarEngine.scan_week` | `weekly_tech_radar` | Identical call. |
| `market_intelligence_report` | Replace | Bi-weekly market intel report | `MarketIntelligenceEngine.generate_report` | `biweekly_research_report` | Same engine, different topic list (`RESEARCH_TOPICS` vs `DEFAULT_MARKET_TOPICS`) and same alternate-week guard — functionally equivalent, not byte-identical. |
| **`competitor_monitoring`** | **Implemented** | Competitor intelligence — Captain-designated core strategic capability | `MarketIntelligenceEngine.monitor_competitors` | `weekly_competitor_monitoring` (Mon 09:00 UTC) | Was the one confirmed real gap (no schedule, no manual route). Restored per Captain's explicit decision. |
| `morning_briefing` | Merge | Data-driven morning briefing | `MorningBriefingEngine.generate_and_send` | `daily_morning_briefing` | Identical call. |
| `daily_optimization_review` | Keep as-is, enhanced | System self-optimization recommendations | `analyze_system` | `daily_optimization_review` | Same name, same core call, scheduler.py's version adds per-tenant RLS looping. |
| `daily_self_learning` | **Rewrite (see Section 2)** | | | | |
| `biweekly_research_report` | Keep as-is | — | — | — | Name collision with `market_intelligence_report`'s replacement above; already correct. |
| `memory_consolidation` | Merge | Working → operational memory promotion | `memory_engine.consolidate_working_to_operational` | `daily_memory_consolidate` | Superset — also prunes and promotes in the same job. |
| `weekly_memory_promotion` | Merge | Operational → strategic memory promotion | `memory_engine.promote_high_relevance_operational` | `daily_memory_consolidate` | Folded into the daily job above — cadence upgrade (weekly → daily), not a loss. |
| `reply_handler_scan` | **Remove permanently** | Inbound reply classification | SES inbound (never configured) | none | Was already a no-op stub in engine.py itself ("disabled until SES inbound processing is configured"). Nothing to migrate. |
| `overnight_lead_discovery` | Replace | Discover new leads | `bulk_score` (mislabeled — this actually re-scores, doesn't discover) | `daily_lead_discovery` | engine.py's version didn't even do what its docstring claimed. `daily_lead_discovery` calls the real `lead_discovery_engine.run_daily_discovery` with 25 targeted search terms — a working superset. |
| `overnight_intel_analysis` | Merge | Market intelligence analysis | `analyze_system` | `daily_optimization_review` | Same call. |
| `overnight_proposal_engine` | **Remove permanently (see Section 2, `nightly_signal_scan`)** | | | | |
| `overnight_cold_outreach` | Merge | Cold outreach email send | `send_outreach_email` due-queue | `daily_follow_up_check` | Same pattern. |
| `overnight_freelance_bids` | **Remove permanently** | Upwork/PPH bid automation | `self_improvement_report` (mislabeled) | none | engine.py's own implementation never matched its docstring — called an unrelated self-improvement report function, never did real bidding. Nothing functional to lose. |
| `overnight_followup_sequences` | Merge | Follow-up email sequences | `send_outreach_email` due-queue | `daily_follow_up_check` | Same pattern. |
| `overnight_pipeline_health` | Replace | Pipeline health check | `bulk_score(limit=50)` | `weekly_pipeline_health` | Replacement (`_pipeline_health_summary` + `notify_business_event`) is materially richer. |
| `overnight_ops_report` | **Rewrite (see Section 2)** | | | | |
| `daily_connector_hub_ingestion` | Keep as-is | — | `connector_hub.ingest_daily_package` | `daily_connector_hub_ingestion` | Identical call, already unchanged. |
| `daily_market_intelligence` | Keep as-is | — | `market_intelligence_engine.write_github_intelligence_package` | `daily_market_intelligence` | Identical call, already unchanged. |
| `self_healer` | **Implemented** | Autonomous subsystem repair | `run_self_healing_cycle` | `self_healer` (unchanged job, fixed body) | Restored the dropped `_report_self_heal_to_headquarters` call per Captain's explicit decision — "self-healing without reporting is incomplete." |
| Routing optimizer registrar | **Implemented** | Learn AI provider routing weights from 30d metrics | `run_routing_optimizer` | `routing_optimizer_sweep` (1st of month, 03:00 UTC) | Implementation was already production-quality; only the registrar's import of the dead `engine.py` was broken. Kept per Captain: "JARVIS depends heavily on intelligent AI routing." |
| LinkedIn outreach registrar | **Implemented** | Enrich HOT leads via Proxycurl, generate connection messages | `linkedin_outreach_sweep` | `linkedin_outreach_sweep` (every 2h) | Business logic was production-quality (real API calls, real AI generation — the same `ai_router.chat` tuple-unpack bug fixed earlier this session already lived here). Registrar imported a `scheduler` attribute that **never existed** on `engine.py` — this job never ran regardless of the engine/scheduler split. Kept per Captain: "sales automation is a core business capability." |
| Voice analytics registrar | **Implemented** | Daily voice interaction metrics | `run_voice_analytics_job` | `voice_analytics_daily` (04:30 UTC) | Same never-existed-attribute bug. Implementation queries real data, persists, and alerts Slack — judged complete. Kept per Captain: "migrate only if the implementation is complete." |

---

## Section 2 — Still needs a migration (not yet implemented)

These require your review before implementation — several have real behavioral
complexity (locking, multi-step cascades) or overlap with each other in ways
that need a product decision, not just a code port.

| Job | Disposition | Business purpose | Technical dependency | Replacement | Why |
|---|---|---|---|---|---|
| `nightly_signal_scan` | **Rewrite — highest priority** | Scan active pipeline leads for buying-intent signals, alert Captain, auto-queue proposals for the highest-confidence HOT leads | `scan_lead`, `auto_generate_proposal_for_lead` (real governance/proposals pipeline, not a memory blob) | none yet — needs to be ported | This job's auto-proposal path is the **one proposal pipeline** per Captain's decision #1. Must be ported with its existing confidence gates intact (HOT tier, confidence≥85, score≥75, capped at 2/run) exactly as-is — do not simplify the gates away. |
| `overnight_proposal_engine` | **Remove permanently** | AI-draft proposals for top-scored leads | `ai_router.chat` → stores a memory blob, flips lead status | folded into `nightly_signal_scan` | Captain's explicit decision: "one proposal pipeline is enough." This job's version is cruder (memory blob, no real `Proposal` record) than `nightly_signal_scan`'s `auto_generate_proposal_for_lead` path. Do not port this one separately. |
| `daily_self_learning` | Rewrite | JARVIS's daily self-evolution cycle | `run_daily_learning_cycle` | none yet | No equivalent anywhere in `scheduler.py` or AIONX. Real, distinct capability tied to the "self-compounding technology company" vision (CLAUDE.md §17) — recommend high priority. |
| `drift_auditor` | Rewrite | Detect duplicate config / stale files / conflicting definitions before they cause an outage | `run_drift_audit` | none yet | Its own docstring explicitly ties it to preventing recurrence of "the 2026-07-04 outage." Recommend high priority given that stated purpose. |
| `nexus_heartbeat` | Rewrite — needs care | Pipeline pulse; autonomous outreach trigger (Redis-locked, 4h cooldown); WebSocket broadcast to frontend | `run_pulse`, `run_autopilot_cycle`, Redis lock, `broadcast` | none yet | The only other Redis-lock usage in either scheduler file besides `scheduler.py`'s own job-lock mechanism — needs careful review to avoid two independent locking schemes colliding. Do not port mechanically; consider whether this should use `scheduler.py`'s existing `_acquire_job_lock`/`JOB_LOCK_TTLS` mechanism instead of its own ad-hoc Redis lock. |
| `daily_strategy_report` | Rewrite | 6-layer strategy cascade: department data → Council → directives → Captain | `strategy_report_service.generate_daily_strategy_report` | none yet | No equivalent. Part of the "6-Layer Autonomous Intelligence System." |
| `weekly_strategy_review` | Rewrite | Full weekly strategic review, 30/60/90-day horizon | `strategy_report_service.generate_weekly_strategy_report` | none yet | Same subsystem as above — recommend migrating together. |
| `milestone_bulk_review` | Rewrite | Bulk Council review of all pending milestones | `milestone_engine.run_bulk_milestone_review` | none yet | No equivalent. |
| `tech_evolution_scan` | Rewrite | 24/7 technology discovery and evaluation cycle | `tech_evolution_engine.run_discovery_cycle` | none yet | Distinct from `weekly_tech_radar` (a different engine/purpose) — do not conflate the two when migrating. |
| `pre_call_briefing_trigger` | Rewrite | Generate briefings 90 min before scheduled calls | `call_intelligence_service.generate_pre_call_briefing` | none yet | No equivalent. Time-window-based (not a fixed cron slot) — needs the same 30-min interval-poll pattern engine.py used. |
| `dio_health_check` | Rewrite | Department Intelligence Officer init/health check | `department_agent_service.initialize_all_dios` | none yet | No equivalent. |
| `daily_scout_network` | Rewrite | 9-agent scout lead discovery → GitHub push | `scout_network.run_all_scouts` | none yet | Distinct from `daily_lead_discovery` (Google Maps search) — a different discovery channel, not a duplicate. |
| `lead_embedding_sweep` | Rewrite | Nightly semantic embedding of leads without embeddings | `embed_pending_leads` | none yet | No equivalent. |
| `captain_dashboard_briefing` | Rewrite (mechanical) | Real pipeline-stats morning dashboard | `notify_captain_morning_briefing` | none yet | **Function already exists and was already fixed this session** (its scheduler-health line now reads the real scheduler). Only needs a job-spec entry — this is the lowest-effort item in this table. |
| `weekly_performance_briefing` | Rewrite (mechanical) | 7-day performance summary via Telegram | `notify_weekly_performance_briefing` | none yet | Function already exists in `telegram_bot.py`, untouched and presumably correct. Only needs a job-spec entry — low effort. |

## Recommended sequencing for Section 2

1. `captain_dashboard_briefing`, `weekly_performance_briefing` — trivial (function exists, just needs a spec entry). Do these first.
2. `nightly_signal_scan` — highest business priority per your proposal-dedup decision; also unblocks fully removing `overnight_proposal_engine`.
3. `drift_auditor`, `daily_self_learning` — both tied to stated architectural principles (outage prevention, self-compounding company vision).
4. `daily_strategy_report` + `weekly_strategy_review` + `milestone_bulk_review` + `dio_health_check` — the "6-Layer" and Council subsystem; migrate together since they share dependencies.
5. `tech_evolution_scan`, `daily_scout_network`, `lead_embedding_sweep`, `pre_call_briefing_trigger` — independent, can be done in any order.
6. `nexus_heartbeat` last — the most architecturally sensitive one (locking scheme question needs resolving first).

## Phase C gate (unchanged from Task #23 approval)

`engine.py` is deleted only after every row above is `Implemented`, `Merge`,
`Replace`, or `Remove permanently` — no row left in a "needs a migration" state —
plus green tests and a full scheduler validation pass (job registration, manual
trigger, health checks, Telegram, self-healer, persistence-after-restart).
