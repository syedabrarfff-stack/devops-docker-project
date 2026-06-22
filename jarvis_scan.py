#!/usr/bin/env python3
"""
JARVIS — Captain's HQ Scanner
Scans the entire laptop and builds JARVIS's complete awareness map.
Run this once on your machine. It generates CAPTAIN_HQ.md automatically.
Usage: python jarvis_scan.py
"""

import os, sys, json, subprocess
from datetime import datetime
from pathlib import Path

print("\n╔══════════════════════════════════════════════════════╗")
print("║     JARVIS — CAPTAIN HQ FULL SCAN                   ║")
print("║     Building complete operational awareness...       ║")
print("╚══════════════════════════════════════════════════════╝\n")

HOME = Path.home()
OUTPUT = Path(__file__).parent / "CAPTAIN_HQ.md"

SCAN_ROOTS = [
    HOME / "Desktop",
    HOME / "Documents",
    HOME / "Downloads",
    HOME / ".continue",
    HOME / "OneDrive",
    HOME / "Projects",
    HOME / "Dev",
    HOME / "Code",
    HOME / "GitHub",
    HOME / "repos",
    Path("C:/Projects"),
    Path("C:/Dev"),
    Path("C:/Code"),
    Path("C:/GitHub"),
]

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    ".next", "dist", "build", ".cache", "vendor", "bower_components",
    "target", ".idea", ".vscode", "coverage", ".pytest_cache",
    "AppData", "Application Data", "$RECYCLE.BIN", "Windows",
    "Program Files", "Program Files (x86)", "ProgramData",
}

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css",
    ".json", ".yaml", ".yml", ".env", ".sh", ".bat", ".ps1",
    ".tf", ".sql", ".md", ".txt", ".toml", ".ini", ".cfg"
}

lines = []
lines.append("# CAPTAIN HQ — JARVIS Operational Awareness Map")
lines.append(f"## Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
lines.append(f"## Machine: {os.environ.get('COMPUTERNAME', os.uname().nodename if hasattr(os, 'uname') else 'Unknown')}")
lines.append(f"## User: {os.environ.get('USERNAME', os.environ.get('USER', 'Unknown'))}")
lines.append("")

# ── Git repos ──────────────────────────────────────────────────────────────
print("  Scanning for git repositories...")
lines.append("---")
lines.append("## GIT REPOSITORIES ON THIS MACHINE")
lines.append("")

git_repos = []
for root_path in SCAN_ROOTS:
    if not root_path.exists():
        continue
    try:
        for dirpath, dirnames, _ in os.walk(str(root_path)):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if ".git" in os.listdir(dirpath):
                git_repos.append(Path(dirpath))
                dirnames.clear()
    except PermissionError:
        pass

for repo in sorted(git_repos):
    lines.append(f"### {repo.name}")
    lines.append(f"- **Path:** `{repo}`")
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=str(repo), stderr=subprocess.DEVNULL, text=True
        ).strip()
        lines.append(f"- **Branch:** `{branch}`")
    except Exception:
        pass
    try:
        remotes = subprocess.check_output(
            ["git", "remote", "-v"],
            cwd=str(repo), stderr=subprocess.DEVNULL, text=True
        ).strip().split("\n")
        for r in remotes[:2]:
            if r:
                lines.append(f"- **Remote:** `{r}`")
    except Exception:
        pass
    try:
        last_commit = subprocess.check_output(
            ["git", "log", "-1", "--pretty=format:%s (%cr)"],
            cwd=str(repo), stderr=subprocess.DEVNULL, text=True
        ).strip()
        lines.append(f"- **Last commit:** {last_commit}")
    except Exception:
        pass
    lines.append("")

print(f"  Found {len(git_repos)} git repositories")

# ── Project inventory ───────────────────────────────────────────────────────
print("  Building project inventory...")
lines.append("---")
lines.append("## PROJECT & FOLDER INVENTORY")
lines.append("")

for root_path in SCAN_ROOTS:
    if not root_path.exists():
        continue
    lines.append(f"### {root_path}")
    try:
        entries = sorted(root_path.iterdir())
        for entry in entries:
            if entry.name in SKIP_DIRS or entry.name.startswith("."):
                continue
            if entry.is_dir():
                lines.append(f"- 📁 `{entry.name}/`")
            else:
                lines.append(f"- 📄 `{entry.name}`")
    except PermissionError:
        lines.append("- (permission denied)")
    lines.append("")

# ── VS Code workspaces ──────────────────────────────────────────────────────
print("  Scanning VS Code recent workspaces...")
lines.append("---")
lines.append("## VS CODE RECENT WORKSPACES")
lines.append("")

vscode_storage = HOME / "AppData" / "Roaming" / "Code" / "User" / "globalStorage" / "storage.json"
if vscode_storage.exists():
    try:
        data = json.loads(vscode_storage.read_text(encoding="utf-8", errors="ignore"))
        recently_opened = data.get("openedPathsList", {}).get("workspaces3", [])
        for ws in recently_opened[:20]:
            lines.append(f"- `{ws}`")
    except Exception:
        lines.append("- (could not read VS Code storage)")
else:
    lines.append("- VS Code storage not found at default path")
lines.append("")

# ── Environment variables (safe ones) ──────────────────────────────────────
print("  Capturing environment summary...")
lines.append("---")
lines.append("## ENVIRONMENT SUMMARY")
lines.append("")
safe_vars = ["COMPUTERNAME", "USERNAME", "OS", "PROCESSOR_ARCHITECTURE",
             "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP"]
for var in safe_vars:
    val = os.environ.get(var, "")
    if val:
        lines.append(f"- **{var}:** `{val}`")
lines.append("")

# ── Python packages ─────────────────────────────────────────────────────────
print("  Listing installed Python packages...")
lines.append("---")
lines.append("## INSTALLED PYTHON PACKAGES")
lines.append("")
try:
    pkgs = subprocess.check_output(
        [sys.executable, "-m", "pip", "list", "--format=columns"],
        stderr=subprocess.DEVNULL, text=True
    ).strip()
    lines.append("```")
    lines.append(pkgs)
    lines.append("```")
except Exception:
    lines.append("- (could not retrieve)")
lines.append("")

# ── Write output ─────────────────────────────────────────────────────────────
OUTPUT.write_text("\n".join(lines), encoding="utf-8")

print(f"\n╔══════════════════════════════════════════════════════╗")
print(f"║  ✅  SCAN COMPLETE                                   ║")
print(f"║  📄  Saved to: CAPTAIN_HQ.md                        ║")
print(f"║  🔍  {len(git_repos)} git repos found                          ║")
print(f"╚══════════════════════════════════════════════════════╝")
print(f"\n  Now run:")
print(f"    git add CAPTAIN_HQ.md")
print(f"    git commit -m \"chore: captain hq scan\"")
print(f"    git push\n")
