"""Persistent request accounting and RPM/TPM throttling."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import time


class QuotaLedger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY,
                    created_at REAL NOT NULL,
                    model TEXT NOT NULL,
                    estimated_tokens INTEGER NOT NULL,
                    actual_tokens INTEGER,
                    status TEXT NOT NULL,
                    error_code TEXT
                )"""
            )

    def record(
        self,
        model: str,
        estimated_tokens: int,
        status: str,
        actual_tokens: int | None = None,
        error_code: str | None = None,
    ) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO requests(created_at, model, estimated_tokens, actual_tokens, status, error_code) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (time.time(), model, estimated_tokens, actual_tokens, status, error_code),
            )

    def requests_today(self, model: str) -> int:
        now = datetime.now(timezone.utc)
        start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp()
        with self._connect() as db:
            row = db.execute(
                "SELECT COUNT(*) FROM requests WHERE model = ? AND created_at >= ?",
                (model, start),
            ).fetchone()
        return int(row[0])

    def usage_since(self, model: str, since: float) -> tuple[int, int]:
        with self._connect() as db:
            row = db.execute(
                "SELECT COUNT(*), COALESCE(SUM(COALESCE(actual_tokens, estimated_tokens)), 0) "
                "FROM requests WHERE model = ? AND created_at >= ?",
                (model, since),
            ).fetchone()
        return int(row[0]), int(row[1])


class RateLimiter:
    def __init__(self, ledger: QuotaLedger, sleep=time.sleep):
        self.ledger = ledger
        self.sleep = sleep

    def wait(self, model, estimated_tokens: int) -> None:
        if estimated_tokens > model.tpm:
            raise ValueError(
                f"Estimated request size {estimated_tokens} exceeds TPM for {model.name}"
            )
        while True:
            count, tokens = self.ledger.usage_since(model.name, time.time() - 60)
            if count < model.rpm and tokens + estimated_tokens <= model.tpm:
                return
            self.sleep(1)
