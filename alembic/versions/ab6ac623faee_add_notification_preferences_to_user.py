"""Add notification preference fields to User model.

Revision ID: ab6ac623faee
Revises: a3f1d2e8c9b0
Create Date: 2026-03-23 01:58:51.544174

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ab6ac623faee"
down_revision: str | Sequence[str] | None = "a3f1d2e8c9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "auth_user",
        sa.Column(
            "notify_in_app",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "auth_user",
        sa.Column(
            "notify_email",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("auth_user", "notify_email")
    op.drop_column("auth_user", "notify_in_app")
