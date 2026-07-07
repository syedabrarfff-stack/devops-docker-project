# Headquarters Engineering Organization
## Phase 7 — Mission Planner + Autonomous Engineering Departments

> Scope boundary (non-negotiable): this layer builds and evolves the product. It does
> NOT redesign the CRM, dashboard, governance, AI Fabric, memory, or business AI Council
> (Strategist/Engineer/Analyst/Scout/Speedster/Contrarian/Economist — L4, Phase 4). Those
> are the product. Headquarters is the organization that maintains and extends it.

```
CEO
 │
 ▼
Captain
 │
 ▼
Headquarters (VS Code + Claude Code)
 │
 ▼
Mission Planner                              ← NEW — decomposes objectives into task graphs
 │
 ▼
Engineering Organization                      ← NEW — 12 departments, each with owned domain
 │  Platform · Cloud · DevOps · Backend · Frontend · AI · Security
 │  SRE · Database · Documentation · QA · Architecture
 │
 ▼
Engineering Council                           ← NEW category on the EXISTING Council engine
 │  (peer review / conflict resolution for engineering decisions — reuses
 │   backend/app/services/council/, does not fork it)
 │
 ▼
GitHub → CI/CD → AWS → Production Dashboard → Verification → Memory
 (all four of these already exist and are unchanged)
```

---

## 1. Why this reuses existing infrastructure instead of forking it

Three subsystems already do 80% of what "departments" and "Engineering Council" need.
Building parallel versions would be pure duplication:

| Need | Reused from | Why not build new |
|---|---|---|
| Task scheduling, retries, priority | `kernel/task_queue.py` (K1-5), `kernel/retry_coordinator.py` (K1-6) | Already transactional, persistent, backed by PG+Redis |
| Model routing per department | `fabric/router.py` (F3-3), `fabric/model_registry.py` (F3-2) | Already does task-profile → model selection → fallback |
| Multi-agent review / conflict resolution | `council/assembly.py`, `council/reasoning.py`, `council/conflict_resolution.py` (C4-1..C4-4) | Already does parallel reasoning + confidence scoring; just needs a new `task_category` and a new member catalogue for engineering roles — not a new engine |
| Authority gating on infra/deploy actions | `kernel/policy_engine.py` + `authority_matrix.py` (K1-3) | Every department's actions still pass through the SAME Authority Matrix — a department cannot bypass ASK_CAPTAIN/NEVER tiers |
| Deployment | `services/headquarters/deploy.py` (HQ-7, already built and gated `production.deploy` ASK_CAPTAIN) | Departments produce PRs; deploy still goes through the exact same SSM self-invoke path |

The two genuinely new things are the **Mission Planner** (nothing decomposes a plain-English
objective into a task graph today — the Task Book is hand-authored) and the **Department
Registry** (nothing currently assigns *ownership* of a file/service boundary to a specific
agent identity with its own builder+reviewer pair and track record).

---

## 2. Mission Planner

**Input:** an engineering objective in plain English — feature request, infra change,
security finding, migration, incident.

**Output:** a `TaskGraph` — a DAG of `WorkPackage` nodes, each with:
- owning department
- acceptance criteria (testable)
- dependencies (other work package IDs)
- authority tier (looked up per-action via the existing Authority Matrix — the Planner
  does not invent its own risk model)

**Pipeline:**
```
Objective → Fabric Router (classify: feature | infra | security | migration | incident)
          → Decompose into candidate work packages (department-shaped chunks)
          → Dependency resolution (topological sort)
          → Authority Matrix pre-check per package (flags any ASK/NEVER items up front)
          → TaskGraph persisted → handed to Work Package Dispatcher
```

A `TaskGraph` for "Build CRM module X" decomposes into work packages like:
`platform: provision table/index` → `backend: API + service layer` → `frontend: UI` →
`security: auth review` → `qa: test plan` → `documentation: update architecture doc` →
`devops: CI pipeline update` — each assigned to its department, with dependencies wired
(frontend depends on backend, qa depends on both, etc).

---

## 3. Engineering Organization — Departments

Each department is a `DepartmentAgent`: a builder/reviewer pair (same free-model/premium-model
split the Task Book already uses) plus an **ownership boundary** — a set of path globs and
service names it is accountable for. A department:

1. Receives work packages from the Dispatcher (via the existing Task Queue — no new queue)
2. Drafts the change (builder tier: NIM/Gemini/DeepSeek, same as existing Task Book builders)
3. Self-tests before submitting for review
4. Submits to peer review (Engineering Council, or a designated reviewer department for
   smaller changes — not every change needs full Council)
5. On approval: commit → PR → existing CI/CD → existing deploy path

| Department | Owns | Model tier (builder) |
|---|---|---|
| Platform | Kubernetes/EKS (future), networking, core infra primitives | NIM |
| Cloud | AWS resources, Terraform, IAM policy drafting (still ASK_CAPTAIN-gated) | Gemini |
| DevOps | GitHub Actions, Docker, CI/CD pipelines | NIM |
| SRE | Incidents, monitoring, self-heal runbooks, uptime | DeepSeek |
| Backend | FastAPI services, business logic, migrations | NIM |
| Frontend | React components, UI, Zustand stores | NIM |
| AI | Fabric routing rules, model registry entries, prompt engineering | Gemini |
| Security | IAM review, dependency scanning, auth code paths | Claude (no free-tier drafting on security-sensitive code) |
| Database | Schema design, indices, query performance | NIM |
| Documentation | Architecture docs, changelogs, runbooks | NIM |
| QA | Test plans, coverage, regression suites | NIM |
| Architecture | Cross-department design review, ADRs | Claude |

Note: Security and Architecture default to Claude-only drafting (no free-tier builder) —
these two domains are where a wrong "cheap draft" is most costly, mirroring the existing
principle that judgment is precious and volume is cheap only where mistakes are recoverable.

---

## 4. Engineering Council (new category, existing engine)

`backend/app/services/council/assembly.py` gets one addition: a new `task_category`,
`"engineering_review"`, with its own member catalogue (department leads: Platform,
Backend, Security, Architecture as the default quorum — same assembly/reasoning/
conflict-resolution/recommendation pipeline C4-1..C4-4 already runs). This is a few new
dict entries in `_MEMBER_CATALOGUE` and `_CATEGORY_MEMBERS`, not a new module.

Used for: cross-department conflicts (e.g. Backend and Security disagree on an auth
change), architecture-significant decisions, and any work package the Mission Planner
flags as high-uncertainty.

---

## 5. Authority Matrix — unchanged, still the only gate

No department, and no Mission Planner decomposition, can grant itself authority beyond
what `authority_matrix.py` already defines. A work package touching `aws.iam.modify_roles`
is still NEVER-tier no matter which department drafted it. This is enforced at the
Dispatcher level: every work package is tagged with its `operation` type before
execution, and the Policy Engine intercepts exactly as it does today for every other
Headquarters action.

---

## 6. What does NOT change

- CRM, dashboard, governance, AI Fabric, memory, business AI Council — untouched.
- Deploy mechanism (SSM self-invoke, `production.deploy` ASK_CAPTAIN) — unchanged.
- Kernel (state machine, event bus, task queue, retry, health, override controller) — unchanged, reused as-is.
- The customer-facing product is the *output* of this organization, never its subject.
