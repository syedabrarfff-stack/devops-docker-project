---
description: Full Production Readiness Review — never deploy without this first
---

Perform a complete Production Readiness Review per the locked engineering workflow.
Do not deploy or change infrastructure as part of this command — review only.

Verify and report on:
1. Git repository status (branch, latest commit, uncommitted changes)
2. Branch status (up to date with origin?)
3. Environment variables (DEBUG flag, placeholder secrets, required vars present)
4. Secrets configuration (rotation status, plaintext exposure risk)
5. Database migration safety (alembic current vs head, untested migrations)
6. Docker build status (all services build clean)
7. AI provider configuration (keys present, Fabric router health if built)
8. Scheduler readiness (jobs registered, no stuck jobs)
9. Monitoring stack (Prometheus/Grafana/Loki reachable)
10. CI/CD pipeline (last run status, workflow file valid)
11. AWS infrastructure (EC2 reachable, IAM role assumable)
12. Health checks (/health, /readyz return 200)

Classify every issue found as Critical / High / Medium / Low.

End with one of: ✅ Proceed / ⚠️ Proceed with Conditions / ❌ Do Not Proceed,
plus rollback plan and estimated deployment + downtime, per the locked deployment
review format. Wait for explicit Captain approval before any deployment follows.
