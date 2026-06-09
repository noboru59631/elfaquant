import sqlite3
from typing import Optional, Dict, Any
from pathlib import Path
import json
from datetime import datetime, timezone

class Registry:
    """
    Manages the SQLite registry for the Elfa GRVT bot.
    """
    def __init__(self, db_path: str = "./registry.db"):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Ensures the database and tables exist with the correct schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                -- Active and historical strategies.
                CREATE TABLE IF NOT EXISTS strategies (
                    query_id              TEXT PRIMARY KEY,
                    title                 TEXT NOT NULL,
                    description           TEXT,
                    eql_json              TEXT NOT NULL,
                    symbol                TEXT NOT NULL,
                    side                  TEXT NOT NULL CHECK (side IN ('buy','sell')),
                    amount                REAL NOT NULL CHECK (amount > 0),
                    order_type            TEXT NOT NULL CHECK (order_type IN ('market','limit')),
                    price                 REAL,
                    leverage              INTEGER,
                    time_in_force         TEXT DEFAULT 'GTC',
                    reduce_only           INTEGER NOT NULL DEFAULT 0,
                    max_notional_usd      REAL NOT NULL CHECK (max_notional_usd > 0),
                    tp_pct                REAL,
                    sl_pct                REAL,
                    env                   TEXT NOT NULL DEFAULT 'prod' CHECK (env = 'prod'),
                    status                TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active','fired','expired','cancelled','failed')),
                    created_at            TEXT NOT NULL,
                    updated_at            TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies(status);

                -- Fire records.
                CREATE TABLE IF NOT EXISTS fires (
                    event_id              TEXT PRIMARY KEY,
                    query_id              TEXT NOT NULL,
                    raw_payload           TEXT NOT NULL,
                    outcome               TEXT NOT NULL
                        CHECK (outcome IN ('placed','rejected_guardrail','grvt_error',
                                           'unknown_strategy','duplicate','unknown')),
                    error                 TEXT,
                    parent_order_id       TEXT,
                    tp_order_id           TEXT,
                    sl_order_id           TEXT,
                    reference_price       REAL,
                    tp_price              REAL,
                    sl_price              REAL,
                    received_at           TEXT NOT NULL,
                    placed_at             TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_fires_query_id ON fires(query_id);

                -- User-facing alerts.
                CREATE TABLE IF NOT EXISTS alerts (
                    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                    severity              TEXT NOT NULL CHECK (severity IN ('info','warning','error')),
                    category              TEXT NOT NULL,
                    message               TEXT NOT NULL,
                    query_id              TEXT,
                    fire_event_id         TEXT,
                    details_json          TEXT,
                    created_at            TEXT NOT NULL,
                    acked_at              TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_alerts_unacked ON alerts(acked_at) WHERE acked_at IS NULL;
            """)
            conn.commit()

    def add_strategy(self, query_id: str, title: str, description: str, eql_json: str,
                     symbol: str, side: str, amount: float, order_type: str,
                     price: Optional[float], leverage: Optional[int],
                     max_notional_usd: float, tp_pct: Optional[float],
                     sl_pct: Optional[float]) -> bool:
        """Adds a new strategy to the registry."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO strategies (
                        query_id, title, description, eql_json, symbol, side, amount,
                        order_type, price, leverage, max_notional_usd, tp_pct, sl_pct,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    query_id, title, description, eql_json, symbol, side, amount,
                    order_type, price, leverage, max_notional_usd, tp_pct, sl_pct,
                    now, now
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_strategy(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a strategy by its query_id."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM strategies WHERE query_id = ?", (query_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_strategy_status(self, query_id: str, status: str) -> bool:
        """Updates the status of a strategy."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE strategies
                SET status = ?, updated_at = ?
                WHERE query_id = ?
            """, (status, now, query_id))
            conn.commit()
            return cursor.rowcount > 0

    def add_fire(self, event_id: str, query_id: str, raw_payload: str,
                 outcome: str, error: Optional[str] = None,
                 parent_order_id: Optional[str] = None,
                 tp_order_id: Optional[str] = None,
                 sl_order_id: Optional[str] = None,
                 reference_price: Optional[float] = None,
                 tp_price: Optional[float] = None,
                 sl_price: Optional[float] = None) -> bool:
        """Adds a fire record to the registry."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO fires (
                        event_id, query_id, raw_payload, outcome, error,
                        parent_order_id, tp_order_id, sl_order_id,
                        reference_price, tp_price, sl_price, received_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id, query_id, raw_payload, outcome, error,
                    parent_order_id, tp_order_id, sl_order_id,
                    reference_price, tp_price, sl_price, now
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def add_alert(self, severity: str, category: str, message: str,
                  query_id: Optional[str] = None,
                  fire_event_id: Optional[str] = None,
                  details_json: Optional[str] = None) -> int:
        """Adds an alert to the registry."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO alerts (
                    severity, category, message, query_id, fire_event_id,
                    details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                severity, category, message, query_id, fire_event_id,
                details_json, now
            ))
            conn.commit()
            return cursor.lastrowid

    def get_unacked_alerts(self) -> list:
        """Retrieves all unacknowledged alerts."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM alerts WHERE acked_at IS NULL")
            return [dict(row) for row in cursor.fetchall()]

    def ack_alert(self, alert_id: int) -> bool:
        """Marks an alert as acknowledged."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE alerts
                SET acked_at = ?
                WHERE id = ?
            """, (now, alert_id))
            conn.commit()
            return cursor.rowcount > 0


    def update_fire_outcome(
        self,
        event_id: str,
        outcome: str,
        error: str = None,
        parent_order_id: str = None,
        tp_order_id: str = None,
        sl_order_id: str = None,
        reference_price: float = None,
        tp_price: float = None,
        sl_price: float = None,
    ) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                """UPDATE fires SET
                    outcome=?,
                    error=?,
                    parent_order_id=?,
                    tp_order_id=?,
                    sl_order_id=?,
                    reference_price=?,
                    tp_price=?,
                    sl_price=?,
                    placed_at=CASE WHEN ? IS NOT NULL THEN datetime('now') ELSE placed_at END
                WHERE event_id=?""",
                (
                    outcome,
                    error,
                    parent_order_id,
                    tp_order_id,
                    sl_order_id,
                    reference_price,
                    tp_price,
                    sl_price,
                    parent_order_id,
                    event_id,
                )
            )
                pass
            return True
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"update_fire_outcome error: {e}")
            return False
    def list_strategies(self, status: str = None) -> list:
        with sqlite3.connect(self.db_path) as conn:
            cols = [d[1] for d in conn.execute("PRAGMA table_info(strategies)").fetchall()]
            rows = conn.execute("SELECT * FROM strategies WHERE status = ?" if status else "SELECT * FROM strategies", (status,) if status else ()).fetchall()
            return [dict(zip(cols, row)) for row in rows]

