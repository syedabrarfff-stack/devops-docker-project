"""
JARVIS Relationship Graph — maps connections between leads, clients, partners,
competitors, and influencers. Enables warm introduction path finding.
"""
from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, set_tenant_context

logger = logging.getLogger(__name__)

ENTITY_TYPES = ("LEAD", "CLIENT", "PARTNER", "COMPETITOR", "INFLUENCER")
RELATIONSHIP_TYPES = (
    "REFERRED_BY", "KNOWS", "COMPETITOR_OF", "PARTNER_OF",
    "INFLUENCED_BY", "WORKED_WITH",
)

INTRO_TEMPLATES = {
    1: "Direct introduction: {from_name} knows {to_name} — ideal for a warm intro.",
    2: "{from_name} → {bridge} → {to_name}: A two-hop introduction via {bridge}.",
    3: "{from_name} → ... → {to_name}: A {hops}-hop path exists through your network.",
}


class RelationshipGraph:
    """Manages the relationship network for CRM intelligence."""

    async def add_node(
        self,
        tenant_id: UUID,
        entity_type: str,
        entity_id: str,
        attributes: dict,
    ) -> dict[str, Any]:
        """Create or update a node in the relationship graph."""
        if entity_type not in ENTITY_TYPES:
            raise ValueError(f"entity_type must be one of {ENTITY_TYPES}")

        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, tenant_id)
            node_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            # Upsert node
            await session.execute(
                text(
                    """
                    INSERT INTO relationship_nodes
                      (id, tenant_id, entity_type, entity_id, attributes, created_at, updated_at)
                    VALUES
                      (:id, :tenant_id, :entity_type, :entity_id, :attributes::jsonb, :now, :now)
                    ON CONFLICT (tenant_id, entity_type, entity_id)
                    DO UPDATE SET
                      attributes = :attributes::jsonb,
                      updated_at = :now
                    RETURNING id
                    """
                ),
                {
                    "id": node_id,
                    "tenant_id": str(tenant_id),
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "attributes": json.dumps(attributes),
                    "now": now,
                },
            )
            await session.commit()

            # Fetch actual ID (in case of conflict update)
            row = await session.execute(
                text(
                    """
                    SELECT id FROM relationship_nodes
                    WHERE tenant_id = :tenant_id
                      AND entity_type = :entity_type
                      AND entity_id = :entity_id
                    """
                ),
                {"tenant_id": str(tenant_id), "entity_type": entity_type, "entity_id": entity_id},
            )
            actual_row = row.fetchone()
            actual_id = str(actual_row.id) if actual_row else node_id

        return {
            "id": actual_id,
            "tenant_id": str(tenant_id),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "attributes": attributes,
            "status": "created_or_updated",
        }

    async def add_edge(
        self,
        tenant_id: UUID,
        from_id: str,
        to_id: str,
        relationship_type: str,
        strength: float = 1.0,
    ) -> dict[str, Any]:
        """Add a relationship edge between two nodes."""
        if relationship_type not in RELATIONSHIP_TYPES:
            raise ValueError(f"relationship_type must be one of {RELATIONSHIP_TYPES}")

        strength = max(0.0, min(1.0, strength))
        edge_id = str(uuid.uuid4())

        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, tenant_id)
            now = datetime.now(timezone.utc)

            await session.execute(
                text(
                    """
                    INSERT INTO relationship_edges
                      (id, tenant_id, from_node_id, to_node_id, relationship_type, strength, created_at)
                    VALUES
                      (:id, :tenant_id, :from_id::uuid, :to_id::uuid, :rel_type, :strength, :now)
                    ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "id": edge_id,
                    "tenant_id": str(tenant_id),
                    "from_id": from_id,
                    "to_id": to_id,
                    "rel_type": relationship_type,
                    "strength": strength,
                    "now": now,
                },
            )
            await session.commit()

        return {
            "id": edge_id,
            "from_node_id": from_id,
            "to_node_id": to_id,
            "relationship_type": relationship_type,
            "strength": strength,
            "status": "created",
        }

    async def get_warm_intros(
        self,
        tenant_id: UUID,
        target_lead_id: str,
    ) -> list[dict[str, Any]]:
        """Find shortest paths from existing clients/contacts to target lead node."""
        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, tenant_id)

            # Load all nodes and edges
            nodes_rows = await session.execute(
                text(
                    "SELECT id, entity_type, entity_id, attributes FROM relationship_nodes WHERE tenant_id = :t"
                ),
                {"t": str(tenant_id)},
            )
            nodes = {str(r.id): {"type": r.entity_type, "id": r.entity_id, "attrs": r.attributes or {}} for r in nodes_rows}

            edges_rows = await session.execute(
                text(
                    "SELECT from_node_id, to_node_id, relationship_type, strength FROM relationship_edges WHERE tenant_id = :t"
                ),
                {"t": str(tenant_id)},
            )
            # Build adjacency list (bidirectional)
            adj: dict[str, list[tuple[str, float]]] = defaultdict(list)
            for r in edges_rows:
                adj[str(r.from_node_id)].append((str(r.to_node_id), float(r.strength or 1.0)))
                adj[str(r.to_node_id)].append((str(r.from_node_id), float(r.strength or 1.0)))

        # Find target node by entity_id
        target_node_id = None
        for node_id, node_data in nodes.items():
            if node_data["id"] == target_lead_id:
                target_node_id = node_id
                break

        if not target_node_id:
            return []

        # BFS from each CLIENT node to target
        client_nodes = [nid for nid, nd in nodes.items() if nd["type"] in ("CLIENT", "PARTNER")]
        intro_paths = []

        for start_node_id in client_nodes:
            path = self._bfs_path(start_node_id, target_node_id, adj)
            if path and len(path) <= 4:  # Max 3 hops
                hops = len(path) - 1
                # Calculate path strength (min strength along path)
                path_strength = 1.0
                for i in range(len(path) - 1):
                    neighbors = dict(adj[path[i]])
                    path_strength = min(path_strength, neighbors.get(path[i + 1], 0.5))

                start_name = nodes[start_node_id]["attrs"].get("name", nodes[start_node_id]["id"])
                target_name = nodes[target_node_id]["attrs"].get("name", target_lead_id)

                # Build intro message
                if hops == 1:
                    template = INTRO_TEMPLATES[1]
                    message = template.format(from_name=start_name, to_name=target_name)
                elif hops == 2:
                    bridge_id = path[1]
                    bridge_name = nodes[bridge_id]["attrs"].get("name", "a shared contact")
                    message = INTRO_TEMPLATES[2].format(
                        from_name=start_name, bridge=bridge_name, to_name=target_name
                    )
                else:
                    message = INTRO_TEMPLATES[3].format(
                        from_name=start_name, to_name=target_name, hops=hops
                    )

                path_names = [nodes[p]["attrs"].get("name", nodes[p]["id"]) for p in path]

                intro_paths.append(
                    {
                        "path": path_names,
                        "path_node_ids": path,
                        "hops": hops,
                        "strength": round(path_strength, 2),
                        "intro_message_template": message,
                        "start_entity_type": nodes[start_node_id]["type"],
                    }
                )

        # Sort by fewest hops, then highest strength
        intro_paths.sort(key=lambda x: (x["hops"], -x["strength"]))
        return intro_paths[:10]

    def _bfs_path(
        self,
        start: str,
        end: str,
        adj: dict[str, list[tuple[str, float]]],
    ) -> list[str] | None:
        """BFS to find shortest path between two nodes."""
        if start == end:
            return [start]
        visited = {start}
        queue: deque[list[str]] = deque([[start]])
        while queue:
            path = queue.popleft()
            current = path[-1]
            for neighbor, _ in adj.get(current, []):
                if neighbor == end:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return None

    async def get_graph_summary(self, tenant_id: UUID) -> dict[str, Any]:
        """Return high-level graph statistics."""
        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, tenant_id)

            # Node count
            node_count_row = await session.execute(
                text("SELECT COUNT(*) as cnt FROM relationship_nodes WHERE tenant_id = :t"),
                {"t": str(tenant_id)},
            )
            total_nodes = node_count_row.scalar() or 0

            # Edge count
            edge_count_row = await session.execute(
                text("SELECT COUNT(*) as cnt FROM relationship_edges WHERE tenant_id = :t"),
                {"t": str(tenant_id)},
            )
            total_edges = edge_count_row.scalar() or 0

            # Most connected entities
            connected_rows = await session.execute(
                text(
                    """
                    SELECT n.entity_id, n.entity_type, n.attributes,
                           COUNT(e.id) as edge_count
                    FROM relationship_nodes n
                    LEFT JOIN relationship_edges e
                      ON (e.from_node_id = n.id OR e.to_node_id = n.id)
                    WHERE n.tenant_id = :t
                    GROUP BY n.id, n.entity_id, n.entity_type, n.attributes
                    ORDER BY edge_count DESC
                    LIMIT 5
                    """
                ),
                {"t": str(tenant_id)},
            )
            most_connected = [
                {
                    "entity_id": r.entity_id,
                    "entity_type": r.entity_type,
                    "name": (r.attributes or {}).get("name", r.entity_id),
                    "connections": r.edge_count,
                }
                for r in connected_rows
            ]

            # Warm intro opportunities = LEAD nodes reachable from CLIENT nodes within 3 hops
            lead_nodes_row = await session.execute(
                text(
                    "SELECT COUNT(*) FROM relationship_nodes WHERE tenant_id = :t AND entity_type = 'LEAD'"
                ),
                {"t": str(tenant_id)},
            )
            lead_count = lead_nodes_row.scalar() or 0

            # Network health: ratio of edges to nodes
            health_ratio = (total_edges / total_nodes) if total_nodes > 0 else 0
            network_health_score = min(100, round(health_ratio * 25, 1))

        return {
            "tenant_id": str(tenant_id),
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "most_connected_entities": most_connected,
            "warm_intro_opportunities": lead_count,
            "network_health_score": network_health_score,
            "health_grade": "A" if network_health_score >= 80 else "B" if network_health_score >= 60 else "C" if network_health_score >= 40 else "D",
        }

    async def list_nodes(
        self,
        tenant_id: UUID,
        entity_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List all nodes in the graph."""
        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, tenant_id)
            where = "WHERE tenant_id = :t"
            params: dict = {"t": str(tenant_id), "limit": limit}
            if entity_type:
                where += " AND entity_type = :et"
                params["et"] = entity_type

            rows = await session.execute(
                text(
                    f"SELECT id, entity_type, entity_id, attributes, created_at FROM relationship_nodes {where} ORDER BY created_at DESC LIMIT :limit"
                ),
                params,
            )
            return [
                {
                    "id": str(r.id),
                    "entity_type": r.entity_type,
                    "entity_id": r.entity_id,
                    "name": (r.attributes or {}).get("name", r.entity_id),
                    "attributes": r.attributes or {},
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]


relationship_graph = RelationshipGraph()
