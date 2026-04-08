"""Add notification payload JSONB field with GIN index.

Revision ID: f2c4d8a1b7e3
Revises: ab1a7039e306
Create Date: 2026-04-08 15:25:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2c4d8a1b7e3"
down_revision: str | Sequence[str] | None = "ab1a7039e306"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "notification",
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index(
        "ix_notification_payload_gin",
        "notification",
        ["payload"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_notification_payload_gin", table_name="notification")
    op.drop_column("notification", "payload")
