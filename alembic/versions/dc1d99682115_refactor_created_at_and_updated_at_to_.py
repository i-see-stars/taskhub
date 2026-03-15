"""Refactor created_at and updated_at to Base and remove legacy time columns

Revision ID: dc1d99682115
Revises: b47ab726b3c1
Create Date: 2026-03-15 18:41:50.839850

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dc1d99682115"
down_revision: str | Sequence[str] | None = "b47ab726b3c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # auth_user: remove create_time, update_time (created_at and updated_at are already there)
    op.drop_column("auth_user", "create_time")
    op.drop_column("auth_user", "update_time")

    # auth_refresh_token: remove create_time, update_time and add created_at, updated_at
    op.drop_column("auth_refresh_token", "create_time")
    op.drop_column("auth_refresh_token", "update_time")
    op.add_column(
        "auth_refresh_token",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "auth_refresh_token",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # auth_refresh_token
    op.drop_column("auth_refresh_token", "updated_at")
    op.drop_column("auth_refresh_token", "created_at")
    op.add_column(
        "auth_refresh_token",
        sa.Column(
            "update_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "auth_refresh_token",
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # auth_user
    op.add_column(
        "auth_user",
        sa.Column(
            "update_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "auth_user",
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
