"""merge multiple heads

Revision ID: 725ec001d3f5
Revises: 07650aa4216d, c9fd5adf3d01
Create Date: 2025-12-31 01:20:29.522245

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '725ec001d3f5'
down_revision = ('07650aa4216d', 'c9fd5adf3d01')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
