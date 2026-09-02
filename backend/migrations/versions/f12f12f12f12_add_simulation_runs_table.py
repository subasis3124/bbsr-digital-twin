"""add_simulation_runs_table

Revision ID: f12f12f12f12
Revises: e11e11e11e11
Create Date: 2026-09-02 03:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f12f12f12f12'
down_revision = 'e11e11e11e11'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create simulation_runs table
    op.create_table(
        'simulation_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('simulation_id', sa.String(length=36), nullable=False),
        sa.Column('scenario_type', sa.String(length=50), nullable=False),
        sa.Column('scenario_name', sa.String(length=150), nullable=False),
        sa.Column('base_state_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('simulation_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('spatial_scope_type', sa.String(length=50), nullable=False, server_default='all'),
        sa.Column('engine_version', sa.String(length=20), nullable=False, server_default='1.0.0'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('impact_summary', sa.JSON(), nullable=False),
        sa.Column('provenance', sa.JSON(), nullable=False),
        sa.Column('transformations', sa.JSON(), nullable=False),
        sa.Column('base_state_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('simulated_state_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('simulated_states_payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_simulation_runs_id'), 'simulation_runs', ['id'], unique=False)
    op.create_index(op.f('ix_simulation_runs_simulation_id'), 'simulation_runs', ['simulation_id'], unique=True)
    op.create_index(op.f('ix_simulation_runs_scenario_type'), 'simulation_runs', ['scenario_type'], unique=False)
    op.create_index(op.f('ix_simulation_runs_base_state_timestamp'), 'simulation_runs', ['base_state_timestamp'], unique=False)
    op.create_index(op.f('ix_simulation_runs_simulation_timestamp'), 'simulation_runs', ['simulation_timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_simulation_runs_simulation_timestamp'), table_name='simulation_runs')
    op.drop_index(op.f('ix_simulation_runs_base_state_timestamp'), table_name='simulation_runs')
    op.drop_index(op.f('ix_simulation_runs_scenario_type'), table_name='simulation_runs')
    op.drop_index(op.f('ix_simulation_runs_simulation_id'), table_name='simulation_runs')
    op.drop_index(op.f('ix_simulation_runs_id'), table_name='simulation_runs')
    op.drop_table('simulation_runs')
