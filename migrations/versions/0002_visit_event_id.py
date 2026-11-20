"""Give visits stable, unique event identities for replay-safe processing."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("visits", sa.Column("event_id", sa.Uuid(), nullable=True))
    op.execute("UPDATE visits SET event_id = gen_random_uuid() WHERE event_id IS NULL")
    op.alter_column("visits", "event_id", nullable=False)
    op.create_unique_constraint("uq_visits_event_id", "visits", ["event_id"])


def downgrade() -> None:
    op.drop_constraint("uq_visits_event_id", "visits", type_="unique")
    op.drop_column("visits", "event_id")
