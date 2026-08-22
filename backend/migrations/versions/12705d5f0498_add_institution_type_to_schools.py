"""add_institution_type_to_schools

Revision ID: 12705d5f0498
Revises: a1a1a1a1a1a1
Create Date: 2026-08-22 19:32:06.037849

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '12705d5f0498'
down_revision = 'a1a1a1a1a1a1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add institution_type column to schools table
    op.add_column('schools', sa.Column('institution_type', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Drop institution_type column from schools table
    op.drop_column('schools', 'institution_type')

