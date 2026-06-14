"""
Knowledge store — thin adapter used by ConnectorHub and other services
to persist intelligence entries into the JARVIS knowledge base.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


class KnowledgeStore:
    """Adapter that persists knowledge entries from ConnectorHub ingestion."""

    async def upsert(
        self,
        *,
        title: str,
        content: str,
        category: str = "general",
        source: str = "connector_hub",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Persist a knowledge entry. Returns True on success."""
        try:
            from app.core.database import AsyncSessionLocal
            from app.services.knowledge.manager import add_knowledge
            async with AsyncSessionLocal() as db:
                await add_knowledge(
                    db,
                    title=title,
                    content=content,
                    category=category,
                    source=source,
                )
            logger.debug("Knowledge stored: [%s] %s", category, title[:60])
            return True
        except Exception as e:
            logger.warning("Knowledge store upsert failed: %s", e)
            return False


knowledge_store = KnowledgeStore()
