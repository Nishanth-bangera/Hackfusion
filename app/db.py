import sqlite3
from pathlib import Path

# The database file sits in the project root, next to README.md
DB_PATH = Path(__file__).resolve().parent.parent / "supplyshield.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS suppliers (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    city        TEXT NOT NULL,
    port        TEXT NOT NULL,
    approved    INTEGER NOT NULL DEFAULT 1   -- 1 = approved supplier, 0 = not approved
);

CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY,
    sku         TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL
);

-- Which supplier sells which product, at what price, lead time and capacity
CREATE TABLE IF NOT EXISTS supplier_products (
    supplier_id     INTEGER NOT NULL REFERENCES suppliers(id),
    product_id      INTEGER NOT NULL REFERENCES products(id),
    unit_price_inr  REAL NOT NULL,
    lead_time_days  INTEGER NOT NULL,
    capacity_units  INTEGER NOT NULL,
    PRIMARY KEY (supplier_id, product_id)
);

CREATE TABLE IF NOT EXISTS inventory (
    product_id          INTEGER PRIMARY KEY REFERENCES products(id),
    on_hand_units       INTEGER NOT NULL,
    daily_usage_units   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY,
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL,
    customer    TEXT NOT NULL,
    due_date    TEXT NOT NULL,              -- YYYY-MM-DD
    status      TEXT NOT NULL DEFAULT 'open'
);

-- One row per disruption run started by an event
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_text      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'queued',  -- queued, running, done, failed, escalated
    failure_reason  TEXT,
    result_json     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Activity log: every agent step, shown live in the dashboard
CREATE TABLE IF NOT EXISTS job_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      INTEGER NOT NULL REFERENCES jobs(id),
    agent       TEXT NOT NULL,
    message     TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Actions taken or proposed: draft POs, emails, escalations
CREATE TABLE IF NOT EXISTS actions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id        INTEGER NOT NULL REFERENCES jobs(id),
    action_type   TEXT NOT NULL,            -- draft_po, email, escalation
    status        TEXT NOT NULL,            -- approved, rejected, escalated, executed
    payload_json  TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us read columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all tables if they don't exist. Safe to run many times."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
