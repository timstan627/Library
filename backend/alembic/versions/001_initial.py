"""Initial migration — create all tables from the current model metadata.

Revision ID: 001_initial
Revises:
Create Date: 2024-01-20

Derived from ``Base.metadata`` (create-all semantics) instead of
hand-written DDL: the schema can never drift from the ORM models, every
table and index is exactly what the models expect, and it runs on SQLite
(the old 001 targeted PostgreSQL — UUID/ARRAY/JSONB/uuid_generate_v4 — and
crashed immediately on this stack).
"""
from typing import Sequence, Union

from alembic import op

from app.core.database import Base

# Register every mapped class on Base.metadata
import app.models  # noqa: F401

# revision identifiers
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # create_all is idempotent per table: a database bootstrapped by
    # init_db() gains only the missing tables; a fresh DB gets everything.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
