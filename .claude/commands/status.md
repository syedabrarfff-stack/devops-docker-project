---
description: One-pager — Task Book progress + production health
---

Produce a single concise status report:

1. **Task Book progress**: read `docs/architecture/TASKBOOK_STATUS.json`, group by
   phase, show counts (VERIFIED / IN_REVIEW / DRAFT / REJECTED / PENDING) per phase.
2. **Production health**: `curl -s https://aliyarsolutions.com/health` and `/readyz`
   status codes.
3. **Git state**: current branch, latest commit, ahead/behind origin.
4. **Last self-heal**: most recent entry from `JARVIS_SELF_KNOWLEDGE.md` if present.
5. **Next unblocked task**: the next Task Book item whose dependencies are all
   VERIFIED but which itself is still PENDING.

Keep the whole report under one screen. No speculation — only what was actually checked.
