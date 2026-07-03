#!/usr/bin/env python3
"""
JARVIS v4 — Agent Bridge
━━━━━━━━━━━━━━━━━━━━━━━━
The builder half of the delivery engine described in
docs/architecture/VSCODE_HQ_SETUP.md.

Given a Task Book task ID, this script:
  1. Looks up the task in docs/architecture/JARVIS_V4_TASKBOOK.md
  2. Builds a prompt (architecture context + task spec + existing code style)
  3. Calls the assigned free-tier model (NVIDIA NIM / Gemini / DeepSeek via NIM)
  4. Writes the raw draft to draft/<task-id>/ — NEVER to a real service path
  5. Records the attempt in docs/architecture/TASKBOOK_STATUS.json

Claude (or a human) reviews every draft afterward. This script never integrates
code into the real codebase — that step is a deliberate, separate, reviewed action.

Usage:
    python3 scripts/agent_bridge.py draft K1-2
    python3 scripts/agent_bridge.py status
"""

import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCH_DOC = ROOT / "docs" / "architecture" / "JARVIS_V4_ARCHITECTURE.md"
TASKBOOK = ROOT / "docs" / "architecture" / "JARVIS_V4_TASKBOOK.md"
STATUS_FILE = ROOT / "docs" / "architecture" / "TASKBOOK_STATUS.json"
DRAFT_DIR = ROOT / "draft"

# Builder model -> NVIDIA NIM model id (all NIM builders share the rotating key pool)
NIM_MODEL_MAP = {
    "NIM": "meta/llama-4-maverick-17b-128e-instruct",
    "DeepSeek": "deepseek-ai/deepseek-v3",
    "Qwen": "qwen/qwen2.5-coder-32b-instruct",
}

NIM_KEY_ENV_VARS = [
    "NVIDIA_API_KEY", "NVIDIA_API_KEY_B", "NVIDIA_API_KEY_C", "NVIDIA_API_KEY_D",
    "NVIDIA_API_KEY_E", "NVIDIA_API_KEY_F", "NVIDIA_API_KEY_G", "NVIDIA_API_KEY_H",
    "NVIDIA_API_KEY_I", "NVIDIA_API_KEY_J",
]


def load_status():
    if STATUS_FILE.exists():
        return json.loads(STATUS_FILE.read_text())
    return {}


def save_status(status):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(status, indent=2, sort_keys=True))


def parse_taskbook_row(task_id):
    """Extract one task's row from the markdown table in JARVIS_V4_TASKBOOK.md."""
    if not TASKBOOK.exists():
        raise FileNotFoundError(f"Task Book not found at {TASKBOOK}")
    text = TASKBOOK.read_text()
    for line in text.splitlines():
        if line.strip().startswith(f"| {task_id} "):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            return cells
    raise ValueError(f"Task {task_id} not found in Task Book")


def next_nim_key():
    """Rotate across the 10 NVIDIA NIM keys to spread load."""
    for var in NIM_KEY_ENV_VARS:
        val = os.getenv(var, "")
        if val and not val.startswith("test"):
            return val
    return None


def build_prompt(task_id, row_cells):
    arch_excerpt = ""
    if ARCH_DOC.exists():
        arch_excerpt = ARCH_DOC.read_text()[:6000]  # keep prompt bounded

    task_desc = " | ".join(row_cells)
    return f"""You are a builder agent in the JARVIS v4 delivery pipeline.
Your draft will be REVIEWED by Claude before anything merges — write clean,
correct, well-tested code and do not guess at things you're unsure of; note
assumptions explicitly instead.

ARCHITECTURE CONTEXT (excerpt):
{arch_excerpt}

TASK: {task_id}
TASK ROW: {task_desc}

Produce ONLY the code for this task's output path. Include a short header
comment naming the task ID. Do not modify any file outside your assigned output
path. If the task requires a test file, include it as a separate clearly-marked
section.
"""


def call_nim(prompt, model_id):
    import urllib.request

    key = next_nim_key()
    if not key:
        raise RuntimeError("No usable NVIDIA NIM key found in environment")

    payload = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 4096,
    }).encode()

    req = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def call_gemini(prompt):
    import urllib.request

    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    if not key or key.startswith("test"):
        raise RuntimeError("No usable Gemini API key found in environment")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={key}"
    )
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]


def draft_task(task_id):
    row = parse_taskbook_row(task_id)
    # Column layout: | ID(0) | Task(1) | Output(2) | builder(3) | reviewer(4) | deps(5) | est(6)
    # Phase 0 rows have no builder/reviewer columns (Claude-only, sequential) — layout is
    # | ID(0) | Task(1) | Output(2) | deps(3) | est(4) |, so guard on column count.
    builder = row[3] if len(row) > 6 else "Claude"
    prompt = build_prompt(task_id, row)

    status = load_status()
    prior = status.get(task_id, {})
    entry = {
        "reviewer": prior.get("reviewer", "Claude"),
        "deps": prior.get("deps", ""),
        "status": "IN_PROGRESS",
        "builder": builder,
        "started_at": time.time(),
    }
    status[task_id] = entry
    save_status(status)

    try:
        if builder in ("NIM", "DeepSeek", "Qwen"):
            content = call_nim(prompt, NIM_MODEL_MAP.get(builder, NIM_MODEL_MAP["NIM"]))
        elif builder == "Gemini":
            content = call_gemini(prompt)
        else:
            raise ValueError(f"Unknown builder '{builder}' for task {task_id}")

        out_dir = DRAFT_DIR / task_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "draft.txt"
        out_file.write_text(content)

        entry["status"] = "DRAFT"
        entry["draft_path"] = str(out_file.relative_to(ROOT))
        entry["completed_at"] = time.time()
        status[task_id] = entry
        save_status(status)

        print(f"[OK] {task_id} drafted by {builder} -> {out_file.relative_to(ROOT)}")
        print("Reviewer note: Claude must review this draft before it is integrated.")

    except Exception as exc:
        entry["status"] = "FAILED"
        entry["error"] = str(exc)
        status[task_id] = entry
        save_status(status)
        print(f"[FAIL] {task_id}: {exc}", file=sys.stderr)
        sys.exit(1)


def show_status():
    status = load_status()
    if not status:
        print("No tasks drafted yet.")
        return
    counts = {}
    for v in status.values():
        s = v.get("status", "UNKNOWN")
        counts[s] = counts.get(s, 0) + 1
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "draft" and len(sys.argv) >= 3:
        draft_task(sys.argv[2])
    elif cmd == "status":
        show_status()
    else:
        print(__doc__)
        sys.exit(1)
