"""add trial and subscription fields to clinic

Revision ID: fb89857480c4
Revises: <PUT_PREVIOUS_REVISION_ID_HERE>
Create Date: 2026-01-10
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "fb89857480c4"
down_revision = '9b90cdeced15'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "clinic",
        sa.Column("trial_started_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "clinic",
        sa.Column("trial_ends_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "clinic",
        sa.Column(
            "subscription_status",
            sa.String(length=20),
            nullable=False,
            server_default="trial"
        )
    )
    op.add_column(
        "clinic",
        sa.Column(
            "plan",
            sa.String(length=50),
            nullable=False,
            server_default="trial"
        )
    )


def downgrade():
    op.drop_column("clinic", "plan")
    op.drop_column("clinic", "subscription_status")
    op.drop_column("clinic", "trial_ends_at")
    op.drop_column("clinic", "trial_started_at")
