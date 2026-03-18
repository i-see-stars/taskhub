"""Add project_member table and comment table, remove project.owner_id.

Revision ID: a3f1d2e8c9b0
Revises: dc1d99682115
Create Date: 2026-03-18 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f1d2e8c9b0"
down_revision: str | Sequence[str] | None = "dc1d99682115"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create projectmemberrole enum
    projectmemberrole = sa.Enum("OWNER", "MEMBER", "VIEWER", name="projectmemberrole")
    projectmemberrole.create(op.get_bind())

    # 2. Create project_member table
    op.create_table(
        "project_member",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "role",
            sa.Enum("OWNER", "MEMBER", "VIEWER", name="projectmemberrole"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["project.project_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id", "user_id"),
    )

    # 3. Migrate existing owner_id data into project_member
    op.execute(
        """
        INSERT INTO project_member (project_id, user_id, role, created_at, updated_at)
        SELECT project_id, owner_id, 'OWNER', now(), now()
        FROM project
        """
    )

    # 4. Drop owner_id FK constraint and column from project
    op.drop_constraint("project_owner_id_fkey", "project", type_="foreignkey")
    op.drop_column("project", "owner_id")

    # 5. Create comment table
    op.create_table(
        "comment",
        sa.Column("comment_id", sa.String(length=36), nullable=False),
        sa.Column("issue_id", sa.String(length=36), nullable=False),
        sa.Column("author_id", sa.String(length=36), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["auth_user.user_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["issue_id"], ["issue.issue_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("comment_id"),
    )
    op.create_index(op.f("ix_comment_issue_id"), "comment", ["issue_id"], unique=False)
    op.create_index(
        op.f("ix_comment_author_id"), "comment", ["author_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Drop comment table
    op.drop_index(op.f("ix_comment_author_id"), table_name="comment")
    op.drop_index(op.f("ix_comment_issue_id"), table_name="comment")
    op.drop_table("comment")

    # 2. Re-add owner_id to project (nullable first for data migration)
    op.add_column(
        "project",
        sa.Column("owner_id", sa.String(length=36), nullable=True),
    )

    # 3. Restore owner_id from project_member where role = 'OWNER'
    op.execute(
        """
        UPDATE project p
        SET owner_id = pm.user_id
        FROM project_member pm
        WHERE pm.project_id = p.project_id
          AND pm.role = 'OWNER'
        """
    )

    # 4. Make owner_id NOT NULL and add FK
    op.alter_column("project", "owner_id", nullable=False)
    op.create_foreign_key(
        "project_owner_id_fkey",
        "project",
        "auth_user",
        ["owner_id"],
        ["user_id"],
        ondelete="CASCADE",
    )

    # 5. Drop project_member table and enum
    op.drop_table("project_member")
    sa.Enum(name="projectmemberrole").drop(op.get_bind())
