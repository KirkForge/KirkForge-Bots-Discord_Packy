"""
services.scheduler — Robust thread-safe scheduler for Packy.

Features:
- Thread-safe queued scheduler using a background worker thread.
- schedule_at(datetime_or_iso, callable, *args, **kwargs) -> job_id
- schedule_delay(seconds, callable, ...) -> job_id
- schedule_every(interval_seconds, callable, ...) -> job_id (repeating)
- cancel(job_id)
- get_pending() -> list of pending jobs (metadata)
- Hooks to persist job metadata via callbacks (optional)

This scheduler is intentionally dependency-free (stdlib only).
"""

from __future__ import annotations

import heapq
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

ISO_FMT = "%Y-%m-%dT%H:%M:%S%z"


def now_ts() -> float:
    return time.time()


def iso_to_ts(iso: str) -> float:
    """Parse ISO 8601 string to epoch seconds. Falls back to fromisoformat."""
    if iso is None:
        raise ValueError("iso timestamp required")
    s = iso
    if s.endswith("Z"):
        s = s[:-1] + "+0000"
    if "+" not in s and "-" not in s[-6:]:
        dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        if s[-3] == ":":
            s = s[:-3] + s[-2:]
        dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")
    return dt.timestamp()


def ts_to_iso(ts: float) -> str:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")


class Scheduler:
    """
    In-process scheduler backed by a min-heap and worker thread.

    Job dict structure:
      {"job_id", "func", "args", "kwargs", "repeat", "next_run", "meta"}
    """

    def __init__(self, poll_interval_seconds: float = 1.0) -> None:
        self._heap: List[Tuple[float, int, dict]] = []
        self._lock = threading.RLock()
        self._cond = threading.Condition(self._lock)
        self._seq = 0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._jobs: Dict[str, dict] = {}
        self.poll_interval_seconds = float(poll_interval_seconds)
        self.persist_hook: Optional[Callable[[dict], None]] = None
        self.delete_hook: Optional[Callable[[str], None]] = None

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._run_loop, name="PackyScheduler", daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._cond.notify_all()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run_loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
                now = now_ts()
                if not self._heap:
                    self._cond.wait(timeout=self.poll_interval_seconds)
                    continue
                run_at, seq, job = self._heap[0]
                if run_at > now:
                    timeout = min(self.poll_interval_seconds, max(0, run_at - now))
                    self._cond.wait(timeout=timeout)
                    continue
                heapq.heappop(self._heap)
                jid = job["job_id"]
                if jid not in self._jobs:
                    continue
            # Execute outside lock
            try:
                job["func"](*job.get("args", ()), **job.get("kwargs", {}))
            except Exception as exc:
                import logging
                logging.getLogger("scheduler").exception("Job %s raised %s", jid, exc)
            finally:
                with self._lock:
                    if jid not in self._jobs:
                        continue
                    repeat = job.get("repeat")
                    if repeat and repeat > 0:
                        job["next_run"] = now_ts() + repeat
                        self._seq += 1
                        heapq.heappush(self._heap, (job["next_run"], self._seq, job))
                        if self.persist_hook:
                            try:
                                self.persist_hook(job.copy())
                            except Exception:
                                pass
                    else:
                        del self._jobs[jid]
                        if self.delete_hook:
                            try:
                                self.delete_hook(jid)
                            except Exception:
                                pass

    def _push_job(self, job: dict) -> None:
        with self._lock:
            self._seq += 1
            heapq.heappush(self._heap, (job["next_run"], self._seq, job))
            self._jobs[job["job_id"]] = job
            if self.persist_hook:
                try:
                    self.persist_hook(job.copy())
                except Exception:
                    pass
            self._cond.notify()

    def schedule_at(
        self,
        when: Any,
        func: Callable,
        *args: Any,
        repeat: Optional[float] = None,
        meta: Optional[dict] = None,
        **kwargs: Any,
    ) -> str:
        """Schedule a callable at a specific UTC time. Returns job_id."""
        if isinstance(when, (int, float)):
            ts = float(when)
        elif isinstance(when, str):
            ts = iso_to_ts(when)
        elif isinstance(when, datetime):
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            ts = when.timestamp()
        else:
            raise ValueError("Unsupported 'when' type")
        jid = str(uuid.uuid4())
        job = {
            "job_id": jid,
            "func": func,
            "args": args,
            "kwargs": kwargs,
            "repeat": float(repeat) if repeat else None,
            "next_run": float(ts),
            "meta": meta or {},
        }
        self._push_job(job)
        return jid

    def schedule_delay(
        self,
        delay_seconds: float,
        func: Callable,
        *args: Any,
        repeat: Optional[float] = None,
        meta: Optional[dict] = None,
        **kwargs: Any,
    ) -> str:
        run_at = now_ts() + float(delay_seconds)
        return self.schedule_at(run_at, func, *args, repeat=repeat, meta=meta, **kwargs)

    def schedule_every(
        self,
        interval_seconds: float,
        func: Callable,
        *args: Any,
        meta: Optional[dict] = None,
        **kwargs: Any,
    ) -> str:
        return self.schedule_delay(
            interval_seconds, func, *args, repeat=interval_seconds, meta=meta, **kwargs
        )

    def cancel(self, job_id: str) -> bool:
        """Cancel a scheduled job. Returns True if found and removed."""
        with self._lock:
            job = self._jobs.pop(job_id, None)
            if not job:
                return False
            if self.delete_hook:
                try:
                    self.delete_hook(job_id)
                except Exception:
                    pass
            self._cond.notify()
            return True

    def get_pending(self) -> List[dict]:
        with self._lock:
            return [job.copy() for job in self._jobs.values()]

    def attach_persistence(
        self,
        persist_hook: Optional[Callable[[dict], None]],
        delete_hook: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Attach persistence hooks for external storage."""
        self.persist_hook = persist_hook
        self.delete_hook = delete_hook


_global_scheduler: Optional[Scheduler] = None


def get_global_scheduler(poll_interval_seconds: float = 1.0) -> Scheduler:
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = Scheduler(poll_interval_seconds=poll_interval_seconds)
        _global_scheduler.start()
    return _global_scheduler
