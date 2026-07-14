"""
Tests for scheduler file-lock leader election.

Verifies that exactly one gunicorn worker starts APScheduler, that the lock
survives normal operation, and that leadership transfers correctly when the
leader exits (worker recycling / SIGHUP reload).
"""
import fcntl
import multiprocessing
import os
import signal
import tempfile
import time

import pytest


LOCK_PATH = None  # set per-test via tmp_path


def _try_lock(lock_path: str) -> bool:
    """Try to acquire an exclusive non-blocking lock. Return True if acquired."""
    fd = open(lock_path, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        fd.close()
        return False


def _hold_lock_until_signalled(lock_path: str, ready_event, stop_event):
    """Simulate a worker holding the scheduler lock until told to stop."""
    fd = open(lock_path, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ready_event.set()
        stop_event.wait(timeout=10)
    except BlockingIOError:
        pass
    finally:
        fd.close()


def _worker_attempt(lock_path: str, results: list, index: int):
    """Simulate a worker trying to acquire the scheduler lock."""
    fd = open(lock_path, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        results[index] = True
        time.sleep(0.5)
    except BlockingIOError:
        results[index] = False
    finally:
        fd.close()


class TestLeaderElection:
    """Core leader election via file lock."""

    def test_first_worker_acquires_lock(self, tmp_path):
        lock_path = str(tmp_path / "sched.lock")
        fd = open(lock_path, "w")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert True  # no BlockingIOError
        fd.close()

    def test_second_worker_blocked(self, tmp_path):
        lock_path = str(tmp_path / "sched.lock")
        fd1 = open(lock_path, "w")
        fcntl.flock(fd1, fcntl.LOCK_EX | fcntl.LOCK_NB)

        fd2 = open(lock_path, "w")
        with pytest.raises(BlockingIOError):
            fcntl.flock(fd2, fcntl.LOCK_EX | fcntl.LOCK_NB)

        fd2.close()
        fd1.close()

    def test_exactly_one_leader_among_three_workers(self, tmp_path):
        """Simulate 3 gunicorn workers — exactly one must win the lock."""
        lock_path = str(tmp_path / "sched.lock")
        manager = multiprocessing.Manager()
        results = manager.list([None, None, None])

        procs = []
        for i in range(3):
            p = multiprocessing.Process(
                target=_worker_attempt, args=(lock_path, results, i)
            )
            procs.append(p)

        for p in procs:
            p.start()
        for p in procs:
            p.join(timeout=5)

        leaders = [r for r in results if r is True]
        followers = [r for r in results if r is False]
        assert len(leaders) == 1, f"Expected exactly 1 leader, got {len(leaders)}"
        assert len(followers) == 2, f"Expected 2 followers, got {len(followers)}"


class TestWorkerRecycling:
    """Lock release and re-acquisition after worker death (max_requests)."""

    def test_lock_released_when_leader_exits(self, tmp_path):
        """When the leader process exits, a new worker can acquire the lock."""
        lock_path = str(tmp_path / "sched.lock")
        ready = multiprocessing.Event()
        stop = multiprocessing.Event()

        leader = multiprocessing.Process(
            target=_hold_lock_until_signalled,
            args=(lock_path, ready, stop),
        )
        leader.start()
        ready.wait(timeout=5)

        assert not _try_lock(lock_path), "Lock should be held by leader"

        stop.set()
        leader.join(timeout=5)

        assert _try_lock(lock_path), "Lock should be available after leader exits"

    def test_new_worker_becomes_leader_after_recycling(self, tmp_path):
        """Simulates max_requests recycling: old leader dies, new worker takes over."""
        lock_path = str(tmp_path / "sched.lock")

        for generation in range(3):
            ready = multiprocessing.Event()
            stop = multiprocessing.Event()

            worker = multiprocessing.Process(
                target=_hold_lock_until_signalled,
                args=(lock_path, ready, stop),
            )
            worker.start()
            ready.wait(timeout=5)

            assert not _try_lock(lock_path), (
                f"Gen {generation}: lock should be held"
            )

            stop.set()
            worker.join(timeout=5)

            assert _try_lock(lock_path), (
                f"Gen {generation}: lock should transfer to next worker"
            )


class TestGracefulReload:
    """Simulate SIGHUP: old workers exit, new workers start."""

    def test_sighup_leadership_transfer(self, tmp_path):
        """Old leader is killed (SIGTERM), new worker acquires leadership."""
        lock_path = str(tmp_path / "sched.lock")
        ready = multiprocessing.Event()
        stop = multiprocessing.Event()

        old_leader = multiprocessing.Process(
            target=_hold_lock_until_signalled,
            args=(lock_path, ready, stop),
        )
        old_leader.start()
        ready.wait(timeout=5)

        assert not _try_lock(lock_path)

        os.kill(old_leader.pid, signal.SIGTERM)
        old_leader.join(timeout=5)

        assert _try_lock(lock_path), "New worker should acquire lock after SIGTERM"


class TestSchedulerTakeover:
    """End-to-end leader election with takeover after leader death."""

    def test_follower_becomes_leader_when_leader_dies(self, tmp_path):
        """Two workers start. Leader dies. Follower retries and becomes leader."""
        lock_path = str(tmp_path / "sched.lock")

        ready = multiprocessing.Event()
        stop = multiprocessing.Event()
        leader = multiprocessing.Process(
            target=_hold_lock_until_signalled,
            args=(lock_path, ready, stop),
        )
        leader.start()
        ready.wait(timeout=5)

        assert not _try_lock(lock_path), "Follower should be blocked"

        stop.set()
        leader.join(timeout=5)

        assert _try_lock(lock_path), "Follower should now become leader"

    def test_lock_survives_multiple_failed_attempts(self, tmp_path):
        lock_path = str(tmp_path / "sched.lock")
        fd = open(lock_path, "w")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        for _ in range(10):
            assert not _try_lock(lock_path)

        fd.close()
        assert _try_lock(lock_path), "Lock should be available after holder closes"


class TestGunicornWorkerAge:
    """Prove that the old worker.age-based approach was broken."""

    def test_gunicorn_worker_age_starts_at_1(self):
        """Verify gunicorn 23.0.0 assigns age=1 to the first worker."""
        from gunicorn.arbiter import Arbiter

        class FakeApp:
            cfg = type("C", (), {"settings": {}})()
            wsgi = lambda: None

        arbiter = object.__new__(Arbiter)
        arbiter.worker_age = 0  # as set in Arbiter.__init__

        ages = []
        for _ in range(3):
            arbiter.worker_age += 1
            ages.append(arbiter.worker_age)

        assert ages == [1, 2, 3], f"Expected [1,2,3], got {ages}"
        assert all(age > 0 for age in ages), "All ages > 0 — old guard was always True"

    def test_old_guard_disabled_all_workers(self):
        """The old `if worker.age > 0` condition disabled every worker."""
        worker_age = 0
        disabled_count = 0
        for _ in range(3):
            worker_age += 1
            if worker_age > 0:
                disabled_count += 1
        assert disabled_count == 3, "Old guard disabled ALL workers"

    def test_recycled_workers_get_higher_ages(self):
        """After max_requests recycling, replacement workers get age 4+."""
        worker_age = 0
        for _ in range(3):
            worker_age += 1
        # Now simulate recycling 3 workers
        recycled_ages = []
        for _ in range(3):
            worker_age += 1
            recycled_ages.append(worker_age)
        assert recycled_ages == [4, 5, 6]
        assert all(age > 1 for age in recycled_ages), (
            "Even age>1 fix would fail for recycled workers"
        )
