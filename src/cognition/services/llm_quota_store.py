"""
services.llm_quota_store — Rate limiting and quota tracking for LLM calls.

Thread-safe with per-minute and daily limits, atomic file persistence.
"""

from __future__ import annotations

import datetime
import fcntl
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Tuple

DATA_DIR = Path(os.path.expanduser("~/assistant_repo/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_PATH = DATA_DIR / "llm_quota.json"


class QuotaExceeded(Exception):
    """Raised when the daily or per-minute rate limit is exceeded."""

    pass


class QuotaStore:
    """File-backed daily + per-minute quota tracker."""

    def __init__(
        self,
        path: str | Path = DEFAULT_PATH,
        daily_limit: int = 1000,
        per_minute_limit: int = 10,
        cost_per_million: float = 0.008,
    ) -> None:
        self.path = Path(path)
        self.daily_limit = int(daily_limit)
        self.per_minute_limit = int(per_minute_limit)
        self.cost_per_million = float(cost_per_million)
        self._minute_bucket: Dict[str, int] = {"minute": 0, "count": 0}

        if not self.path.exists():
            self._write_store({})

    # --- File helpers ---

    def _read_store(self) -> Dict[str, int]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            return {}
        with open(self.path, "r+", encoding="utf-8") as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX)
                data = json.load(f)
            except Exception:
                data = {}
            finally:
                try:
                    fcntl.flock(f, fcntl.LOCK_UN)
                except Exception:
                    pass
        return data

    def _write_store(self, data: Dict[str, int]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(self.path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(self.path))

    # --- Rate limiting ---

    @staticmethod
    def _today_key(now: datetime.datetime | None = None) -> str:
        now = now or datetime.datetime.now(datetime.timezone.utc)
        return now.strftime("%Y-%m-%d")

    def get_today_usage(self) -> int:
        store = self._read_store()
        return int(store.get(self._today_key(), 0))

    def _increment_today(self, delta: int = 1) -> int:
        store = self._read_store()
        key = self._today_key()
        current = int(store.get(key, 0))
        current += delta
        store[key] = current
        self._write_store(store)
        return current

    def _check_per_minute(self) -> None:
        now = int(time.time())
        minute = now // 60
        if self._minute_bucket["minute"] != minute:
            self._minute_bucket["minute"] = minute
            self._minute_bucket["count"] = 0
        if self._minute_bucket["count"] >= self.per_minute_limit:
            raise QuotaExceeded("Per-minute rate limit exceeded")
        self._minute_bucket["count"] += 1

    # --- Public API ---

    def try_consume(self, tokens: int = 1) -> Tuple[bool, Dict[str, Any]]:
        """Try to consume quota. Returns (allowed, info)."""
        try:
            self._check_per_minute()
        except QuotaExceeded as e:
            return False, {"reason": str(e)}

        used = self.get_today_usage()
        if used + tokens > self.daily_limit:
            return False, {
                "reason": "Daily quota exceeded",
                "allowed_daily": self.daily_limit,
                "used_today": used,
                "cost_estimate_usd": round((used / 1_000_000.0) * self.cost_per_million, 9),
            }

        new = self._increment_today(tokens)
        return True, {
            "allowed_daily": self.daily_limit,
            "used_today": new,
            "cost_estimate_usd": round((new / 1_000_000.0) * self.cost_per_million, 9),
        }

    def usage_info(self) -> Dict[str, Any]:
        used = self.get_today_usage()
        now = datetime.datetime.now(datetime.timezone.utc)
        tomorrow = now + datetime.timedelta(days=1)
        reset = datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day)

        return {
            "allowed_daily": self.daily_limit,
            "used_today": used,
            "cost_estimate_usd": round((used / 1_000_000.0) * self.cost_per_million, 9),
            "resets_at_utc": reset.isoformat() + "Z",
        }
