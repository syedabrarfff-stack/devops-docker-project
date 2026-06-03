# JARVIS BUILD INSTRUCTIONS FOR CODEX

## READ THIS FIRST

These 4 files contain complete instructions to build the full 227-system JARVIS architecture on EC2.

## ORDER OF EXECUTION — STRICTLY SEQUENTIAL

| Batch | File | Systems | What It Builds |
|-------|------|---------|----------------|
| **1** | `batch1_compliance_stability.md` | 1-12 | Email compliance, CAN-SPAM, GDPR, job locking, dead letter queue, backup |
| **2** | `batch2_intelligence_engines.md` | 13-23 | Lead scoring v2, revenue forecasting, memory synthesis, client health, pricing AI |
| **3** | `batch3_captain_bridge_tonstark.md` | 24-45 | Captain Bridge (10 parts), voice commands, war room, situation feed, pushback engine |
| **4** | `batch4_frontier_frontend.md` | 46-101+ | Red team, expert council, conscience layer, relationship graph, 7 frontend views |

## RULES

1. **Complete and verify each batch before starting the next.**
2. Each batch includes its own Alembic migration — run `alembic upgrade head` after each.
3. Working directory on EC2: `/opt/jarvis/`
4. Deploy after each batch: `docker-compose up -d --build jarvis_app`
5. Each batch ends with a verification checklist — all items must be checked before proceeding.
6. **Never touch .env**
7. After all 4 batches: `git commit -m "feat: JARVIS 227-system architecture complete"` and `git push origin main`

## VERIFICATION COMMAND (run after each batch)

```bash
curl -s http://localhost:8000/health && echo "HEALTH OK"
curl -s http://localhost:8000/api/v1/system/hud | python3 -m json.tool
```
