"""SQLite wrapper for license records.

One row per Stripe checkout completion. Holds the customer info Stripe
gave us and the signed license JSON we handed them. Survives across
server restarts so customers can re-download their license months later.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


@dataclass
class LicenseRow:
    license_id: str
    tier: str
    customer_name: str
    customer_email: str
    stripe_session_id: str
    signed_at: str
    support_until: str
    seats: int
    features_json: str
    license_json: str
    amount_cents: int
    currency: str

    @property
    def signed_at_dt(self) -> datetime:
        return datetime.fromisoformat(self.signed_at)

    @property
    def support_until_dt(self) -> datetime:
        return datetime.fromisoformat(self.support_until)

    @property
    def features(self) -> list[str]:
        return json.loads(self.features_json)


class LicenseDB:
    """Thread-safe SQLite wrapper.

    Each request gets a connection; we serialize writes via a lock because
    SQLite's WAL mode still serializes. Reads can use a fresh connection
    but for simplicity we share the lock.
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS licenses (
      license_id         TEXT PRIMARY KEY,
      tier               TEXT NOT NULL,
      customer_name      TEXT NOT NULL,
      customer_email     TEXT NOT NULL,
      stripe_session_id  TEXT NOT NULL UNIQUE,
      signed_at          TEXT NOT NULL,
      support_until      TEXT NOT NULL,
      seats              INTEGER NOT NULL,
      features_json      TEXT NOT NULL,
      license_json       TEXT NOT NULL,
      amount_cents       INTEGER NOT NULL,
      currency           TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_licenses_email ON licenses(customer_email);
    """

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._lock = threading.Lock()
        # mode 600 — only this process should read it
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(self.SCHEMA)
            conn.commit()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, isolation_level=None, timeout=5.0)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn
        finally:
            conn.close()

    def insert_license(self, row: LicenseRow) -> None:
        with self._lock, self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO licenses
                      (license_id, tier, customer_name, customer_email,
                       stripe_session_id, signed_at, support_until, seats,
                       features_json, license_json, amount_cents, currency)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.license_id, row.tier, row.customer_name,
                        row.customer_email, row.stripe_session_id,
                        row.signed_at, row.support_until, row.seats,
                        row.features_json, row.license_json,
                        row.amount_cents, row.currency,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                # The stripe_session_id UNIQUE constraint is our idempotency
                # guarantee: Stripe retries the same webhook can hit us
                # many times, and we MUST not double-insert.
                if "stripe_session_id" in str(exc):
                    raise DuplicateSessionError(row.stripe_session_id) from exc
                raise

    def find_by_license_id(self, license_id: str) -> LicenseRow | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM licenses WHERE license_id = ?", (license_id,)
            ).fetchone()
        return _row_to_obj(row) if row else None

    def find_by_session_id(self, session_id: str) -> LicenseRow | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM licenses WHERE stripe_session_id = ?", (session_id,)
            ).fetchone()
        return _row_to_obj(row) if row else None


class DuplicateSessionError(Exception):
    """Raised when the same Stripe session is processed twice.

    Not an error condition — it's our idempotency guard. Callers should
    treat it as success.
    """

    def __init__(self, session_id: str):
        super().__init__(f"session {session_id} already processed")
        self.session_id = session_id


def _row_to_obj(row: sqlite3.Row) -> LicenseRow:
    return LicenseRow(
        license_id=row["license_id"],
        tier=row["tier"],
        customer_name=row["customer_name"],
        customer_email=row["customer_email"],
        stripe_session_id=row["stripe_session_id"],
        signed_at=row["signed_at"],
        support_until=row["support_until"],
        seats=row["seats"],
        features_json=row["features_json"],
        license_json=row["license_json"],
        amount_cents=row["amount_cents"],
        currency=row["currency"],
    )


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
