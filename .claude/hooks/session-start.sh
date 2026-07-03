#!/bin/bash
# JARVIS v4 — SessionStart hook
# Loads system state so every new session starts already knowing where things stand.
# Read-only: prints context, never mutates anything.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

echo "═══════════════════════════════════════════════════════════"
echo " JARVIS v4 — Session Context"
echo "═══════════════════════════════════════════════════════════"

if [ -f "$ROOT/JARVIS_SELF_KNOWLEDGE.md" ]; then
  echo "--- JARVIS_SELF_KNOWLEDGE.md (last 40 lines) ---"
  tail -40 "$ROOT/JARVIS_SELF_KNOWLEDGE.md"
fi

if [ -f "$ROOT/docs/architecture/TASKBOOK_STATUS.json" ]; then
  echo "--- Task Book status ---"
  python3 -c "
import json
try:
    d = json.load(open('$ROOT/docs/architecture/TASKBOOK_STATUS.json'))
    counts = {}
    for k, v in d.items():
        s = v.get('status', 'UNKNOWN')
        counts[s] = counts.get(s, 0) + 1
    print(counts)
except Exception as e:
    print('status file unreadable:', e)
" 2>/dev/null || echo "(status file present but unparsable)"
fi

echo "--- Git ---"
git -C "$ROOT" log --oneline -3 2>/dev/null
git -C "$ROOT" status --porcelain 2>/dev/null | head -5

echo "═══════════════════════════════════════════════════════════"
