"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-09

Hand-written raw SQL, one statement per op.execute() (the asyncpg driver rejects
multi-statement prepared statements). See docs/db_schema.dbml for the diagram.
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

_STATEMENTS = [
    # Keep updated_at honest without any application code touching it.
    """
    CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
    BEGIN
        NEW.updated_at = now();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,
    "CREATE TYPE order_status AS ENUM ('pending', 'confirmed', 'cancelled')",
    """
    CREATE TABLE users (
        id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        email         VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE products (
        id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        name           VARCHAR(255) NOT NULL,
        price          NUMERIC(12, 2) NOT NULL CHECK (price > 0),
        stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0),
        created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TRIGGER trg_products_updated_at BEFORE UPDATE ON products
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """,
    """
    CREATE TABLE orders (
        id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id      BIGINT NOT NULL REFERENCES users(id),
        status       order_status NOT NULL DEFAULT 'pending',
        total_amount NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0),
        expires_at   TIMESTAMPTZ NOT NULL,
        created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TRIGGER trg_orders_updated_at BEFORE UPDATE ON orders
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """,
    "CREATE INDEX idx_orders_user_id ON orders(user_id)",
    # Drives the expiry sweep; partial so it only spans live reservations.
    """
    CREATE INDEX idx_orders_pending_expires_at ON orders(expires_at)
        WHERE status = 'pending'
    """,
    """
    CREATE TABLE order_items (
        id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        order_id          BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        product_id        BIGINT NOT NULL REFERENCES products(id),
        quantity          INTEGER NOT NULL CHECK (quantity > 0),
        price_at_purchase NUMERIC(12, 2) NOT NULL CHECK (price_at_purchase > 0)
    )
    """,
    "CREATE INDEX idx_order_items_order_id ON order_items(order_id)",
    """
    CREATE TABLE idempotency_keys (
        id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id       BIGINT NOT NULL REFERENCES users(id),
        key           VARCHAR(255) NOT NULL,
        endpoint      VARCHAR(255) NOT NULL,
        response_body JSONB NOT NULL,
        status_code   INTEGER NOT NULL,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (user_id, key)
    )
    """,
]

_DOWN_STATEMENTS = [
    "DROP TABLE IF EXISTS idempotency_keys",
    "DROP TABLE IF EXISTS order_items",
    "DROP TABLE IF EXISTS orders",
    "DROP TABLE IF EXISTS products",
    "DROP TABLE IF EXISTS users",
    "DROP TYPE IF EXISTS order_status",
    "DROP FUNCTION IF EXISTS set_updated_at()",
]


def upgrade() -> None:
    for statement in _STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in _DOWN_STATEMENTS:
        op.execute(statement)
