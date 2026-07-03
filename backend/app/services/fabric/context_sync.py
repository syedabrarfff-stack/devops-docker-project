"""F3-5: Context Sync — immutable Executive Memory snapshot for AI Fabric tasks.

Provides three guarantees for every multi-model reasoning task:
  1. Snapshot  — atomic read of all MemoryEntry rows, frozen into a dict keyed
                 by (layer, key).  All models in a Council session receive the
                 *same* snapshot, preventing split-brain reasoning.
  2. Lock      — cooperative advisory lock on a snapshot ID.  The Council
                 reasoner holds the lock while models run in parallel; competing
                 writes to memory are deferred until unlock.
  3. Merge     — versioned write-back after reasoning completes.  Each updated
                 entry is matched against the version captured at snapshot time.
                 A concurrent modification (version mismatch) raises
                 ContextMergeConflict — the caller decides to retry or discard.

Design notes:
  - Snapshots are transient in-process structures.  No extra DB table is
    created — the authoritative store is `memory_entries`.
  - Locks are asyncio-local and advisory.  They prevent *our own* concurrent
    tasks from trampling each other; external processes can still write.
  - Singleton `get_context_sync()` returns the module-level instance so all
    parts of the codebase share the same lock registry.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kernel import MemoryEntry

log = logging.getLogger(__name__)

VALID_LAYERS = frozenset(
    {"strategic", "operational", "technical", "customer", "financial"}
)


class ContextMergeConflict(Exception):
    """Raised when a memory entry was modified between snapshot and merge."""


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class MemoryItem:
    layer: str
    key: str
    value: dict
    confidence_score: Optional[float]
    version: int
    owner: str


@dataclass
class MemorySnapshot:
    """Frozen view of Executive Memory at a point in time.

    Attributes:
        snapshot_id: unique ID for this snapshot instance.
        task_id:     the reasoning task that requested the snapshot.
        entries:     dict of (layer, key) → MemoryItem at capture time.
        captured_at: UTC timestamp of the snapshot.
        locked:      True while the Council hold the advisory lock.
        lock_holder: identity string of the current lock holder.
    """
    snapshot_id: str
    task_id: str
    entries: dict[tuple[str, str], MemoryItem]
    captured_at: datetime
    locked: bool = False
    lock_holder: Optional[str] = None


# ── Core service ───────────────────────────────────────────────────────────────

class ContextSync:
    """Manages Executive Memory snapshots for AI Fabric reasoning tasks.

    Usage::

        sync = get_context_sync()

        # 1. Capture a snapshot before any model is called
        snap = await sync.snapshot("task-abc", session)

        # 2. Lock it while models reason in parallel
        await sync.lock(snap.snapshot_id, holder="council_reasoner")

        # 3. … models read snap.entries (read-only) …

        # 4. Merge updates back to DB, unlock automatically
        await sync.merge(snap.snapshot_id, updates, holder="council_reasoner", session)
    """

    def __init__(self) -> None:
        self._snapshots: dict[str, MemorySnapshot] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    # ── Snapshot ───────────────────────────────────────────────────────────────

    async def snapshot(self, task_id: str, session: AsyncSession) -> MemorySnapshot:
        """Read all MemoryEntry rows and return a frozen snapshot.

        Args:
            task_id: caller-supplied identifier (decision ID, task queue ID, …).
            session: live DB session — must be active.

        Returns:
            MemorySnapshot with all memory entries at this instant.
        """
        result = await session.execute(select(MemoryEntry))
        rows = result.scalars().all()

        entries: dict[tuple[str, str], MemoryItem] = {}
        for row in rows:
            entries[(row.layer, row.key)] = MemoryItem(
                layer=row.layer,
                key=row.key,
                value=dict(row.value) if row.value else {},
                confidence_score=float(row.confidence_score) if row.confidence_score is not None else None,
                version=row.version,
                owner=row.owner,
            )

        snap = MemorySnapshot(
            snapshot_id=str(uuid.uuid4()),
            task_id=task_id,
            entries=entries,
            captured_at=datetime.now(tz=timezone.utc),
        )
        self._snapshots[snap.snapshot_id] = snap
        self._locks[snap.snapshot_id] = asyncio.Lock()
        log.debug("snapshot %s captured — %d entries for task %s",
                  snap.snapshot_id, len(entries), task_id)
        return snap

    # ── Lock ──────────────────────────────────────────────────────────────────

    async def lock(self, snapshot_id: str, holder: str) -> bool:
        """Acquire the advisory lock on a snapshot.

        Args:
            snapshot_id: ID returned by :meth:`snapshot`.
            holder:      string identity of the caller (used for diagnostics).

        Returns:
            True on success.

        Raises:
            KeyError:      snapshot_id is unknown.
            RuntimeError:  already locked by a different holder.
        """
        snap = self._snapshots.get(snapshot_id)
        if snap is None:
            raise KeyError(f"Unknown snapshot: {snapshot_id}")

        lock = self._locks[snapshot_id]
        acquired = lock.locked()
        if acquired:
            raise RuntimeError(
                f"Snapshot {snapshot_id} is already locked by '{snap.lock_holder}'"
            )

        await lock.acquire()
        snap.locked = True
        snap.lock_holder = holder
        log.debug("snapshot %s locked by %s", snapshot_id, holder)
        return True

    async def unlock(self, snapshot_id: str, holder: str) -> bool:
        """Release the advisory lock on a snapshot.

        Args:
            snapshot_id: ID returned by :meth:`snapshot`.
            holder:      must match the holder who acquired the lock.

        Returns:
            True on success, False if the snapshot is not locked.
        """
        snap = self._snapshots.get(snapshot_id)
        if snap is None:
            raise KeyError(f"Unknown snapshot: {snapshot_id}")

        if not snap.locked:
            return False

        if snap.lock_holder != holder:
            raise RuntimeError(
                f"Cannot unlock snapshot {snapshot_id}: "
                f"locked by '{snap.lock_holder}', not '{holder}'"
            )

        lock = self._locks[snapshot_id]
        lock.release()
        snap.locked = False
        snap.lock_holder = None
        log.debug("snapshot %s unlocked by %s", snapshot_id, holder)
        return True

    # ── Merge ─────────────────────────────────────────────────────────────────

    async def merge(
        self,
        snapshot_id: str,
        updates: dict[tuple[str, str], Any],
        holder: str,
        session: AsyncSession,
    ) -> int:
        """Write reasoning outcomes back to `memory_entries` with OCC.

        For each (layer, key) in *updates*:
        - If the row's current DB version == the captured snapshot version →
          update value + increment version.
        - If version mismatches → raise ContextMergeConflict (partial writes
          already committed are NOT rolled back; caller must handle).

        After all updates the lock is released.

        Args:
            snapshot_id: ID of the locked snapshot.
            updates:     dict of (layer, key) → new_value dict.
            holder:      must match the lock holder.
            session:     active DB session.

        Returns:
            Number of rows successfully updated.

        Raises:
            KeyError:             unknown snapshot_id.
            ContextMergeConflict: OCC conflict on one or more entries.
        """
        snap = self._snapshots.get(snapshot_id)
        if snap is None:
            raise KeyError(f"Unknown snapshot: {snapshot_id}")

        conflicts: list[str] = []
        updated_count = 0

        for (layer, key), new_value in updates.items():
            captured = snap.entries.get((layer, key))
            expected_version = captured.version if captured else 0

            # Attempt OCC update: only succeeds when DB version == expected.
            stmt = (
                update(MemoryEntry)
                .where(
                    MemoryEntry.layer == layer,
                    MemoryEntry.key == key,
                    MemoryEntry.version == expected_version,
                )
                .values(value=new_value, version=expected_version + 1)
            )
            result = await session.execute(stmt)

            if result.rowcount == 0:
                # Version mismatch or row missing — conflict.
                conflicts.append(f"{layer}/{key}")
                log.warning(
                    "merge conflict on %s/%s (expected version %d)",
                    layer, key, expected_version,
                )
            else:
                updated_count += 1
                log.debug("merged %s/%s → version %d", layer, key, expected_version + 1)

        await session.commit()

        # Always release the lock, even on conflict.
        try:
            await self.unlock(snapshot_id, holder)
        except (KeyError, RuntimeError):
            pass

        if conflicts:
            raise ContextMergeConflict(
                f"OCC conflicts on {len(conflicts)} entries: {', '.join(conflicts)}"
            )

        log.info(
            "merge complete — %d entries written for snapshot %s",
            updated_count, snapshot_id,
        )
        return updated_count

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def discard(self, snapshot_id: str) -> None:
        """Remove a snapshot from the in-process registry (does not touch DB).

        Call this after merge or when a task is cancelled to free memory.
        """
        self._snapshots.pop(snapshot_id, None)
        self._locks.pop(snapshot_id, None)

    def get_snapshot(self, snapshot_id: str) -> Optional[MemorySnapshot]:
        """Return a snapshot by ID or None if not found / already discarded."""
        return self._snapshots.get(snapshot_id)

    def active_count(self) -> int:
        """Number of snapshots currently tracked in-process."""
        return len(self._snapshots)


# ── Singleton ─────────────────────────────────────────────────────────────────

_context_sync: Optional[ContextSync] = None


def get_context_sync() -> ContextSync:
    """Return the module-level ContextSync singleton (created on first call)."""
    global _context_sync
    if _context_sync is None:
        _context_sync = ContextSync()
    return _context_sync
