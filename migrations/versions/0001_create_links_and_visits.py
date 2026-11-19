"""Create links, visits, and the dedicated short-code sequence."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSequence(sa.Sequence("short_code_sequence", start=1)))
    op.create_table(
        "short_links",
        sa.Column("short_code", sa.String(), nullable=False),
        sa.Column("original_url", sa.String(2048), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "visit_count", sa.BigInteger(), server_default=sa.text("0"), nullable=False
        ),
        sa.CheckConstraint(
            "visit_count >= 0", name="ck_short_links_visit_count_nonnegative"
        ),
        sa.PrimaryKeyConstraint("short_code", name="pk_short_links"),
    )
    op.create_table(
        "visits",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("short_code", sa.String(), nullable=False),
        sa.Column("client_ip", postgresql.INET(), nullable=False),
        sa.Column(
            "visited_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_visits"),
        sa.ForeignKeyConstraint(
            ["short_code"],
            ["short_links.short_code"],
            name="fk_visits_short_code_short_links",
        ),
    )
    op.create_index("ix_visits_short_code", "visits", ["short_code"])


def downgrade() -> None:
    op.drop_index("ix_visits_short_code", table_name="visits")
    op.drop_table("visits")
    op.drop_table("short_links")
    op.execute(sa.schema.DropSequence(sa.Sequence("short_code_sequence")))
