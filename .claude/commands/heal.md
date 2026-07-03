---
description: Health check → diagnose → fix → verify cycle (the scheduled self-heal, runnable on demand)
---

Run one self-heal cycle:

1. **Detect**: check `https://aliyarsolutions.com/health`, `/readyz`, docker container
   status, and recent backend logs for errors.
2. **Analyze**: if anything is unhealthy, identify root cause with evidence (log lines,
   error codes, timestamps).
3. **Plan**: per the Authority Matrix — AUTO-tier issues (bugs, perf, additive fixes)
   get a fix plan now; ASK-tier issues get flagged to Captain instead of auto-fixed.
4. **Implement** (AUTO-tier only): make the fix.
5. **Test**: run relevant tests / rebuild affected service locally if possible.
6. **Verify**: redeploy if needed, confirm health checks pass post-fix.
7. **Report**: "Verified: [what was checked, what was found, what was fixed, evidence]."
   If nothing was wrong: "Verified: all systems healthy. [timestamp, checks run]."
   Never say "Fixed" without the verification evidence attached.
8. Update `JARVIS_SELF_KNOWLEDGE.md` with anything learned this cycle.
