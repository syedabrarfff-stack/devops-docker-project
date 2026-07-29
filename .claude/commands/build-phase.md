---
description: Run the JARVIS v4 fan-out delivery engine for one Task Book phase
argument-hint: <phase-number: 0|1|2|3|4|5>
---

Execute Task Book phase **$ARGUMENTS** from `docs/architecture/JARVIS_V4_TASKBOOK.md`.

Follow this procedure exactly:

1. **Load context**: Read `docs/architecture/JARVIS_V4_ARCHITECTURE.md`,
   `docs/architecture/JARVIS_V4_TASKBOOK.md`, and
   `docs/architecture/TASKBOOK_STATUS.json` (create the status file with all tasks
   PENDING if it doesn't exist yet).

2. **Select unblocked tasks**: From the requested phase, find every task whose `deps`
   are all VERIFIED (or has no deps). Skip anything already VERIFIED.

3. **Fan out builders**: For each unblocked task, invoke
   `python3 scripts/agent_bridge.py draft <task-id>` — this calls the assigned free
   model (NVIDIA NIM / Gemini / DeepSeek) and writes a draft to `draft/<task-id>/`.
   Run independent tasks in parallel (multiple Agent tool calls in one message).

4. **Review every draft yourself** (Claude is the reviewer for all tasks, no exceptions):
   - Check correctness against the architecture spec
   - Check it doesn't touch anything outside its assigned path
   - Check for security issues (secrets, injection, unsafe deserialization)
   - Run/write unit tests; they must pass
   - APPROVE → integrate into the real path, mark VERIFIED in TASKBOOK_STATUS.json
   - REJECT → note the reason, re-run agent_bridge.py draft for that task with the
     reviewer feedback appended to the prompt

5. **Never skip verification to go faster.** A task is not done until it is VERIFIED,
   not merely drafted.

6. **Commit**: one commit per verified task or logical group, format
   `feat(v4-phase-$ARGUMENTS): <task-id> <short description>`.

7. **Report**: end with a status table — task ID, status, builder used, time taken.
   Do not claim the phase is "done" if any task is not VERIFIED — list what remains.

8. **Do not deploy.** Deployment is a separate, explicitly-approved step per the
   locked engineering workflow (Production Readiness Review required first).
