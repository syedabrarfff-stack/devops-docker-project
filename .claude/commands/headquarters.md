---
description: Open JARVIS Headquarters — architecture, model keys, task book, git and production status in one screen
---

Produce a single "Headquarters" splash screen. This is the entry point Captain
uses at the start of every local VS Code session. Read-only — never mutate
anything. Keep the whole report to one screen, no filler.

1. **System identity** — one line: "JARVIS v4 — Aliyar Solutions Headquarters".

2. **V4 Architecture snapshot** — read `docs/architecture/JARVIS_V4_ARCHITECTURE.md`
   and `docs/architecture/VSCODE_HQ_SETUP.md`; summarise in 3-4 lines: what the
   delivery engine does (fan-out build → Claude review → verify → commit/push →
   EC2 deploy), and where the Task Book and status file live.

3. **Model keys configured** — check (do not print values) which of these env
   vars are set in `.env` / process env, report present/missing only:
   `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` (Gemini),
   `DEEPSEEK_API_KEY`, `NVIDIA_API_KEY` through `NVIDIA_API_KEY_J` (count how
   many of the 10 NIM keys are present), `OPENROUTER_API_KEY`. One line per
   provider: ✅ set / ⚠️ missing.

4. **Task Book progress** — read `docs/architecture/TASKBOOK_STATUS.json`,
   group by phase, show counts (VERIFIED / IN_REVIEW / DRAFT / REJECTED /
   PENDING) per phase, and name the next unblocked PENDING task (deps all
   VERIFIED).

5. **Git state** — current branch, latest commit, ahead/behind origin,
   uncommitted file count (do not list contents, just the count) and whether
   any stash entries exist.

6. **Production health** (best-effort, skip silently if unreachable) —
   `curl -s https://aliyarsolutions.com/health` and `/readyz` status codes.

7. **Available commands** — list the five slash commands Captain can run next:
   `/build-phase <N>`, `/council <question>`, `/readiness`, `/heal`, `/status`.

End with one line: "Ready, Captain." if steps 3-5 all check out, or a one-line
list of what's blocking readiness (e.g. "missing ANTHROPIC_API_KEY", "3
uncommitted files pending review") if not.
