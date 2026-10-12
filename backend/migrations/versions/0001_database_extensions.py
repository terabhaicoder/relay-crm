"""Enable search and future AI extensions; no business schema before Phase 0 approval.

Revision ID: 0001_database_extensions
Revises: None
"""

from alembic import op

revision = "0001_database_extensions"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Extensions may be shared with later schemas. Never cascade-delete their dependent data.
    # Removing them is an explicit DBA operation after confirming no dependent objects exist.
    pass
