#!/usr/bin/env python3
"""
JARVIS Council — Session Viewer
Browse and search past council sessions from the terminal.
Usage:
  python sessions_viewer.py           # list recent sessions
  python sessions_viewer.py 3         # read session #3
  python sessions_viewer.py pricing   # search by keyword
"""

import os
import sys

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(SCRIPT_DIR, "sessions")

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    G = Fore.GREEN; Y = Fore.YELLOW; C = Fore.CYAN
    W = Fore.WHITE; B = Style.BRIGHT; RS = Style.RESET_ALL
except ImportError:
    G = Y = C = W = B = RS = ""


def list_sessions() -> list[dict]:
    if not os.path.exists(SESSIONS_DIR):
        return []
    sessions = []
    for fname in sorted(os.listdir(SESSIONS_DIR), reverse=True):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(SESSIONS_DIR, fname)
        task_line = date_line = active_line = ""
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("Task   :") or line.startswith("Task:"):
                        task_line = line.split(":", 1)[1].strip()
                    if line.startswith("Date   :") or line.startswith("Date:"):
                        date_line = line.split(":", 1)[1].strip()
                    if line.startswith("Active:") or line.startswith("Council:"):
                        active_line = line.split(":", 1)[1].strip()
                    if task_line and date_line:
                        break
        except Exception:
            pass
        sessions.append({
            "file":   fname,
            "path":   path,
            "task":   task_line or fname,
            "date":   date_line,
            "active": active_line,
        })
    return sessions


def read_verdict(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        content = f.read()
    start = content.find("COUNCIL VERDICT\n")
    if start == -1:
        start = content.find("VERDICT\n=")
    end = content.find("INDIVIDUAL MEMBER RESPONSES", start)
    if start == -1:
        return content
    return content[start:end if end != -1 else len(content)].strip()


def print_list(sessions: list[dict]):
    print(f"\n{B}{C}{'═'*65}{RS}")
    print(f"{B}{C}   JARVIS Council — Session History ({len(sessions)} sessions){RS}")
    print(f"{C}{'═'*65}{RS}\n")
    if not sessions:
        print(f"  {Y}No sessions found. Run council.py first.{RS}\n")
        return
    for i, s in enumerate(sessions, 1):
        date = s["date"][:19] if s["date"] else "unknown date"
        task = s["task"][:58] + ("..." if len(s["task"]) > 58 else "")
        src  = " [telegram]" if s["file"].startswith("telegram_") else ""
        print(f"  {B}{i:>2}.{RS}  {C}{date}{RS}{Y}{src}{RS}")
        print(f"       {W}{task}{RS}")
        if s["active"]:
            print(f"       {G}({s['active']}){RS}")
        print()
    print(f"  {Y}Usage: python sessions_viewer.py <number>   — read a session{RS}")
    print(f"  {Y}       python sessions_viewer.py <keyword>  — search sessions{RS}\n")


def print_session(s: dict):
    verdict = read_verdict(s["path"])
    print(f"\n{B}{C}{'═'*65}{RS}")
    print(f"{B}{C}   Session: {s['date']}{RS}")
    print(f"{C}   Task: {s['task']}{RS}")
    if s["active"]:
        print(f"{G}   {s['active']}{RS}")
    print(f"{C}{'═'*65}{RS}\n")
    for line in verdict.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            print(f"\n{B}{C}{line}{RS}")
        elif stripped.startswith("- ") or stripped.startswith("• "):
            print(f"{W}{line}{RS}")
        elif stripped and stripped[0].isdigit() and len(stripped) > 2 and stripped[1] in ".)":
            print(f"{Y}{line}{RS}")
        else:
            print(f"{W}{line}{RS}")
    print(f"\n{C}{'═'*65}{RS}")
    print(f"{Y}  File: {s['file']}{RS}\n")


def search_sessions(keyword: str, sessions: list[dict]):
    kw = keyword.lower()
    matches = []
    for s in sessions:
        if kw in s["task"].lower():
            matches.append(s)
            continue
        # Also search inside the file
        try:
            with open(s["path"], encoding="utf-8") as f:
                if kw in f.read().lower():
                    matches.append(s)
        except Exception:
            pass

    print(f"\n{B}{C}  Search: '{keyword}' — {len(matches)} result(s){RS}\n")
    if not matches:
        print(f"  {Y}No sessions found matching '{keyword}'{RS}\n")
        return
    for i, s in enumerate(matches, 1):
        date = s["date"][:19] if s["date"] else "unknown"
        task = s["task"][:58] + ("..." if len(s["task"]) > 58 else "")
        print(f"  {B}{i:>2}.{RS}  {C}{date}{RS}  {W}{task}{RS}")
    print(f"\n  {Y}Run: python sessions_viewer.py <number> to read a result{RS}\n")


def main():
    sessions = list_sessions()
    arg = sys.argv[1] if len(sys.argv) > 1 else ""

    if not arg:
        print_list(sessions[:20])
        return

    # Numeric argument → read that session
    if arg.isdigit():
        n = int(arg)
        if 1 <= n <= len(sessions):
            print_session(sessions[n - 1])
        else:
            print(f"\n  {Y}Session #{n} not found. There are {len(sessions)} sessions.{RS}\n")
        return

    # Text argument → search
    search_sessions(arg, sessions)


if __name__ == "__main__":
    main()
