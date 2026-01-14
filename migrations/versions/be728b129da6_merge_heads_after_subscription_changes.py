"""merge heads after subscription changes

Revision ID: be728b129da6
Revises: 4bf0f736c4c4, fb89857480c4
Create Date: 2026-01-10 08:40:32.559967

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'be728b129da6'
down_revision = ('4bf0f736c4c4', 'fb89857480c4')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
