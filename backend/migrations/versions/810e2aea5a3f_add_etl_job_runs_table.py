"""add_etl_job_runs_table

Revision ID: 810e2aea5a3f
Revises: c21b22b894db
Create Date: 2026-08-23 22:28:10.575426

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '810e2aea5a3f'
down_revision = 'c21b22b894db'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'etl_job_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('dataset', sa.String(length=100), nullable=False),
        sa.Column('job_uuid', sa.String(length=36), nullable=False),
        sa.Column('execution_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('records_processed', sa.Integer(), nullable=True),
        sa.Column('records_inserted', sa.Integer(), nullable=True),
        sa.Column('records_updated', sa.Integer(), nullable=True),
        sa.Column('records_skipped', sa.Integer(), nullable=True),
        sa.Column('records_rejected', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.String(length=1000), nullable=True),
        sa.Column('duration', sa.Numeric(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_etl_job_runs_id'), 'etl_job_runs', ['id'], unique=False)
    op.create_index(op.f('ix_etl_job_runs_job_uuid'), 'etl_job_runs', ['job_uuid'], unique=True)
    op.create_index(op.f('ix_etl_job_runs_source'), 'etl_job_runs', ['source'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_etl_job_runs_source'), table_name='etl_job_runs')
    op.drop_index(op.f('ix_etl_job_runs_job_uuid'), table_name='etl_job_runs')
    op.drop_index(op.f('ix_etl_job_runs_id'), table_name='etl_job_runs')
    op.drop_table('etl_job_runs')

