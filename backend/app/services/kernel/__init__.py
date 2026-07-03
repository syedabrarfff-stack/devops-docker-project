"""JARVIS v4 Runtime Kernel — L3 subsystems.

All subsystems expose an async interface. No subsystem calls an LLM directly;
AI routing flows through L4 (Fabric). No engine mutates production state
without a prior Policy Engine check.

Subsystems:
  event_bus           — Redis pub/sub, typed events
  state_machine       — single source of truth, transactional, versioned (K1-2)
  policy_engine       — Authority Matrix interceptor (K1-3)
  task_queue          — priority queue, persistent (K1-5)
  retry_coordinator   — circuit breakers, backoff+jitter (K1-6)
  health_aggregator   — 30s poll, aggregate, publish (K1-7)
  audit_logger        — append-only, queryable (K1-8)
  override_controller — Telegram PAUSE/STOP/ROLLBACK/SHUTDOWN (K1-9)
"""
