# VS Code Headquarters — Extreme Delivery Configuration
## The command center that builds and operates JARVIS v4

> Purpose: configure VS Code + Claude Code so Captain gives one plain-English command
> and the system plans, fans out to parallel agents, builds with free models, reviews
> with premium models, verifies, commits, pushes, deploys, and reports — fast and stable.

---

## 1. The Three Operating Modes

| Mode | Trigger | Behavior |
|---|---|---|
| **Reactive** | Captain types a command | 7-step review → approval → 12-step execution |
| **Proactive** | Session open, idle | Watch health/CI/PRs → find issues → fix (AUTO-tier) → report |
| **Scheduled** | CCR cron (laptop can be off) | 07:00 UTC self-heal: health → diagnose → fix → verify → brief Captain |

## 2. The Delivery Engine (how v4 gets built fast)

```
Captain: "build phase 1"
   │
   ▼
CLAUDE (orchestrator, in VS Code)
   │  reads JARVIS_V4_ARCHITECTURE.md + JARVIS_V4_TASKBOOK.md + TASKBOOK_STATUS.json
   │  selects all unblocked tasks in the phase
   ▼
FAN-OUT — parallel lanes (up to 10 simultaneous)
   ├─ Lane 1: builder drafts K1-2 (State Machine)      [NIM key 1]
   ├─ Lane 2: builder drafts K1-3 (Policy Engine)      [Gemini]
   ├─ Lane 3: builder drafts K1-4 (Event Bus)          [NIM key 2]
   ├─ Lane 4: builder drafts K1-5 (Task Queue)         [NIM key 3]
   └─ Lane N: ...                                      [rotating keys]
   ▼
REVIEW GATE — Claude reviews every draft
   │  correct / reject / integrate; tests must pass
   ▼
VERIFY — imports, unit tests, health checks
   ▼
COMMIT + PUSH → GitHub Actions → EC2 deploy → health gates
   ▼
REPORT — "Verified: K1-2, K1-4, K1-5. Rejected: K1-3 draft (reason), rebuilding."
```

Key principle: **free models produce volume, Claude produces judgment.** Nothing merges
without review + verification. Speed comes from parallelism, never from skipped gates.

## 3. Components To Install/Configure

### 3.1 Repo-level Claude Code configuration (`.claude/`)
- `settings.json` — permissions allowlist (git, docker, pytest, curl health checks),
  so routine build/test commands never stall on prompts
- `commands/` — slash commands:
  - `/build-phase <N>` — run the fan-out delivery engine for a Task Book phase
  - `/council <question>` — assemble multi-model council on a decision
  - `/readiness` — full Production Readiness Review
  - `/heal` — health check → diagnose → fix → verify cycle
  - `/status` — Task Book progress + production health one-pager
- `hooks/` — SessionStart hook: load `JARVIS_SELF_KNOWLEDGE.md` + `TASKBOOK_STATUS.json`
  so every session starts already knowing system state

### 3.2 The Builder Bridge (`scripts/agent_bridge.py`)
A small Python orchestrator Claude invokes to delegate drafting to free models:
- Reads a Task Book task ID → constructs prompt (architecture context + task spec + existing code style)
- Calls NVIDIA NIM (rotating across the 10 keys) or Gemini API
- Writes result to `draft/<task-id>/` — never to real service paths
- Records builder, model, latency, tokens to `TASKBOOK_STATUS.json`
- Claude then reviews the draft and integrates or rejects

### 3.3 VS Code workspace (`.vscode/`)
- `tasks.json` — one-key tasks: run backend tests, docker build, health check prod,
  tail EC2 logs (via SSM), trigger deploy workflow
- `settings.json` — Python + ESLint + file nesting for the kernel/fabric/council trees
- `extensions.json` — recommended: Claude Code, Python, Docker, GitLens

### 3.4 Autonomy plumbing (already proven in this project)
- GitHub Actions `ec2-deploy.yml` (OIDC → SSM → base64 script) — the deploy arm
- PR Activity subscription — CI fails at any hour → auto-diagnose → fix → push
- CCR cron trigger — 07:00 UTC scheduled self-heal session
- Telegram override channel — PAUSE / STOP / ROLLBACK / SHUTDOWN (Kernel K1-9)

## 4. Guarantees

1. **Stability** — nothing unreviewed ever merges; every merge is tested + verified
2. **Speed** — up to 10 parallel build lanes; free-tier volume costs ~$0
3. **Continuity** — Task Book status survives session limits; any new session resumes exactly where the last stopped
4. **Authority** — Policy Engine tiers enforced; ASK/NEVER actions always reach Captain
5. **Evidence** — every report is "Verified" with health checks, logs, and test results

## 5. Setup Order (when Captain approves implementation)

1. `.claude/settings.json` + slash commands + SessionStart hook (~1h)
2. `scripts/agent_bridge.py` builder bridge + `TASKBOOK_STATUS.json` (~2h)
3. `.vscode/` workspace config (~0.5h)
4. Dry-run: one Task Book task through the full pipeline (draft → review → verify) (~1h)
5. Then: `/build-phase 0` — production blockers first, always.
