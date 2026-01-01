"""add missing columns to user

Revision ID: 9b90cdeced15
Revises: 
Create Date: 2026-01-01 20:21:27.747444

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b90cdeced15'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user",
        sa.Column("profile_photo", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "user",
        sa.Column("aadhar", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "user",
        sa.Column("mrc_certificate", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "user",
        sa.Column("clinic_license", sa.String(length=255), nullable=True)
    )


def downgrade():
    op.drop_column("user", "clinic_license")
    op.drop_column("user", "mrc_certificate")
    op.drop_column("user", "aadhar")
    op.drop_column("user", "profile_photo")

