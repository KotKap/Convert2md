"""SQLite persistence and schema migrations."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
from typing import Any

from .domain import Budget, BudgetPeriod, Model, ModelStatus, Price, Provider
from .dto import RegisterUsageCommand, UsageQuery, UsageRecord, UsageSummary


MIGRATIONS = (
    (
        1,
        """
        CREATE TABLE providers(
          code TEXT PRIMARY KEY, display_name TEXT NOT NULL, adapter TEXT NOT NULL,
          secret_ref TEXT, enabled INTEGER NOT NULL, metadata_json TEXT NOT NULL);
        CREATE TABLE models(
          id TEXT PRIMARY KEY, provider_code TEXT NOT NULL REFERENCES providers(code),
          code TEXT NOT NULL, display_name TEXT NOT NULL, context_window INTEGER NOT NULL,
          max_output_tokens INTEGER, status TEXT NOT NULL, capabilities_json TEXT NOT NULL,
          rpm INTEGER, tpm INTEGER, rpd INTEGER, concurrent_requests INTEGER,
          metadata_json TEXT NOT NULL, UNIQUE(provider_code, code));
        CREATE TABLE prices(
          id INTEGER PRIMARY KEY, model_id TEXT NOT NULL REFERENCES models(id),
          currency TEXT NOT NULL, input_per_million TEXT, cached_input_per_million TEXT,
          output_per_million TEXT, image_each TEXT, effective_from TEXT NOT NULL,
          source TEXT NOT NULL);
        CREATE INDEX prices_model_date ON prices(model_id, effective_from DESC);
        CREATE TABLE budgets(
          scope TEXT PRIMARY KEY, amount TEXT NOT NULL, currency TEXT NOT NULL,
          period TEXT NOT NULL, warning_ratio TEXT NOT NULL, enabled INTEGER NOT NULL);
        CREATE TABLE usage_records(
          request_id TEXT PRIMARY KEY, model_id TEXT NOT NULL, provider_code TEXT NOT NULL,
          operation TEXT NOT NULL, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
          cached_input_tokens INTEGER NOT NULL, reasoning_tokens INTEGER NOT NULL,
          image_count INTEGER NOT NULL, duration_ms INTEGER NOT NULL, status TEXT NOT NULL,
          total_cost TEXT, currency TEXT, price_snapshot_json TEXT, occurred_at TEXT NOT NULL,
          scope TEXT NOT NULL, document_id TEXT, provider_request_id TEXT, error_code TEXT,
          metadata_json TEXT NOT NULL);
        CREATE INDEX usage_date ON usage_records(occurred_at);
        CREATE INDEX usage_model ON usage_records(model_id, occurred_at);
        CREATE TABLE configuration_revisions(
          id INTEGER PRIMARY KEY, imported_at TEXT NOT NULL, format TEXT NOT NULL,
          source TEXT, payload_hash TEXT NOT NULL);
        CREATE TABLE audit_log(
          id INTEGER PRIMARY KEY, occurred_at TEXT NOT NULL, action TEXT NOT NULL,
          entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, details_json TEXT NOT NULL);
        """,
    ),
)


class SQLiteRepository:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.migrate()

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def migrate(self) -> None:
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY)")
            applied = {row[0] for row in db.execute("SELECT version FROM schema_migrations")}
            for version, sql in MIGRATIONS:
                if version not in applied:
                    db.executescript(sql)
                    db.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))

    def upsert_provider(self, provider: Provider) -> None:
        with self.connect() as db:
            db.execute(
                """INSERT INTO providers VALUES(?,?,?,?,?,?)
                ON CONFLICT(code) DO UPDATE SET display_name=excluded.display_name,
                adapter=excluded.adapter, secret_ref=excluded.secret_ref,
                enabled=excluded.enabled, metadata_json=excluded.metadata_json""",
                (provider.code, provider.display_name, provider.adapter, provider.secret_ref,
                 provider.enabled, json.dumps(provider.metadata)),
            )

    def list_providers(self) -> list[Provider]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM providers ORDER BY code").fetchall()
        return [Provider(r["code"], r["display_name"], r["adapter"], r["secret_ref"],
                         bool(r["enabled"]), json.loads(r["metadata_json"])) for r in rows]

    def upsert_model(self, model: Model) -> None:
        with self.connect() as db:
            db.execute(
                """INSERT INTO models VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET display_name=excluded.display_name,
                context_window=excluded.context_window,max_output_tokens=excluded.max_output_tokens,
                status=excluded.status,capabilities_json=excluded.capabilities_json,
                rpm=excluded.rpm,tpm=excluded.tpm,rpd=excluded.rpd,
                concurrent_requests=excluded.concurrent_requests,metadata_json=excluded.metadata_json""",
                (model.id, model.provider_code, model.code, model.display_name,
                 model.context_window, model.max_output_tokens, model.status.value,
                 json.dumps(model.capabilities), model.rpm, model.tpm, model.rpd,
                 model.concurrent_requests, json.dumps(model.metadata)),
            )

    def get_model(self, model_id: str) -> Model | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM models WHERE id=?", (model_id,)).fetchone()
        return self._model(row) if row else None

    def list_models(self, include_disabled: bool = False) -> list[Model]:
        sql = "SELECT * FROM models"
        if not include_disabled:
            sql += " WHERE status != 'disabled'"
        with self.connect() as db:
            rows = db.execute(sql + " ORDER BY provider_code, code").fetchall()
        return [self._model(row) for row in rows]

    @staticmethod
    def _model(row: sqlite3.Row) -> Model:
        return Model(
            row["provider_code"], row["code"], row["display_name"], row["context_window"],
            row["max_output_tokens"], ModelStatus(row["status"]),
            tuple(json.loads(row["capabilities_json"])), row["rpm"], row["tpm"], row["rpd"],
            row["concurrent_requests"], json.loads(row["metadata_json"]),
        )

    def add_price(self, price: Price) -> None:
        with self.connect() as db:
            db.execute(
                """INSERT INTO prices(model_id,currency,input_per_million,
                cached_input_per_million,output_per_million,image_each,effective_from,source)
                VALUES(?,?,?,?,?,?,?,?)""",
                (price.model_id, price.currency, _str(price.input_per_million),
                 _str(price.cached_input_per_million), _str(price.output_per_million),
                 _str(price.image_each), price.effective_from.isoformat(), price.source),
            )

    def current_price(self, model_id: str, at: datetime | None = None) -> Price | None:
        at = at or datetime.now().astimezone()
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM prices WHERE model_id=? AND effective_from<=? "
                "ORDER BY effective_from DESC,id DESC LIMIT 1", (model_id, at.isoformat())
            ).fetchone()
        if not row:
            return None
        return Price(row["model_id"], row["currency"], _decimal(row["input_per_million"]),
                     _decimal(row["cached_input_per_million"]), _decimal(row["output_per_million"]),
                     _decimal(row["image_each"]), datetime.fromisoformat(row["effective_from"]),
                     row["source"])

    def list_current_prices(self) -> list[Price]:
        return [
            price for model in self.list_models(include_disabled=True)
            if (price := self.current_price(model.id)) is not None
        ]

    def upsert_budget(self, budget: Budget) -> None:
        with self.connect() as db:
            db.execute(
                """INSERT INTO budgets VALUES(?,?,?,?,?,?) ON CONFLICT(scope) DO UPDATE SET
                amount=excluded.amount,currency=excluded.currency,period=excluded.period,
                warning_ratio=excluded.warning_ratio,enabled=excluded.enabled""",
                (budget.scope, str(budget.amount), budget.currency, budget.period.value,
                 str(budget.warning_ratio), budget.enabled),
            )

    def get_budget(self, scope: str) -> Budget | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM budgets WHERE scope=?", (scope,)).fetchone()
        return Budget(row["scope"], Decimal(row["amount"]), row["currency"],
                      BudgetPeriod(row["period"]), Decimal(row["warning_ratio"]),
                      bool(row["enabled"])) if row else None

    def list_budgets(self) -> list[Budget]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM budgets ORDER BY scope").fetchall()
        return [
            Budget(row["scope"], Decimal(row["amount"]), row["currency"],
                   BudgetPeriod(row["period"]), Decimal(row["warning_ratio"]),
                   bool(row["enabled"]))
            for row in rows
        ]

    def insert_usage(self, record: UsageRecord) -> None:
        snapshot = json.dumps(record.price_snapshot.__dict__) if record.price_snapshot else None
        with self.connect() as db:
            db.execute(
                """INSERT INTO usage_records VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (record.request_id, record.model_id, record.provider_code, record.operation,
                 record.input_tokens, record.output_tokens, record.cached_input_tokens,
                 record.reasoning_tokens, record.image_count, record.duration_ms, record.status,
                 _str(record.total_cost), record.currency, snapshot, record.occurred_at.isoformat(),
                 record.scope, record.document_id, record.provider_request_id, record.error_code,
                 json.dumps(record.metadata),),
            )

    def usage_summary(self, query: UsageQuery) -> UsageSummary:
        clauses, args = [], []
        for expression, value in (
            ("model_id=?", query.model_id), ("scope=?", query.scope),
            ("occurred_at>=?", query.since.isoformat() if query.since else None),
            ("occurred_at<?", query.until.isoformat() if query.until else None),
        ):
            if value is not None:
                clauses.append(expression)
                args.append(value)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self.connect() as db:
            rows = db.execute("SELECT * FROM usage_records" + where, args).fetchall()
        by_model: dict[str, dict[str, Any]] = {}
        total = Decimal("0")
        for row in rows:
            item = by_model.setdefault(row["model_id"], {"requests": 0, "input_tokens": 0,
                                                         "output_tokens": 0, "cost": "0"})
            item["requests"] += 1
            item["input_tokens"] += row["input_tokens"]
            item["output_tokens"] += row["output_tokens"]
            cost = Decimal(row["total_cost"] or "0")
            total += cost
            item["cost"] = str(Decimal(item["cost"]) + cost)
        return UsageSummary(
            len(rows), sum(r["status"] == "success" for r in rows),
            sum(r["status"] != "success" for r in rows), sum(r["input_tokens"] for r in rows),
            sum(r["output_tokens"] for r in rows), sum(r["cached_input_tokens"] for r in rows),
            sum(r["reasoning_tokens"] for r in rows), sum(r["image_count"] for r in rows),
            total, rows[0]["currency"] if rows and rows[0]["currency"] else "USD", by_model,
        )


def _decimal(value: str | None) -> Decimal | None:
    return Decimal(value) if value is not None else None


def _str(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
