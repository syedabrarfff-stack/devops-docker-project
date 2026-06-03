"""
JARVIS GitHub Bridge — Local repo data bridge for EC2 deployment.

Reads from the local GitHub repo clone on EC2.
JARVIS is deployed on EC2 alongside the git repo clone at:
  /home/ubuntu/jarvis_sales_pipeline/

Reads structured JSON/MD files from /jarvis-data/ and writes JARVIS output
back to /jarvis-data/outputs/ for Claude to consume.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Override via JARVIS_REPO_DATA_PATH environment variable for testing
_DEFAULT_REPO_DATA_PATH = "/home/ubuntu/jarvis_sales_pipeline/jarvis-data"


class GitHubBridge:
    """
    Reads from the local GitHub repo clone on EC2.
    JARVIS is deployed on EC2 alongside the git repo clone.
    Reads /jarvis-data/ from the repo directory.
    """

    @property
    def REPO_DATA_PATH(self) -> str:
        return os.getenv("JARVIS_REPO_DATA_PATH", _DEFAULT_REPO_DATA_PATH)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def read_daily_package(self, date_str: str | None = None) -> dict:
        """
        Reads all JSON files from /jarvis-data/daily/YYYY-MM-DD/
        Returns: {leads: [...], sequences: [...], decks: [...],
                  market_report: {...}, metadata: {...}}
        """
        effective_date = date_str or self.get_latest_date_folder()
        if not effective_date:
            logger.warning("[GitHubBridge] No date folder found in %s/daily/", self.REPO_DATA_PATH)
            return {}

        daily_path = Path(self.REPO_DATA_PATH) / "daily" / effective_date
        if not daily_path.exists():
            logger.warning("[GitHubBridge] Daily folder not found: %s", daily_path)
            return {}

        package: dict[str, Any] = {
            "date": effective_date,
            "leads": [],
            "sequences": [],
            "decks": [],
            "invoices": [],
            "calendar": [],
            "market_report": {},
            "metadata": {"source_path": str(daily_path)},
        }

        file_map = {
            "leads.json": "leads",
            "sequences.json": "sequences",
            "decks.json": "decks",
            "invoices.json": "invoices",
            "calendar.json": "calendar",
            "market_report.json": "market_report",
        }

        for filename, key in file_map.items():
            file_path = daily_path / filename
            if not file_path.exists():
                logger.debug("[GitHubBridge] File not found (skipping): %s", file_path)
                continue

            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                package[key] = data
                logger.info("[GitHubBridge] Loaded %s: %s records", filename,
                            len(data) if isinstance(data, list) else "object")
            except json.JSONDecodeError as exc:
                logger.error("[GitHubBridge] JSON parse error in %s: %s", file_path, exc)
            except OSError as exc:
                logger.error("[GitHubBridge] Read error for %s: %s", file_path, exc)

        return package

    async def read_intelligence_package(self) -> dict:
        """
        Reads latest files from /jarvis-data/intelligence/
        Returns all markdown reports and JSON files as dict keyed by filename.
        """
        intel_path = Path(self.REPO_DATA_PATH) / "intelligence"
        if not intel_path.exists():
            logger.debug("[GitHubBridge] Intelligence directory not found: %s", intel_path)
            return {}

        package: dict[str, Any] = {}

        for file_path in sorted(intel_path.iterdir()):
            if file_path.name.startswith(".") or file_path.is_dir():
                continue

            try:
                if file_path.suffix == ".json":
                    content = json.loads(file_path.read_text(encoding="utf-8"))
                elif file_path.suffix in (".md", ".txt"):
                    content = file_path.read_text(encoding="utf-8")
                else:
                    continue

                package[file_path.name] = content
                logger.info("[GitHubBridge] Loaded intelligence file: %s", file_path.name)

            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("[GitHubBridge] Could not read intelligence file %s: %s", file_path.name, exc)

        return package

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def write_jarvis_output(self, output_type: str, data: dict, date_str: str | None = None) -> str:
        """
        Writes JARVIS processing results back to /jarvis-data/outputs/
        So Claude can read what JARVIS did with the data.
        output_type: 'leads_processed' | 'outreach_sent' | 'proposals_generated' | 'deals_closed'
        Returns: file_path written.
        """
        effective_date = date_str or date.today().isoformat()
        output_path = Path(self.REPO_DATA_PATH) / "outputs"

        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("[GitHubBridge] Cannot create outputs directory: %s", exc)
            return ""

        filename = f"{output_type}_{effective_date}.json"
        file_path = output_path / filename

        try:
            output_data = {
                "output_type": output_type,
                "date": effective_date,
                "written_at": datetime.now(UTC).isoformat(),
                "data": data,
            }
            file_path.write_text(
                json.dumps(output_data, indent=2, default=str, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info("[GitHubBridge] Written output: %s", file_path)
            return str(file_path)
        except OSError as exc:
            logger.error("[GitHubBridge] Write error for %s: %s", file_path, exc)
            return ""

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def get_latest_date_folder(self) -> str | None:
        """
        Scans /jarvis-data/daily/ and returns the most recent date folder.
        Returns: YYYY-MM-DD string or None if empty.
        """
        daily_path = Path(self.REPO_DATA_PATH) / "daily"
        if not daily_path.exists():
            return None

        date_folders = []
        for item in daily_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                # Validate it looks like a date
                try:
                    date.fromisoformat(item.name)
                    date_folders.append(item.name)
                except ValueError:
                    continue

        if not date_folders:
            return None

        return sorted(date_folders)[-1]

    def get_all_date_folders(self) -> list[str]:
        """Returns all available date folders, sorted ascending."""
        daily_path = Path(self.REPO_DATA_PATH) / "daily"
        if not daily_path.exists():
            return []

        folders = []
        for item in daily_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                try:
                    date.fromisoformat(item.name)
                    folders.append(item.name)
                except ValueError:
                    continue

        return sorted(folders)

    def get_outputs_for_date(self, date_str: str) -> dict:
        """Read all JARVIS output files for a given date."""
        outputs_path = Path(self.REPO_DATA_PATH) / "outputs"
        if not outputs_path.exists():
            return {}

        results = {}
        for file_path in outputs_path.iterdir():
            if date_str in file_path.name and file_path.suffix == ".json":
                try:
                    results[file_path.stem] = json.loads(file_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue

        return results

    def health_check(self) -> dict:
        """Return bridge health status."""
        repo_path = Path(self.REPO_DATA_PATH)
        daily_path = repo_path / "daily"
        intel_path = repo_path / "intelligence"
        outputs_path = repo_path / "outputs"

        return {
            "repo_data_path": self.REPO_DATA_PATH,
            "repo_exists": repo_path.exists(),
            "daily_exists": daily_path.exists(),
            "intelligence_exists": intel_path.exists(),
            "outputs_exists": outputs_path.exists(),
            "latest_date_folder": self.get_latest_date_folder(),
            "available_dates": self.get_all_date_folders(),
        }


github_bridge = GitHubBridge()
